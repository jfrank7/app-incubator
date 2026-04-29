import json
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncIterator

from langfuse import observe, propagate_attributes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Run
from app.schemas.form import ArchitectureBlueprint, FormAnswers, ProductSpec
from app.services.agent_loader import load_agent_instructions
from app.services.claude_client import ClaudeClient
from app.services.pattern_library import get_patterns_for_file
from app.services.sse_manager import sse_manager
from app.services.version_checker import (
    format_versions_for_prompt,
    get_mobile_versions,
    get_python_versions,
)
from app.services.workspace import workspace

claude = ClaudeClient()

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
## Workspace context (from previous agents)
{workspace_context}

---

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

Keep screens minimal (3-5). Auth always true. Prioritise MVP."""

BLUEPRINT_PROMPT = """\
## Workspace context (from previous agents)
{workspace_context}

---

Generate an ArchitectureBlueprint JSON for this app.

Product spec:
{spec_json}

Return a JSON object with these exact fields:
{{
  "mobile_framework": "expo",
  "backend_framework": "fastapi",
  "selected_modules": ["list of module names"],
  "file_plan": [
    {{"path": "relative/path/from/app/root.tsx", "description": "what this file does"}}
  ],
  "api_routes": [
    {{"method": "GET|POST|PUT|DELETE", "path": "/api/...", "description": "..."}}
  ],
  "db_entities": ["EntityName"],
  "env_vars": [
    {{"key": "VAR_NAME", "example_value": "...", "description": "..."}}
  ]
}}

