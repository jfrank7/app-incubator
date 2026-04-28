> **SUPERSEDED** — Pipeline rewritten as fully agentic. See 2026-04-28-agentic-redesign.md

# Agentic App Incubator — Phase 3: Generation Pipeline (Human-Gated)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the generation pipeline so a submitted run goes through four human-gated stages, producing a reviewable frontend shell first, then a fully wired app after confirmation.

**Architecture:** Four staged async functions (no LangGraph — human gates break continuous flow). Each stage is triggered by an API call, runs as a background task, streams SSE progress, and terminates in a `awaiting_*_review` or `done`/`failed` status. State flows through the DB between stages.

**Pipeline flow:**
```
POST /api/runs
  → Stage 1: spec_generation (Claude generates ProductSpec)
  → status: awaiting_spec_review

POST /api/runs/{id}/approve-spec  (user submits reviewed/edited spec)
  → Stage 2: blueprint_generation (mapper produces ArchitectureBlueprint)
  → status: awaiting_blueprint_review

POST /api/runs/{id}/approve-blueprint  (user submits reviewed/edited blueprint)
  → Stage 3: shell_scaffolding (mobile-only, placeholder screens, instant MVP)
  → status: awaiting_shell_review

POST /api/runs/{id}/approve-shell  (user confirms shell layout is right)
  → Stage 4: full_scaffolding (complete frontend + backend)
  → status: done | failed
```

**Shell pass philosophy:** Mobile only. Scaffold real screen structure with app name/goal text but no API wiring, no auth checks, no backend. Goal is fastest possible proof-of-concept for the user to confirm screen structure is correct before spending tokens on the full backend. Aesthetics are the user's job.

**Tech Stack:** Anthropic Python SDK, sse-starlette, asyncio

**Prerequisite:** Phase 1 and Phase 2 complete.

---

## File Map

**Create:**
- `incubator/backend/app/services/claude_client.py`
- `incubator/backend/app/services/blueprint_mapper.py`
- `incubator/backend/app/services/sse_manager.py`
- `incubator/backend/app/pipeline/__init__.py`
- `incubator/backend/app/pipeline/stages.py`
- `incubator/backend/tests/test_claude_client.py`
- `incubator/backend/tests/test_blueprint_mapper.py`
- `incubator/backend/tests/test_pipeline_stages.py`

**Modify:**
- `incubator/backend/app/api/runs.py` — add approval endpoints + pipeline triggers
- `incubator/backend/app/schemas/run.py` — add approval request schemas
- `incubator/backend/app/templates/mobile/base/app/(tabs)/index.tsx.j2` — add shell mode mock data block
- `incubator/backend/app/templates/mobile/base/app/(auth)/login.tsx.j2` — add shell mode bypass block

---

## Task 11: Claude API service

**Files:**
- Create: `incubator/backend/app/services/claude_client.py`
- Create: `incubator/backend/tests/test_claude_client.py`

- [ ] **Step 1: Write failing test**

`incubator/backend/tests/test_claude_client.py`:
```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.claude_client import ClaudeClient


@pytest.fixture
def client():
    return ClaudeClient()


@pytest.mark.asyncio
async def test_generate_spec_calls_opus(client):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"app_name": "Test"}')]

    with patch.object(client._client_instance, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_spec("build a tracker", "{}")

    mock_msgs.create.assert_called_once()
    assert mock_msgs.create.call_args.kwargs["model"] == "claude-opus-4-7"


@pytest.mark.asyncio
async def test_generate_json_parses_response(client):
    payload = {"app_name": "Tracker", "app_slug": "tracker"}
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(payload))]

    with patch.object(client._client_instance, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_json("prompt")

    assert result["app_name"] == "Tracker"


@pytest.mark.asyncio
async def test_generate_json_strips_markdown_fences(client):
    payload = {"key": "value"}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=fenced)]

    with patch.object(client._client_instance, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_json("prompt")

    assert result["key"] == "value"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && uv run pytest tests/test_claude_client.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `incubator/backend/app/services/claude_client.py`**

```python
import json
import re

