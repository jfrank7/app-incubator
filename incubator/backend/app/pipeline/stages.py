import json
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Run
from app.schemas.form import ArchitectureBlueprint, FormAnswers, ProductSpec
from app.services.blueprint_mapper import BlueprintMapper
from app.services.claude_client import ClaudeClient
from app.services.scaffolder import ScaffolderService
from app.services.sse_manager import sse_manager

claude = ClaudeClient()
mapper = BlueprintMapper()
scaffolder = ScaffolderService()

# Optional session override for testing — set via _override_session context manager
_session_override: ContextVar[AsyncSession | None] = ContextVar("_session_override", default=None)


@asynccontextmanager
async def _get_session() -> AsyncIterator[AsyncSession]:
    override = _session_override.get()
    if override is not None:
        yield override
    else:
        async with AsyncSessionLocal() as session:
            yield session

SPEC_PROMPT = """\
Generate a ProductSpec JSON for this mobile app.

Raw idea: {raw_idea}

Form answers:
{form_json}

Return a JSON object with these exact fields:
{{
  "app_name": "Human-readable name (letters/numbers/spaces/hyphens only)",
  "app_slug": "kebab-case-slug",
  "goal": "one sentence goal",
  "target_user": "who this is for",
  "screens": [{{"name": "string", "route": "string", "description": "string"}}],
  "features": ["string"],
  "data_entities": [{{"name": "PascalCase", "fields": ["field_name"]}}],
  "offline_support": boolean,
  "notifications": boolean,
  "auth_required": boolean,
  "payments_placeholder": boolean,
  "style_notes": "string",
  "non_goals": ["string"]
}}

Keep screens minimal (3-5 max). Prioritise MVP. No nice-to-haves."""


async def _update_run(run_id: str, **fields) -> None:
    async with _get_session() as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            raise RuntimeError(f"Run {run_id} not found")
        for k, v in fields.items():
            setattr(run, k, v)
        await session.commit()


async def run_spec_generation(run_id: str, raw_idea: str, form_answers: FormAnswers) -> None:
    """Stage 1: Call Claude to generate ProductSpec. Saves to DB, sets awaiting_spec_review."""
    await _update_run(run_id, status="generating_spec")
    await sse_manager.emit(run_id, "spec_generation", "Generating product spec...")
    try:
        prompt = SPEC_PROMPT.format(
            raw_idea=raw_idea,
            form_json=form_answers.model_dump_json(indent=2),
        )
        spec_dict = await claude.generate_json(prompt, model="opus")
        spec = ProductSpec.model_validate(spec_dict)
        await _update_run(
            run_id,
            status="awaiting_spec_review",
            app_name=spec.app_name,
            product_spec_json=spec.model_dump_json(),
        )
        await sse_manager.emit(run_id, "spec_generation", f"Spec ready: {spec.app_name}")
        await sse_manager.emit_done(run_id, "awaiting_spec_review")
    except Exception as e:
        try:
            await _update_run(run_id, status="failed", error_summary=str(e))
        except Exception:
            pass  # best-effort; don't suppress original or block emit_done
        await sse_manager.emit_done(run_id, "failed")
        raise


async def run_blueprint_generation(run_id: str, spec: ProductSpec) -> None:
    """Stage 2: Map spec to ArchitectureBlueprint. Saves to DB, sets awaiting_blueprint_review."""
    await _update_run(run_id, status="generating_blueprint")
    await sse_manager.emit(run_id, "blueprint_generation", "Building architecture blueprint...")
    try:
        blueprint = mapper.map(spec)
        await sse_manager.emit(
            run_id,
            "blueprint_generation",
            f"Modules: {', '.join(blueprint.selected_modules)}",
        )
        await _update_run(
            run_id,
            status="awaiting_blueprint_review",
            blueprint_json=blueprint.model_dump_json(),
        )
        await sse_manager.emit(run_id, "blueprint_generation", "Blueprint ready")
        await sse_manager.emit_done(run_id, "awaiting_blueprint_review")
    except Exception as e:
        try:
            await _update_run(run_id, status="failed", error_summary=str(e))
        except Exception:
            pass  # best-effort; don't suppress original or block emit_done
        await sse_manager.emit_done(run_id, "failed")
        raise


async def run_shell_scaffolding(
    run_id: str, spec: ProductSpec, blueprint: ArchitectureBlueprint
) -> None:
    """Stage 3: Scaffold mobile-only shell with placeholder data. Sets awaiting_shell_review."""
    await _update_run(run_id, status="generating_shell")
    await sse_manager.emit(run_id, "shell_scaffolding", "Scaffolding frontend shell...")
    try:
        shell_plan_items = mapper.shell_file_plan(spec)
        shell_blueprint = ArchitectureBlueprint(
            mobile_framework=blueprint.mobile_framework,
            backend_framework=blueprint.backend_framework,
            selected_modules=blueprint.selected_modules,
            file_plan=shell_plan_items,
            api_routes=[],
            db_entities=blueprint.db_entities,
            env_vars=blueprint.env_vars,
        )
        context_extra = {"shell_mode": True}
        output_dir = settings.generated_apps_path / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        written = scaffolder.scaffold(
            spec, shell_blueprint, output_dir, extra_context=context_extra
        )
        await sse_manager.emit(run_id, "shell_scaffolding", f"Wrote {len(written)} files")
        await _update_run(
            run_id,
            status="awaiting_shell_review",
            stage_logs_json=json.dumps([{"stage": "shell_scaffolding", "files": len(written)}]),
        )
        await sse_manager.emit_done(run_id, "awaiting_shell_review")
    except Exception as e:
        try:
            await _update_run(run_id, status="failed", error_summary=str(e))
        except Exception:
            pass  # best-effort; don't suppress original or block emit_done
        await sse_manager.emit_done(run_id, "failed")
        raise


async def run_full_scaffolding(
    run_id: str, spec: ProductSpec, blueprint: ArchitectureBlueprint
) -> None:
    """Stage 4: Scaffold complete app (frontend + backend). Sets done."""
    await _update_run(run_id, status="building_full")
    await sse_manager.emit(run_id, "full_scaffolding", "Building full app...")
    try:
        output_dir = settings.generated_apps_path / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        written = scaffolder.scaffold(spec, blueprint, output_dir)
        await sse_manager.emit(run_id, "full_scaffolding", f"Wrote {len(written)} files")

        incubator_dir = output_dir / "incubator"
        incubator_dir.mkdir(exist_ok=True)
        (incubator_dir / "product_spec.json").write_text(spec.model_dump_json(indent=2))
        (incubator_dir / "architecture_blueprint.json").write_text(
            blueprint.model_dump_json(indent=2)
        )

        await _update_run(
            run_id,
            status="done",
            stage_logs_json=json.dumps([{"stage": "full_scaffolding", "files": len(written)}]),
        )
        await sse_manager.emit(run_id, "full_scaffolding", "App generated successfully")
        await sse_manager.emit_done(run_id, "done")
    except Exception as e:
        try:
            await _update_run(run_id, status="failed", error_summary=str(e))
        except Exception:
            pass  # best-effort; don't suppress original or block emit_done
        await sse_manager.emit_done(run_id, "failed")
        raise