File plan rules:
- Mobile files: start with "apps/mobile/"
- Backend files: start with "backend/"
- Always include: apps/mobile/babel.config.js, apps/mobile/metro.config.js, apps/mobile/package.json, apps/mobile/app.json, apps/mobile/tsconfig.json
- Always include: apps/mobile/app/_layout.tsx, apps/mobile/app/(tabs)/_layout.tsx, apps/mobile/app/(tabs)/index.tsx, apps/mobile/app/(tabs)/settings.tsx
- Always include auth: apps/mobile/app/(auth)/login.tsx, apps/mobile/app/(auth)/signup.tsx
- Always include: apps/mobile/lib/storage/session.tsx, apps/mobile/lib/api/client.ts
- Always include: backend/app/main.py, backend/app/db/database.py, backend/app/models/user.py, backend/app/auth/router.py, backend/app/auth/service.py, backend/app/core/security.py, backend/pyproject.toml, backend/.env.example
- Add app-specific screens and backend resources based on the spec
- DB entities always includes User"""


async def _update_run(run_id: str, **fields) -> None:
    async with _get_session() as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            raise RuntimeError(f"Run {run_id} not found")
        for k, v in fields.items():
            setattr(run, k, v)
        await session.commit()


# ── Stage 1: Spec Generation ──────────────────────────────────────────────────

@observe(name="spec-generation")
async def run_spec_generation(run_id: str, raw_idea: str, form_answers: FormAnswers) -> None:
    with propagate_attributes(session_id=run_id):
        workspace.init_index(run_id)
        await _update_run(run_id, status="generating_spec")
        await sse_manager.emit(run_id, "spec_generation", "Generating product spec with Claude Opus...")
        try:
            ctx = workspace.read_index(run_id)
            system = load_agent_instructions("spec-agent.md")
            prompt = SPEC_PROMPT.format(
                raw_idea=raw_idea,
                form_json=form_answers.model_dump_json(indent=2),
                workspace_context=ctx,
            )
            spec_dict = await claude.generate_json(prompt, model="opus", system=system)
            spec = ProductSpec.model_validate(spec_dict)

            workspace.write_artifact(run_id, "spec.json", spec.model_dump())
            workspace.update_index(
                run_id,
                agent="spec-agent",
                summary=f"Generated spec: '{spec.app_name}' — {spec.goal}",
                decisions=[
                    f"App name: {spec.app_name}",
                    f"Screens: {', '.join(s.name for s in spec.screens)}",
                    f"Entities: {', '.join(e.name for e in spec.data_entities)}",
                    f"Auth: {spec.auth_required}, Payments: {spec.payments_placeholder}",
                ],
            )
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
                pass
            await sse_manager.emit_done(run_id, "failed")
            raise


# ── Stage 2: Blueprint Generation ─────────────────────────────────────────────

@observe(name="blueprint-generation")
async def run_blueprint_generation(run_id: str, spec: ProductSpec) -> None:
    with propagate_attributes(session_id=run_id):
        await _update_run(run_id, status="generating_blueprint")
        await sse_manager.emit(run_id, "blueprint_generation", "Generating architecture blueprint...")
        try:
            ctx = workspace.read_index(run_id)
            system = load_agent_instructions("blueprint-agent.md")
            prompt = BLUEPRINT_PROMPT.format(
                spec_json=spec.model_dump_json(indent=2),
                workspace_context=ctx,
            )
            bp_dict = await claude.generate_json(prompt, model="opus", system=system)
            blueprint = ArchitectureBlueprint.model_validate(bp_dict)

            workspace.write_artifact(run_id, "blueprint.json", blueprint.model_dump())
            workspace.update_index(
                run_id,
                agent="blueprint-agent",
                summary=f"{len(blueprint.file_plan)} files planned, {len(blueprint.api_routes)} API routes",
                decisions=[
                    f"Modules: {', '.join(blueprint.selected_modules)}",
                    f"DB entities: {', '.join(blueprint.db_entities)}",
                    f"API routes: {', '.join(f'{r.method} {r.path}' for r in blueprint.api_routes[:5])}",
                ],
            )
            await sse_manager.emit(
                run_id, "blueprint_generation",
                f"{len(blueprint.file_plan)} files planned — modules: {', '.join(blueprint.selected_modules)}"  # noqa: E501
            )
            await _update_run(
                run_id,
                status="awaiting_blueprint_review",
                blueprint_json=blueprint.model_dump_json(),
            )
            await sse_manager.emit_done(run_id, "awaiting_blueprint_review")
        except Exception as e:
            try:
                await _update_run(run_id, status="failed", error_summary=str(e))
            except Exception:
                pass
            await sse_manager.emit_done(run_id, "failed")
            raise


# ── Stage 3: Version Check ─────────────────────────────────────────────────────

async def run_version_check(run_id: str) -> tuple[dict, dict]:
    await sse_manager.emit(run_id, "version_check", "Checking live library versions...")
    try:
        mobile_v, python_v = await get_mobile_versions(), await get_python_versions()
        versions_artifact = {"mobile": mobile_v, "python": python_v}
        workspace.write_artifact(run_id, "versions.json", versions_artifact)
        workspace.update_index(
            run_id,
            agent="version-checker",
            summary=f"Verified: expo {mobile_v.get('expo', '?')}, fastapi {python_v.get('fastapi', '?')}",
        )
        await sse_manager.emit(  # noqa: E501
            run_id, "version_check",
            f"Versions verified: expo {mobile_v.get('expo', '?')}, fastapi {python_v.get('fastapi', '?')}"
        )
        return mobile_v, python_v
    except Exception as e:
        await sse_manager.emit(run_id, "version_check", f"Version check failed, using pinned defaults: {e}")  # noqa: E501
        return {}, {}


# ── Stage 4: File Generation (Agentic) ────────────────────────────────────────

def _build_file_prompt(
    file_path: str,
    file_description: str,
    spec: ProductSpec,
    blueprint: ArchitectureBlueprint,
    version_block: str,
    already_generated: list[str],
    workspace_context: str = "",
) -> str:
    patterns = get_patterns_for_file(file_path)
    generated_list = "\n".join(f"  - {p}" for p in already_generated) if already_generated else "  (none yet)"  # noqa: E501

    return f"""## Workspace context (decisions from previous agents)
{workspace_context}

---

Generate the file: `{file_path}`

Purpose: {file_description or 'See context below'}

## App Context
- Name: {spec.app_name}
- Slug: {spec.app_slug}
- Goal: {spec.goal}
- Target user: {spec.target_user}
- Screens: {', '.join(s.name for s in spec.screens)}
- Data entities: {', '.join(e.name for e in spec.data_entities)}
- Features: {', '.join(spec.features)}
- Auth required: {spec.auth_required}
- Payments placeholder: {spec.payments_placeholder}
- Style notes: {spec.style_notes}

## Architecture
- Selected modules: {', '.join(blueprint.selected_modules)}
- DB entities: {', '.join(blueprint.db_entities)}
- API routes: {', '.join(f"{r.method} {r.path}" for r in blueprint.api_routes)}

{version_block}

## Already Generated Files
{generated_list}

## Relevant Patterns
{patterns}