from anthropic import AsyncAnthropic

from app.config import settings

OPUS_MODEL = "claude-opus-4-7"
SONNET_MODEL = "claude-sonnet-4-6"

SPEC_SYSTEM = (
    "You are an expert mobile app architect. Generate structured JSON specs from app ideas. "
    "Always respond with valid JSON only. No markdown fences, no explanation."
)


class ClaudeClient:
    def __init__(self) -> None:
        self._client_instance = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate_spec(self, prompt: str, context: str, model: str = "opus") -> str:
        model_id = OPUS_MODEL if model == "opus" else SONNET_MODEL
        response = await self._client_instance.messages.create(
            model=model_id,
            max_tokens=4096,
            system=SPEC_SYSTEM,
            messages=[{"role": "user", "content": f"{context}\n\n{prompt}"}],
        )
        return response.content[0].text

    async def generate_json(self, prompt: str, model: str = "opus") -> dict:
        text = await self.generate_spec(prompt, "", model=model)
        text = text.strip()
        # strip markdown fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text.strip())
```

- [ ] **Step 4: Run tests**

```bash
cd incubator/backend && uv run pytest tests/test_claude_client.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/services/claude_client.py incubator/backend/tests/test_claude_client.py
git commit -m "feat: add Claude API client with Opus model routing"
```

---

## Task 12: Blueprint mapper service

**Files:**
- Create: `incubator/backend/app/services/blueprint_mapper.py`
- Create: `incubator/backend/tests/test_blueprint_mapper.py`

Converts a `ProductSpec` into an `ArchitectureBlueprint` by selecting modules and building a `file_plan`. Keeps full and shell file plans separate.

- [ ] **Step 1: Write failing test**

`incubator/backend/tests/test_blueprint_mapper.py`:
```python
import pytest

from app.schemas.form import EntitySpec, ProductSpec, ScreenSpec
from app.services.blueprint_mapper import BlueprintMapper


@pytest.fixture
def caffeine_spec() -> ProductSpec:
    return ProductSpec(
        app_name="Caffeine Tracker",
        app_slug="caffeine-tracker",
        goal="track caffeine",
        target_user="adults",
        screens=[
            ScreenSpec(name="Dashboard", route="/", description="main"),
            ScreenSpec(name="Add Entry", route="/new", description="log"),
        ],
        features=["logging", "history"],
        data_entities=[EntitySpec(name="CaffeineEntry", fields=["id", "mg", "timestamp"])],
        offline_support=True,
        notifications=False,
        auth_required=True,
        payments_placeholder=False,
        style_notes="minimal",
        non_goals=["social"],
    )