Generate the complete file content for `{file_path}`. Raw content only, no explanation."""


@observe(name="file-generation")
async def run_file_generation(
    run_id: str, spec: ProductSpec, blueprint: ArchitectureBlueprint
) -> None:
    with propagate_attributes(session_id=run_id):
        await _update_run(run_id, status="building_full")
        await sse_manager.emit(run_id, "file_generation", "Starting agentic file generation...")

        try:
            mobile_v, python_v = await run_version_check(run_id)
            version_block = format_versions_for_prompt(mobile_v, python_v)
            file_gen_system = load_agent_instructions("file-generator.md")

            output_dir = settings.generated_apps_path / run_id
            output_dir.mkdir(parents=True, exist_ok=True)

            already_generated: list[str] = []
            total = len(blueprint.file_plan)

            for i, file_plan in enumerate(blueprint.file_plan, 1):
                await sse_manager.emit(
                    run_id, "file_generation",
                    f"[{i}/{total}] Generating {file_plan.path}..."
                )
                ctx = workspace.read_index(run_id)
                prompt = _build_file_prompt(
                    file_plan.path,
                    file_plan.description,
                    spec,
                    blueprint,
                    version_block,
                    already_generated,
                    workspace_context=ctx,
                )

                content = await claude.generate_file(prompt, system=file_gen_system)

                dest = output_dir / file_plan.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content)
                already_generated.append(file_plan.path)
                workspace.register_file(run_id, file_plan.path, status="generated")

            # Write incubator artifacts
            incubator_dir = output_dir / "incubator"
            incubator_dir.mkdir(exist_ok=True)
            (incubator_dir / "product_spec.json").write_text(spec.model_dump_json(indent=2))
            (incubator_dir / "architecture_blueprint.json").write_text(blueprint.model_dump_json(indent=2))

            workspace.update_index(
                run_id, agent="file-generator",
                summary=f"Full generation complete: {len(already_generated)} files",
                files_written=already_generated,
            )
            await _update_run(
                run_id,
                status="done",
                stage_logs_json=json.dumps([{"stage": "file_generation", "files": len(already_generated)}]),  # noqa: E501
            )
            await sse_manager.emit(run_id, "file_generation", f"Done — {len(already_generated)} files generated")  # noqa: E501
            await sse_manager.emit_done(run_id, "done")

        except Exception as e:
            try:
                await _update_run(run_id, status="failed", error_summary=str(e))
            except Exception:
                pass
            await sse_manager.emit_done(run_id, "failed")
            raise


# ── Stage 3 alt: Shell (mobile-only preview) ──────────────────────────────────

@observe(name="shell-scaffolding")
async def run_shell_scaffolding(
    run_id: str, spec: ProductSpec, blueprint: ArchitectureBlueprint
) -> None:
    """Generate mobile-only files for quick preview before full build."""
    with propagate_attributes(session_id=run_id):
        await _update_run(run_id, status="generating_shell")
        await sse_manager.emit(run_id, "shell_scaffolding", "Generating mobile shell preview...")

        try:
            mobile_v, _ = await run_version_check(run_id)
            version_block = format_versions_for_prompt(mobile_v, {})
            file_gen_system = load_agent_instructions("file-generator.md")

            mobile_files = [f for f in blueprint.file_plan if f.path.startswith("apps/mobile")]
            output_dir = settings.generated_apps_path / run_id
            output_dir.mkdir(parents=True, exist_ok=True)

            already_generated: list[str] = []
            for i, file_plan in enumerate(mobile_files, 1):
                await sse_manager.emit(
                    run_id, "shell_scaffolding",
                    f"[{i}/{len(mobile_files)}] {file_plan.path}"
                )
                ctx = workspace.read_index(run_id)
                prompt = _build_file_prompt(
                    file_plan.path, file_plan.description, spec, blueprint,
                    version_block, already_generated, workspace_context=ctx
                )
                content = await claude.generate_file(prompt, system=file_gen_system)
                dest = output_dir / file_plan.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content)
                already_generated.append(file_plan.path)
                workspace.register_file(run_id, file_plan.path, status="shell-generated")

            workspace.update_index(
                run_id, agent="file-generator (shell)",
                summary=f"Shell: {len(already_generated)} mobile files generated",
                files_written=already_generated,
            )
            await _update_run(run_id, status="awaiting_shell_review")
            await sse_manager.emit(  # noqa: E501
                run_id, "shell_scaffolding",
                f"Shell ready — {len(already_generated)} mobile files"
            )
            await sse_manager.emit_done(run_id, "awaiting_shell_review")

        except Exception as e:
            try:
                await _update_run(run_id, status="failed", error_summary=str(e))
            except Exception:
                pass
            await sse_manager.emit_done(run_id, "failed")
            raise