def test_mapper_includes_dashboard_module(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "dashboard" in blueprint.selected_modules


def test_mapper_auth_module_when_auth_required(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "auth" in blueprint.selected_modules


def test_mapper_no_auth_module_when_auth_not_required(caffeine_spec):
    caffeine_spec.auth_required = False
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "auth" not in blueprint.selected_modules


def test_mapper_includes_payments_when_spec_says_so(caffeine_spec):
    caffeine_spec.payments_placeholder = True
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "payments_placeholder" in blueprint.selected_modules


def test_mapper_excludes_payments_by_default(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "payments_placeholder" not in blueprint.selected_modules


def test_mapper_full_file_plan_has_mobile_and_backend(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    paths = [f.path for f in blueprint.file_plan]
    assert any("package.json" in p for p in paths)
    assert any("main.py" in p for p in paths)


def test_mapper_shell_file_plan_has_only_mobile(caffeine_spec):
    mapper = BlueprintMapper()
    shell_plan = mapper.shell_file_plan(caffeine_spec)
    paths = [f.path for f in shell_plan]
    assert any("package.json" in p for p in paths)
    assert not any("main.py" in p for p in paths)


def test_mapper_includes_env_vars(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    keys = [e.key for e in blueprint.env_vars]
    assert "SECRET_KEY" in keys
    assert "DATABASE_URL" in keys
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && uv run pytest tests/test_blueprint_mapper.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `incubator/backend/app/services/blueprint_mapper.py`**

```python
from app.schemas.form import ArchitectureBlueprint, EnvVar, FilePlan, ProductSpec

MOBILE_BASE_FILES: list[tuple[str, str]] = [
    ("apps/mobile/package.json", "mobile/base/package.json.j2"),
    ("apps/mobile/app.json", "mobile/base/app.json.j2"),
    ("apps/mobile/tsconfig.json", "mobile/base/tsconfig.json.j2"),
    ("apps/mobile/app/_layout.tsx", "mobile/base/app/_layout.tsx.j2"),
    ("apps/mobile/app/(tabs)/_layout.tsx", "mobile/base/app/(tabs)/_layout.tsx.j2"),
    ("apps/mobile/app/(tabs)/index.tsx", "mobile/base/app/(tabs)/index.tsx.j2"),
    ("apps/mobile/lib/api/client.ts", "mobile/base/lib/api/client.ts.j2"),
    ("apps/mobile/lib/storage/session.ts", "mobile/base/lib/storage/session.ts.j2"),
    ("apps/mobile/lib/telemetry/analytics.ts", "mobile/base/lib/telemetry/analytics.ts.j2"),
]

AUTH_MOBILE_FILES: list[tuple[str, str]] = [
    ("apps/mobile/app/(auth)/login.tsx", "mobile/base/app/(auth)/login.tsx.j2"),
    ("apps/mobile/app/(auth)/signup.tsx", "mobile/base/app/(auth)/signup.tsx.j2"),
]

BACKEND_BASE_FILES: list[tuple[str, str]] = [
    ("backend/app/main.py", "backend/base/app/main.py.j2"),
    ("backend/app/core/security.py", "backend/base/app/core/security.py.j2"),
    ("backend/app/db/database.py", "backend/base/app/db/database.py.j2"),
    ("backend/app/models/user.py", "backend/base/app/models/user.py.j2"),
    ("backend/app/schemas/auth.py", "backend/base/app/schemas/auth.py.j2"),
    ("backend/app/auth/service.py", "backend/base/app/auth/service.py.j2"),
    ("backend/app/auth/router.py", "backend/base/app/auth/router.py.j2"),
    ("backend/pyproject.toml", "backend/base/pyproject.toml.j2"),
    ("backend/.env.example", "backend/base/.env.example.j2"),
    ("README.md", "backend/base/README.md.j2"),
]

MODULE_FILES: dict[str, list[tuple[str, str]]] = {
    "payments_placeholder": [
        ("apps/mobile/app/paywall.tsx", "mobile/modules/payments_placeholder/app/paywall.tsx.j2"),
        ("backend/app/api/billing.py", "backend/modules/payments_placeholder/app/api/billing.py.j2"),
        (
            "backend/app/services/billing.py",
            "backend/modules/payments_placeholder/app/services/billing.py.j2",
        ),
    ],
    "list_detail_crud": [
        ("apps/mobile/app/(tabs)/list.tsx", "mobile/modules/list_detail/app/(tabs)/list.tsx.j2"),
        ("apps/mobile/app/(tabs)/detail.tsx", "mobile/modules/list_detail/app/(tabs)/detail.tsx.j2"),
        ("backend/app/api/items.py", "backend/modules/list_detail/app/api/items.py.j2"),
        ("backend/app/models/item.py", "backend/modules/list_detail/app/models/item.py.j2"),
    ],
    "form_flow": [
        (
            "apps/mobile/app/(tabs)/new-entry.tsx",
            "mobile/modules/form_flow/app/(tabs)/new-entry.tsx.j2",
        ),
    ],
    "settings": [
        (
            "apps/mobile/app/(tabs)/settings.tsx",
            "mobile/modules/settings/app/(tabs)/settings.tsx.j2",
        ),
    ],
    "notifications_placeholder": [
        (
            "apps/mobile/lib/notifications.ts",
            "mobile/modules/notifications/lib/notifications.ts.j2",
        ),
    ],
    "local_persistence": [
        ("apps/mobile/lib/db/local.ts", "mobile/base/lib/db/local.ts.j2"),
    ],
    "analytics_hook": [
        ("apps/mobile/lib/telemetry/analytics.ts", "mobile/base/lib/telemetry/analytics.ts.j2"),
    ],
}

BASE_ENV_VARS = [
    EnvVar(key="DATABASE_URL", example_value="sqlite+aiosqlite:///./app.db", description="DB path"),
    EnvVar(key="SECRET_KEY", example_value="change-me-in-production", description="JWT secret"),
    EnvVar(
        key="EXPO_PUBLIC_API_URL", example_value="http://localhost:8000", description="Backend URL"
    ),
]

PAYMENTS_ENV_VARS = [
    EnvVar(key="STRIPE_SECRET_KEY", example_value="sk_test_...", description="Stripe secret key"),
    EnvVar(
        key="STRIPE_WEBHOOK_SECRET", example_value="whsec_...", description="Stripe webhook secret"
    ),
]

ALWAYS_ON_MODULES = ["dashboard", "local_persistence", "analytics_hook"]


class BlueprintMapper:
    def _select_modules(self, spec: ProductSpec) -> list[str]:
        modules = list(ALWAYS_ON_MODULES)
        if spec.auth_required:
            modules.insert(0, "auth")
        if spec.payments_placeholder:
            modules.append("payments_placeholder")
        if spec.notifications:
            modules.append("notifications_placeholder")
        return modules

    def shell_file_plan(self, spec: ProductSpec) -> list[FilePlan]:
        """Mobile-only file plan for the shell pass (no backend)."""
        files = list(MOBILE_BASE_FILES)
        if spec.auth_required:
            files.extend(AUTH_MOBILE_FILES)
        modules = self._select_modules(spec)
        for module in modules:
            if module in MODULE_FILES:
                for path, template in MODULE_FILES[module]:
                    if path.startswith("apps/mobile"):
                        files.append((path, template))
        return [FilePlan(path=p, template=t, context_keys=[]) for p, t in files]

    def map(self, spec: ProductSpec) -> ArchitectureBlueprint:
        """Full file plan for both mobile and backend."""
        modules = self._select_modules(spec)
        files = list(MOBILE_BASE_FILES)
        if spec.auth_required:
            files.extend(AUTH_MOBILE_FILES)
        files.extend(BACKEND_BASE_FILES)
        for module in modules:
            if module in MODULE_FILES:
                files.extend(MODULE_FILES[module])

        file_plan = [FilePlan(path=p, template=t, context_keys=[]) for p, t in files]
        env_vars = list(BASE_ENV_VARS)
        if spec.payments_placeholder:
            env_vars.extend(PAYMENTS_ENV_VARS)

        return ArchitectureBlueprint(
            mobile_framework="expo",
            backend_framework="fastapi",
            selected_modules=modules,
            file_plan=file_plan,
            api_routes=[],
            db_entities=["User"] + [e.name for e in spec.data_entities],
            env_vars=env_vars,
        )
```

- [ ] **Step 4: Run tests**

```bash
cd incubator/backend && uv run pytest tests/test_blueprint_mapper.py -v
```

Expected: `8 passed`.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/services/blueprint_mapper.py incubator/backend/tests/test_blueprint_mapper.py
git commit -m "feat: add blueprint mapper with separate shell and full file plans"
```

---

## Task 13: SSE manager

**Files:**
- Create: `incubator/backend/app/services/sse_manager.py`

Emits events matching the `SSEEvent` frontend type: `{stage, message, done?, final_status?}`.

- [ ] **Step 1: Write `incubator/backend/app/services/sse_manager.py`**

```python
import asyncio
import json
from collections import defaultdict


class SSEManager:
    """Holds per-run async queues for SSE streaming."""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues[run_id].append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        try:
            self._queues[run_id].remove(q)
        except (ValueError, KeyError):
            pass

    async def emit(self, run_id: str, stage: str, message: str) -> None:
        data = json.dumps({"stage": stage, "message": message})
        for q in list(self._queues.get(run_id, [])):
            await q.put(data)

    async def emit_done(self, run_id: str, final_status: str) -> None:
        data = json.dumps({"stage": "done", "message": final_status, "done": True,
                           "final_status": final_status})
        for q in list(self._queues.get(run_id, [])):
            await q.put(data)
            await q.put(None)  # sentinel to close stream


sse_manager = SSEManager()
```

- [ ] **Step 2: Commit**

```bash
git add incubator/backend/app/services/sse_manager.py
git commit -m "feat: add SSE manager for per-run event streaming"
```

---

## Task 14: Pipeline stages

**Files:**
- Create: `incubator/backend/app/pipeline/__init__.py`
- Create: `incubator/backend/app/pipeline/stages.py`
- Create: `incubator/backend/tests/test_pipeline_stages.py`

Each stage is a standalone async function. Stages run as background tasks and update the DB on completion.

- [ ] **Step 1: Write failing tests**

`incubator/backend/tests/test_pipeline_stages.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch

from app.pipeline.stages import run_spec_generation, run_blueprint_generation
from app.schemas.form import FormAnswers


def make_form() -> FormAnswers:
    return FormAnswers(
        app_goal="track caffeine",
        target_user="adults",
        top_3_actions=["log drink", "view total", "set goal"],
        must_have_screens=["dashboard", "add entry"],
        works_offline=True,
        needs_notifications=False,
        core_data_entities=["CaffeineEntry"],
        style_notes="minimal",
        constraints_non_goals="no social",
    )


@pytest.mark.asyncio
async def test_spec_generation_saves_spec_to_db(db_session):
    from app.db.models import Run
    import uuid, json
    run_id = str(uuid.uuid4())
    form = make_form()
    run = Run(
        id=run_id,
        raw_idea="caffeine tracker",
        status="pending",
        form_answers_json=form.model_dump_json(),
    )
    db_session.add(run)
    await db_session.commit()

    mock_spec = {
        "app_name": "Caffeine Tracker",
        "app_slug": "caffeine-tracker",
        "goal": "track caffeine",
        "target_user": "adults",
        "screens": [{"name": "Dashboard", "route": "/", "description": "main"}],
        "features": ["logging"],
        "data_entities": [{"name": "CaffeineEntry", "fields": ["id", "mg", "timestamp"]}],
        "offline_support": True,
        "notifications": False,
        "auth_required": True,
        "payments_placeholder": False,
        "style_notes": "minimal",
        "non_goals": ["social"],
    }

    with patch("app.pipeline.stages.claude.generate_json", AsyncMock(return_value=mock_spec)):
        with patch("app.pipeline.stages.sse_manager.emit", AsyncMock()):
            with patch("app.pipeline.stages.sse_manager.emit_done", AsyncMock()):
                await run_spec_generation(run_id, "caffeine tracker", form)

    from sqlalchemy import select
    result = await db_session.execute(select(Run).where(Run.id == run_id))
    updated = result.scalar_one()
    assert updated.status == "awaiting_spec_review"
    assert updated.product_spec_json is not None
    spec_data = json.loads(updated.product_spec_json)
    assert spec_data["app_name"] == "Caffeine Tracker"


@pytest.mark.asyncio
async def test_blueprint_generation_saves_blueprint(db_session):
    from app.db.models import Run
    from app.schemas.form import ProductSpec, ScreenSpec, EntitySpec
    import uuid, json
    run_id = str(uuid.uuid4())
    spec = ProductSpec(
        app_name="Caffeine Tracker",
        app_slug="caffeine-tracker",
        goal="track caffeine",
        target_user="adults",
        screens=[ScreenSpec(name="Dashboard", route="/", description="main")],
        features=["logging"],
        data_entities=[EntitySpec(name="CaffeineEntry", fields=["id", "mg", "timestamp"])],
        offline_support=True,
        notifications=False,
        auth_required=True,
        payments_placeholder=False,
        style_notes="minimal",
        non_goals=["social"],
    )
    run = Run(
        id=run_id,
        raw_idea="caffeine tracker",
        status="awaiting_spec_review",
        form_answers_json="{}",
        product_spec_json=spec.model_dump_json(),
    )
    db_session.add(run)
    await db_session.commit()

    with patch("app.pipeline.stages.sse_manager.emit", AsyncMock()):
        with patch("app.pipeline.stages.sse_manager.emit_done", AsyncMock()):
            await run_blueprint_generation(run_id, spec)

    from sqlalchemy import select
    result = await db_session.execute(select(Run).where(Run.id == run_id))
    updated = result.scalar_one()
    assert updated.status == "awaiting_blueprint_review"
    assert updated.blueprint_json is not None
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && uv run pytest tests/test_pipeline_stages.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `incubator/backend/app/pipeline/__init__.py`** (empty)

- [ ] **Step 4: Write `incubator/backend/app/pipeline/stages.py`**

```python
import json
from pathlib import Path

from sqlalchemy import select

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
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if run:
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
        await _update_run(run_id, status="failed", error_summary=str(e))
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
        await _update_run(run_id, status="failed", error_summary=str(e))
        await sse_manager.emit_done(run_id, "failed")
        raise


async def run_shell_scaffolding(run_id: str, spec: ProductSpec, blueprint: ArchitectureBlueprint) -> None:
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

        written = scaffolder.scaffold(spec, shell_blueprint, output_dir, extra_context=context_extra)
        await sse_manager.emit(run_id, "shell_scaffolding", f"Wrote {len(written)} files")
        await _update_run(
            run_id,
            status="awaiting_shell_review",
            stage_logs_json=json.dumps([{"stage": "shell_scaffolding", "files": len(written)}]),
        )
        await sse_manager.emit_done(run_id, "awaiting_shell_review")
    except Exception as e:
        await _update_run(run_id, status="failed", error_summary=str(e))
        await sse_manager.emit_done(run_id, "failed")
        raise


async def run_full_scaffolding(run_id: str, spec: ProductSpec, blueprint: ArchitectureBlueprint) -> None:
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
        (incubator_dir / "architecture_blueprint.json").write_text(blueprint.model_dump_json(indent=2))

        await _update_run(
            run_id,
            status="done",
            stage_logs_json=json.dumps([{"stage": "full_scaffolding", "files": len(written)}]),
        )
        await sse_manager.emit(run_id, "full_scaffolding", "App generated successfully")
        await sse_manager.emit_done(run_id, "done")
    except Exception as e:
        await _update_run(run_id, status="failed", error_summary=str(e))
        await sse_manager.emit_done(run_id, "failed")
        raise
```

- [ ] **Step 5: Update `ScaffolderService.scaffold` to accept `extra_context`**

Modify `incubator/backend/app/services/scaffolder.py` — add `extra_context` parameter:

Current signature:
```python
def scaffold(self, spec: ProductSpec, blueprint: ArchitectureBlueprint, output_dir: Path) -> list[str]:
    context = self._build_context(spec, blueprint)
```

New signature:
```python
def scaffold(
    self,
    spec: ProductSpec,
    blueprint: ArchitectureBlueprint,
    output_dir: Path,
    extra_context: dict | None = None,
) -> list[str]:
    context = self._build_context(spec, blueprint)
    if extra_context:
        context.update(extra_context)
```

- [ ] **Step 6: Add `shell_mode` default to scaffolder context so `StrictUndefined` doesn't raise for templates that don't use it**

In `_build_context`, add `"shell_mode": False` to the returned dict.

- [ ] **Step 7: Run tests**

```bash
cd incubator/backend && uv run pytest tests/test_pipeline_stages.py -v
```

Expected: `2 passed`.

- [ ] **Step 8: Run full suite**

```bash
cd incubator/backend && uv run pytest -v && uv run ruff check .
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add incubator/backend/app/pipeline/ incubator/backend/app/services/scaffolder.py \
        incubator/backend/tests/test_pipeline_stages.py
git commit -m "feat: add staged pipeline with human review gates between each phase"
```

---

## Task 15: Approval API endpoints + run schemas

**Files:**
- Modify: `incubator/backend/app/schemas/run.py` — add approval request schemas
- Modify: `incubator/backend/app/api/runs.py` — add approval endpoints + pipeline triggers

- [ ] **Step 1: Add approval schemas to `incubator/backend/app/schemas/run.py`**

Append to the existing file:
```python
from app.schemas.form import ArchitectureBlueprint, ProductSpec


class ApproveSpecRequest(BaseModel):
    spec: ProductSpec


class ApproveBlueprintRequest(BaseModel):
    blueprint: ArchitectureBlueprint


class ApproveShellRequest(BaseModel):
    pass  # no body needed — approval is the action
```

- [ ] **Step 2: Write full replacement of `incubator/backend/app/api/runs.py`**

```python
import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Run
from app.schemas.form import ArchitectureBlueprint, FormAnswers, ProductSpec
from app.schemas.run import (
    ApproveBlueprintRequest,
    ApproveShellRequest,
    ApproveSpecRequest,
    CreateRunRequest,
    RunListItem,
    RunResponse,
)
from app.services.sse_manager import sse_manager

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(body: CreateRunRequest, session: AsyncSession = Depends(get_session)):
    run_id = str(uuid.uuid4())
    run = Run(
        id=run_id,
        raw_idea=body.raw_idea,
        status="pending",
        app_name=None,
        form_answers_json=body.form_answers.model_dump_json(),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    async def _kick_spec():
        from app.pipeline.stages import run_spec_generation
        await run_spec_generation(run_id, body.raw_idea, body.form_answers)

    asyncio.create_task(_kick_spec())
    return run


@router.post("/{run_id}/approve-spec", response_model=RunResponse)
async def approve_spec(
    run_id: str, body: ApproveSpecRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_spec_review":
        raise HTTPException(status_code=409, detail=f"Run is in status '{run.status}', expected 'awaiting_spec_review'")

    run.product_spec_json = body.spec.model_dump_json()
    run.app_name = body.spec.app_name
    await session.commit()
    await session.refresh(run)

    async def _kick_blueprint():
        from app.pipeline.stages import run_blueprint_generation
        await run_blueprint_generation(run_id, body.spec)

    asyncio.create_task(_kick_blueprint())
    return run


@router.post("/{run_id}/approve-blueprint", response_model=RunResponse)
async def approve_blueprint(
    run_id: str, body: ApproveBlueprintRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_blueprint_review":
        raise HTTPException(status_code=409, detail=f"Run is in status '{run.status}', expected 'awaiting_blueprint_review'")
    if not run.product_spec_json:
        raise HTTPException(status_code=422, detail="No product spec found on run")

    run.blueprint_json = body.blueprint.model_dump_json()
    await session.commit()
    await session.refresh(run)

    spec = ProductSpec.model_validate_json(run.product_spec_json)

    async def _kick_shell():
        from app.pipeline.stages import run_shell_scaffolding
        await run_shell_scaffolding(run_id, spec, body.blueprint)

    asyncio.create_task(_kick_shell())
    return run


@router.post("/{run_id}/approve-shell", response_model=RunResponse)
async def approve_shell(
    run_id: str, body: ApproveShellRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_shell_review":
        raise HTTPException(status_code=409, detail=f"Run is in status '{run.status}', expected 'awaiting_shell_review'")
    if not run.product_spec_json or not run.blueprint_json:
        raise HTTPException(status_code=422, detail="Missing spec or blueprint")

    spec = ProductSpec.model_validate_json(run.product_spec_json)
    blueprint = ArchitectureBlueprint.model_validate_json(run.blueprint_json)

    async def _kick_full():
        from app.pipeline.stages import run_full_scaffolding
        await run_full_scaffolding(run_id, spec, blueprint)

    asyncio.create_task(_kick_full())
    await session.refresh(run)
    return run


@router.get("", response_model=list[RunListItem])
async def list_runs(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Run).order_by(Run.created_at.desc()))
    return result.scalars().all()


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    q = sse_manager.subscribe(run_id)

    async def event_generator():
        try:
            while True:
                data = await asyncio.wait_for(q.get(), timeout=30.0)
                if data is None:
                    break
                yield f"data: {data}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'stage': 'heartbeat', 'message': 'ping'})}\n\n"
        finally:
            sse_manager.unsubscribe(run_id, q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{run_id}/artifacts")
async def get_artifacts(run_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "product_spec": json.loads(run.product_spec_json) if run.product_spec_json else None,
        "blueprint": json.loads(run.blueprint_json) if run.blueprint_json else None,
        "stage_logs": json.loads(run.stage_logs_json) if run.stage_logs_json else [],
    }
```

- [ ] **Step 3: Update frontend types for new statuses**

Modify `incubator/frontend/src/types/index.ts` — update `RunStatus`:

```typescript
export type RunStatus =
  | 'pending'
  | 'generating_spec'
  | 'awaiting_spec_review'
  | 'generating_blueprint'
  | 'awaiting_blueprint_review'
  | 'generating_shell'
  | 'awaiting_shell_review'
  | 'building_full'
  | 'done'
  | 'failed'
```

- [ ] **Step 4: Update frontend API client for new endpoints**

Add to `incubator/frontend/src/api/client.ts`:

```typescript
approveSpec: (id: string, spec: unknown) =>
  request<Run>(`/runs/${id}/approve-spec`, { method: 'POST', body: JSON.stringify({ spec }) }),

approveBlueprint: (id: string, blueprint: unknown) =>
  request<Run>(`/runs/${id}/approve-blueprint`, { method: 'POST', body: JSON.stringify({ blueprint }) }),

approveShell: (id: string) =>
  request<Run>(`/runs/${id}/approve-shell`, { method: 'POST', body: JSON.stringify({}) }),

getArtifacts: (id: string) =>
  request<{ product_spec: unknown; blueprint: unknown; stage_logs: unknown[] }>(`/runs/${id}/artifacts`),
```

- [ ] **Step 5: Run all tests + lint**

```bash
cd incubator/backend && uv run pytest -v && uv run ruff check .
cd incubator/frontend && npm run build
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add incubator/backend/app/api/runs.py incubator/backend/app/schemas/run.py \
        incubator/frontend/src/types/index.ts incubator/frontend/src/api/client.ts
git commit -m "feat: add approval endpoints for spec/blueprint/shell review gates"
```

---

## Phase 3 Complete

**What was built:**
- Claude API client with Opus routing
- Blueprint mapper with separate shell (mobile-only) and full file plans
- SSE manager emitting `{stage, message, done?, final_status?}` events
- Four-stage human-gated pipeline: spec → blueprint → shell → full app
- Approval endpoints: POST approve-spec, approve-blueprint, approve-shell
- SSE stream endpoint for live progress
- Frontend RunStatus extended with all intermediate states

**Review questions:**
1. Want the spec generation prompt tweaked before Phase 4?
2. Phase 4 adds QA (ruff + pytest on generated code) — should QA run after shell, after full build, or both?
