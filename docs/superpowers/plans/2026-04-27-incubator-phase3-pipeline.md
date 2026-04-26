# Agentic App Incubator — Phase 3: Generation Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the LangGraph pipeline with all nodes, Claude API integration, and SSE streaming so a submitted run actually generates a repo.

**Architecture:** LangGraph `StateGraph[RunState]` with 10 nodes. Each node is a thin async function that calls a service class. Claude API service routes to Opus (spec/arch nodes) or Sonnet (all others). Pipeline runs in a background asyncio task; SSE pushes events to the frontend.

**Tech Stack:** LangGraph, Anthropic Python SDK, sse-starlette, asyncio

**Prerequisite:** Phase 1 and Phase 2 complete.

---

## File Map

**Create:**
- `incubator/backend/app/services/claude_client.py`
- `incubator/backend/app/pipeline/state.py`
- `incubator/backend/app/pipeline/nodes.py`
- `incubator/backend/app/pipeline/graph.py`
- `incubator/backend/app/services/sse_manager.py`
- `incubator/backend/app/services/blueprint_mapper.py`
- `incubator/backend/tests/test_claude_client.py`
- `incubator/backend/tests/test_pipeline_nodes.py`

**Modify:**
- `incubator/backend/app/api/runs.py` — add stream endpoint + async pipeline trigger
- `incubator/backend/app/schemas/pipeline.py` — already done in Phase 1

---

## Task 11: Claude API service

**Files:**
- Create: `incubator/backend/app/services/claude_client.py`
- Create: `incubator/backend/tests/test_claude_client.py`

- [ ] **Step 1: Write failing test**

`incubator/backend/tests/test_claude_client.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.claude_client import ClaudeClient


@pytest.mark.asyncio
async def test_generate_uses_opus_for_spec():
    client = ClaudeClient()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"app_name": "Test"}')]

    with patch.object(client._opus, 'messages') as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_spec("build a tracker app", "{}", model="opus")

    mock_msgs.create.assert_called_once()
    call_kwargs = mock_msgs.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-opus-4-7"


@pytest.mark.asyncio
async def test_generate_uses_sonnet_for_scaffold():
    client = ClaudeClient()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="some code")]

    with patch.object(client._sonnet, 'messages') as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_text("write a file", model="sonnet")

    mock_msgs.create.assert_called_once()
    call_kwargs = mock_msgs.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_claude_client.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `incubator/backend/app/services/claude_client.py`**

```python
import json
from anthropic import AsyncAnthropic
from app.config import settings

OPUS_MODEL = "claude-opus-4-7"
SONNET_MODEL = "claude-sonnet-4-6"

SPEC_SYSTEM = """You are an expert mobile app architect. Generate structured JSON specs from app ideas.
Always respond with valid JSON only. No markdown fences, no explanation."""

SCAFFOLD_SYSTEM = """You are an expert mobile and backend developer.
Generate clean, production-quality code files as requested. Respond with the file content only."""


class ClaudeClient:
    def __init__(self) -> None:
        self._opus = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._sonnet = AsyncAnthropic(api_key=settings.anthropic_api_key)

    def _client(self, model: str) -> AsyncAnthropic:
        return self._opus if model == "opus" else self._sonnet

    def _model_id(self, model: str) -> str:
        return OPUS_MODEL if model == "opus" else SONNET_MODEL

    async def generate_spec(self, prompt: str, context: str, model: str = "opus") -> str:
        client = self._client(model)
        response = await client.messages.create(
            model=self._model_id(model),
            max_tokens=4096,
            system=SPEC_SYSTEM,
            messages=[{"role": "user", "content": f"{context}\n\n{prompt}"}],
        )
        return response.content[0].text

    async def generate_text(self, prompt: str, model: str = "sonnet", system: str = SCAFFOLD_SYSTEM) -> str:
        client = self._client(model)
        response = await client.messages.create(
            model=self._model_id(model),
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def generate_json(self, prompt: str, model: str = "opus") -> dict:
        text = await self.generate_spec(prompt, "", model=model)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
```

- [ ] **Step 4: Run tests**

```bash
cd incubator/backend && pytest tests/test_claude_client.py -v
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/services/claude_client.py incubator/backend/tests/test_claude_client.py
git commit -m "feat: add Claude API client with Opus/Sonnet routing"
```

---

## Task 12: Blueprint mapper service

**Files:**
- Create: `incubator/backend/app/services/blueprint_mapper.py`
- Create: `incubator/backend/tests/test_blueprint_mapper.py`

The blueprint mapper converts a `ProductSpec` into an `ArchitectureBlueprint` by selecting modules and building a `file_plan` list.

- [ ] **Step 1: Write failing test**

`incubator/backend/tests/test_blueprint_mapper.py`:
```python
import pytest
from app.services.blueprint_mapper import BlueprintMapper
from app.schemas.form import ProductSpec, ScreenSpec, EntitySpec


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


def test_mapper_always_includes_auth_module(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "auth" in blueprint.selected_modules


def test_mapper_always_includes_dashboard(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "dashboard" in blueprint.selected_modules


def test_mapper_includes_payments_when_spec_says_so(caffeine_spec):
    caffeine_spec.payments_placeholder = True
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "payments_placeholder" in blueprint.selected_modules


def test_mapper_excludes_payments_by_default(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert "payments_placeholder" not in blueprint.selected_modules


def test_mapper_produces_file_plan(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    assert len(blueprint.file_plan) > 0
    paths = [f.path for f in blueprint.file_plan]
    assert any("package.json" in p for p in paths)
    assert any("main.py" in p for p in paths)


def test_mapper_includes_env_vars(caffeine_spec):
    mapper = BlueprintMapper()
    blueprint = mapper.map(caffeine_spec)
    keys = [e.key for e in blueprint.env_vars]
    assert "SECRET_KEY" in keys
    assert "DATABASE_URL" in keys
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_blueprint_mapper.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `incubator/backend/app/services/blueprint_mapper.py`**

```python
from app.schemas.form import ProductSpec, ArchitectureBlueprint, FilePlan, APIRoute, EnvVar

ALWAYS_ON_MODULES = ["auth", "dashboard", "settings", "local_persistence", "analytics_hook"]

MOBILE_BASE_FILES = [
    ("apps/mobile/package.json", "mobile/base/package.json.j2"),
    ("apps/mobile/app.json", "mobile/base/app.json.j2"),
    ("apps/mobile/tsconfig.json", "mobile/base/tsconfig.json.j2"),
    ("apps/mobile/app/_layout.tsx", "mobile/base/app/_layout.tsx.j2"),
    ("apps/mobile/app/(auth)/login.tsx", "mobile/base/app/(auth)/login.tsx.j2"),
    ("apps/mobile/app/(auth)/signup.tsx", "mobile/base/app/(auth)/signup.tsx.j2"),
    ("apps/mobile/app/(tabs)/_layout.tsx", "mobile/base/app/(tabs)/_layout.tsx.j2"),
    ("apps/mobile/app/(tabs)/index.tsx", "mobile/base/app/(tabs)/index.tsx.j2"),
    ("apps/mobile/lib/api/client.ts", "mobile/base/lib/api/client.ts.j2"),
    ("apps/mobile/lib/storage/session.ts", "mobile/base/lib/storage/session.ts.j2"),
    ("apps/mobile/lib/telemetry/analytics.ts", "mobile/base/lib/telemetry/analytics.ts.j2"),
]

BACKEND_BASE_FILES = [
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
        ("backend/app/services/billing.py", "backend/modules/payments_placeholder/app/services/billing.py.j2"),
    ],
    "list_detail_crud": [
        ("apps/mobile/app/(tabs)/list.tsx", "mobile/modules/list_detail/app/(tabs)/list.tsx.j2"),
        ("apps/mobile/app/(tabs)/detail.tsx", "mobile/modules/list_detail/app/(tabs)/detail.tsx.j2"),
        ("backend/app/api/items.py", "backend/modules/list_detail/app/api/items.py.j2"),
        ("backend/app/models/item.py", "backend/modules/list_detail/app/models/item.py.j2"),
    ],
    "form_flow": [
        ("apps/mobile/app/(tabs)/new-entry.tsx", "mobile/modules/form_flow/app/(tabs)/new-entry.tsx.j2"),
    ],
    "settings": [
        ("apps/mobile/app/(tabs)/settings.tsx", "mobile/modules/settings/app/(tabs)/settings.tsx.j2"),
    ],
    "notifications_placeholder": [
        ("apps/mobile/lib/notifications.ts", "mobile/modules/notifications/lib/notifications.ts.j2"),
    ],
}

BASE_ENV_VARS = [
    EnvVar(key="DATABASE_URL", example_value="sqlite+aiosqlite:///./app.db", description="SQLite DB path"),
    EnvVar(key="SECRET_KEY", example_value="change-me-in-production", description="JWT signing secret"),
    EnvVar(key="EXPO_PUBLIC_API_URL", example_value="http://localhost:8000", description="Backend API URL"),
]

PAYMENTS_ENV_VARS = [
    EnvVar(key="STRIPE_SECRET_KEY", example_value="sk_test_...", description="Stripe secret key"),
    EnvVar(key="STRIPE_WEBHOOK_SECRET", example_value="whsec_...", description="Stripe webhook secret"),
]


class BlueprintMapper:
    def map(self, spec: ProductSpec) -> ArchitectureBlueprint:
        modules = list(ALWAYS_ON_MODULES)
        if spec.payments_placeholder and "payments_placeholder" not in modules:
            modules.append("payments_placeholder")
        if spec.notifications and "notifications_placeholder" not in modules:
            modules.append("notifications_placeholder")

        all_files = list(MOBILE_BASE_FILES) + list(BACKEND_BASE_FILES)
        for module in modules:
            if module in MODULE_FILES:
                all_files.extend(MODULE_FILES[module])

        file_plan = [
            FilePlan(path=path, template=template, context_keys=[])
            for path, template in all_files
        ]

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
cd incubator/backend && pytest tests/test_blueprint_mapper.py -v
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/services/blueprint_mapper.py incubator/backend/tests/test_blueprint_mapper.py
git commit -m "feat: add blueprint mapper that converts ProductSpec to ArchitectureBlueprint"
```

---

## Task 13: SSE manager

**Files:**
- Create: `incubator/backend/app/services/sse_manager.py`

- [ ] **Step 1: Write `incubator/backend/app/services/sse_manager.py`**

```python
import asyncio
import json
from datetime import datetime, timezone
from collections import defaultdict


class SSEManager:
    """Holds per-run event queues for SSE streaming."""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues[run_id].append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        if run_id in self._queues:
            self._queues[run_id].discard(q) if hasattr(self._queues[run_id], 'discard') else None
            try:
                self._queues[run_id].remove(q)
            except ValueError:
                pass

    async def emit(self, run_id: str, event: dict) -> None:
        event["ts"] = datetime.now(timezone.utc).isoformat()
        data = json.dumps(event)
        for q in list(self._queues.get(run_id, [])):
            await q.put(data)

    async def emit_stage(self, run_id: str, stage: str, status: str) -> None:
        await self.emit(run_id, {"stage": stage, "status": status})

    async def emit_log(self, run_id: str, message: str) -> None:
        await self.emit(run_id, {"log": message})

    async def emit_done(self, run_id: str, final_status: str) -> None:
        await self.emit(run_id, {"done": True, "final_status": final_status})
        for q in list(self._queues.get(run_id, [])):
            await q.put(None)  # sentinel to close stream


sse_manager = SSEManager()
```

- [ ] **Step 2: Commit**

```bash
git add incubator/backend/app/services/sse_manager.py
git commit -m "feat: add SSE manager for per-run event streaming"
```

---

## Task 14: LangGraph pipeline nodes

**Files:**
- Create: `incubator/backend/app/pipeline/nodes.py`
- Create: `incubator/backend/tests/test_pipeline_nodes.py`

- [ ] **Step 1: Write failing tests**

`incubator/backend/tests/test_pipeline_nodes.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from app.pipeline.nodes import run_intake, run_spec_generator, run_architecture_mapper
from app.schemas.pipeline import RunState
from app.schemas.form import FormAnswers


def make_state(overrides: dict = {}) -> RunState:
    form = FormAnswers(
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
    base: RunState = {
        "run_id": "test-123",
        "raw_idea": "caffeine tracker app",
        "form_answers": form,
        "product_spec": None,
        "architecture_blueprint": None,
        "selected_modules": [],
        "file_plan": [],
        "changed_files": [],
        "qa_results": None,
        "retry_count": 0,
        "error_history": [],
        "final_status": "pending",
        "stage_logs": [],
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_intake_sets_status_running():
    state = make_state()
    result = await run_intake(state)
    assert result["final_status"] == "running"


@pytest.mark.asyncio
async def test_spec_generator_parses_json_from_claude():
    state = make_state({"final_status": "running"})
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

    with patch("app.pipeline.nodes.claude.generate_json", AsyncMock(return_value=mock_spec)):
        with patch("app.pipeline.nodes.sse_manager.emit_stage", AsyncMock()):
            with patch("app.pipeline.nodes.sse_manager.emit_log", AsyncMock()):
                result = await run_spec_generator(state)

    assert result["product_spec"] is not None
    assert result["product_spec"].app_name == "Caffeine Tracker"


@pytest.mark.asyncio
async def test_architecture_mapper_produces_blueprint():
    from app.schemas.form import ProductSpec, ScreenSpec, EntitySpec
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
    state = make_state({"final_status": "running", "product_spec": spec})

    with patch("app.pipeline.nodes.sse_manager.emit_stage", AsyncMock()):
        with patch("app.pipeline.nodes.sse_manager.emit_log", AsyncMock()):
            result = await run_architecture_mapper(state)

    assert result["architecture_blueprint"] is not None
    assert "auth" in result["selected_modules"]
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_pipeline_nodes.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `incubator/backend/app/pipeline/nodes.py`**

```python
import json
from pathlib import Path
from app.schemas.pipeline import RunState, QACheck, QAResults
from app.schemas.form import ProductSpec, ArchitectureBlueprint
from app.services.claude_client import ClaudeClient
from app.services.scaffolder import ScaffolderService
from app.services.blueprint_mapper import BlueprintMapper
from app.services.sse_manager import sse_manager
from app.config import settings

claude = ClaudeClient()
scaffolder = ScaffolderService()
mapper = BlueprintMapper()

SPEC_PROMPT = """Given this app idea and structured form, generate a ProductSpec JSON object.

App idea: {raw_idea}

Form answers:
{form_json}

Return a JSON object matching this schema exactly:
{{
  "app_name": "string",
  "app_slug": "string (kebab-case)",
  "goal": "string",
  "target_user": "string",
  "screens": [{{"name": "string", "route": "string", "description": "string"}}],
  "features": ["string"],
  "data_entities": [{{"name": "string", "fields": ["string"]}}],
  "offline_support": boolean,
  "notifications": boolean,
  "auth_required": true,
  "payments_placeholder": boolean,
  "style_notes": "string",
  "non_goals": ["string"]
}}"""


async def run_intake(state: RunState) -> dict:
    return {"final_status": "running", "stage_logs": state["stage_logs"] + [{"stage": "intake", "status": "completed"}]}


async def run_spec_generator(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "spec_generator", "started")
    prompt = SPEC_PROMPT.format(
        raw_idea=state["raw_idea"],
        form_json=state["form_answers"].model_dump_json(indent=2),
    )
    spec_dict = await claude.generate_json(prompt, model="opus")
    spec = ProductSpec.model_validate(spec_dict)
    await sse_manager.emit_log(state["run_id"], f"Generated spec: {spec.app_name}")
    await sse_manager.emit_stage(state["run_id"], "spec_generator", "completed")
    return {"product_spec": spec, "stage_logs": state["stage_logs"] + [{"stage": "spec_generator", "status": "completed"}]}


async def run_spec_validator(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "spec_validator", "started")
    spec = state["product_spec"]
    assert spec is not None, "spec_generator must run first"
    assert spec.auth_required is True, "auth_required must always be True"
    assert len(spec.screens) > 0, "spec must define at least one screen"
    await sse_manager.emit_stage(state["run_id"], "spec_validator", "completed")
    return {"stage_logs": state["stage_logs"] + [{"stage": "spec_validator", "status": "completed"}]}


async def run_architecture_mapper(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "architecture_mapper", "started")
    spec = state["product_spec"]
    assert spec is not None
    blueprint = mapper.map(spec)
    await sse_manager.emit_log(state["run_id"], f"Selected modules: {', '.join(blueprint.selected_modules)}")
    await sse_manager.emit_log(state["run_id"], f"File plan: {len(blueprint.file_plan)} files")
    await sse_manager.emit_stage(state["run_id"], "architecture_mapper", "completed")
    return {
        "architecture_blueprint": blueprint,
        "selected_modules": blueprint.selected_modules,
        "file_plan": blueprint.file_plan,
        "stage_logs": state["stage_logs"] + [{"stage": "architecture_mapper", "status": "completed"}],
    }


async def run_template_selector(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "template_selector", "started")
    await sse_manager.emit_stage(state["run_id"], "template_selector", "completed")
    return {"stage_logs": state["stage_logs"] + [{"stage": "template_selector", "status": "completed"}]}


async def run_scaffolder(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "scaffolder", "started")
    spec = state["product_spec"]
    blueprint = state["architecture_blueprint"]
    assert spec and blueprint

    output_dir = settings.generated_apps_path / state["run_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    written = scaffolder.scaffold(spec, blueprint, output_dir)
    for f in written:
        await sse_manager.emit_log(state["run_id"], f"Wrote: {Path(f).relative_to(output_dir)}")

    await sse_manager.emit_stage(state["run_id"], "scaffolder", "completed")
    return {
        "changed_files": written,
        "stage_logs": state["stage_logs"] + [{"stage": "scaffolder", "status": "completed"}],
    }


async def run_task_planner(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "task_planner", "started")
    await sse_manager.emit_stage(state["run_id"], "task_planner", "completed")
    return {"stage_logs": state["stage_logs"] + [{"stage": "task_planner", "status": "completed"}]}


async def run_repo_editor(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "repo_editor", "started")
    await sse_manager.emit_stage(state["run_id"], "repo_editor", "completed")
    return {"stage_logs": state["stage_logs"] + [{"stage": "repo_editor", "status": "completed"}]}


async def run_delivery_packager(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "delivery_packager", "started")
    spec = state["product_spec"]
    blueprint = state["architecture_blueprint"]
    output_dir = settings.generated_apps_path / state["run_id"]

    incubator_dir = output_dir / "incubator"
    incubator_dir.mkdir(parents=True, exist_ok=True)

    if spec:
        (incubator_dir / "product_spec.json").write_text(spec.model_dump_json(indent=2))
    if blueprint:
        (incubator_dir / "architecture_blueprint.json").write_text(blueprint.model_dump_json(indent=2))
    if state.get("qa_results"):
        (incubator_dir / "qa_report.json").write_text(state["qa_results"].model_dump_json(indent=2))

    gen_report = {
        "run_id": state["run_id"],
        "app_name": spec.app_name if spec else None,
        "files_written": len(state["changed_files"]),
        "modules": state["selected_modules"],
        "stages": state["stage_logs"],
        "final_status": state["final_status"],
    }
    (incubator_dir / "generation_report.json").write_text(json.dumps(gen_report, indent=2))

    await sse_manager.emit_log(state["run_id"], "Artifacts written to incubator/")
    await sse_manager.emit_stage(state["run_id"], "delivery_packager", "completed")
    await sse_manager.emit_done(state["run_id"], "done")
    return {
        "final_status": "done",
        "stage_logs": state["stage_logs"] + [{"stage": "delivery_packager", "status": "completed"}],
    }


async def run_failure_handler(state: RunState) -> dict:
    await sse_manager.emit_log(state["run_id"], f"Pipeline failed: {state['error_history']}")
    await sse_manager.emit_done(state["run_id"], "failed")
    return {"final_status": "failed"}
```

- [ ] **Step 4: Run tests**

```bash
cd incubator/backend && pytest tests/test_pipeline_nodes.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/pipeline/nodes.py incubator/backend/tests/test_pipeline_nodes.py
git commit -m "feat: add LangGraph pipeline nodes for all generation stages"
```

---

## Task 15: LangGraph graph wiring

**Files:**
- Create: `incubator/backend/app/pipeline/graph.py`

- [ ] **Step 1: Write `incubator/backend/app/pipeline/graph.py`**

```python
from langgraph.graph import StateGraph, END
from app.schemas.pipeline import RunState
from app.pipeline.nodes import (
    run_intake,
    run_spec_generator,
    run_spec_validator,
    run_architecture_mapper,
    run_template_selector,
    run_scaffolder,
    run_task_planner,
    run_repo_editor,
    run_delivery_packager,
    run_failure_handler,
)


def build_graph() -> StateGraph:
    graph = StateGraph(RunState)

    graph.add_node("intake", run_intake)
    graph.add_node("spec_generator", run_spec_generator)
    graph.add_node("spec_validator", run_spec_validator)
    graph.add_node("architecture_mapper", run_architecture_mapper)
    graph.add_node("template_selector", run_template_selector)
    graph.add_node("scaffolder", run_scaffolder)
    graph.add_node("task_planner", run_task_planner)
    graph.add_node("repo_editor", run_repo_editor)
    graph.add_node("delivery_packager", run_delivery_packager)
    graph.add_node("failure_handler", run_failure_handler)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "spec_generator")
    graph.add_edge("spec_generator", "spec_validator")
    graph.add_edge("spec_validator", "architecture_mapper")
    graph.add_edge("architecture_mapper", "template_selector")
    graph.add_edge("template_selector", "scaffolder")
    graph.add_edge("scaffolder", "task_planner")
    graph.add_edge("task_planner", "repo_editor")
    graph.add_edge("repo_editor", "delivery_packager")
    graph.add_edge("delivery_packager", END)
    graph.add_edge("failure_handler", END)

    return graph


pipeline = build_graph().compile()
```

Note: the `qa_runner` and `fix_loop` nodes are added in Phase 4 between `repo_editor` and `delivery_packager`.

- [ ] **Step 2: Verify graph builds**

```python
# quick smoke test in Python REPL
cd incubator/backend
python -c "from app.pipeline.graph import pipeline; print('graph compiled ok')"
```

Expected: `graph compiled ok`

- [ ] **Step 3: Commit**

```bash
git add incubator/backend/app/pipeline/graph.py
git commit -m "feat: wire LangGraph pipeline graph with all nodes"
```

---

## Task 16: Async pipeline runner + SSE API endpoints

**Files:**
- Modify: `incubator/backend/app/api/runs.py`

- [ ] **Step 1: Write `incubator/backend/app/api/runs.py`** (full replacement)

```python
import asyncio
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_session
from app.db.models import Run
from app.schemas.run import CreateRunRequest, RunResponse, RunListItem
from app.schemas.pipeline import RunState
from app.services.sse_manager import sse_manager

router = APIRouter(prefix="/api/runs", tags=["runs"])


async def _run_pipeline(run_id: str, state: RunState) -> None:
    from app.pipeline.graph import pipeline
    from app.db.database import AsyncSessionLocal
    try:
        final_state = await pipeline.ainvoke(state)
        status = final_state.get("final_status", "done")
    except Exception as e:
        await sse_manager.emit_log(run_id, f"Pipeline error: {e}")
        await sse_manager.emit_done(run_id, "failed")
        status = "failed"
        final_state = {"error_history": [str(e)], "stage_logs": []}

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if run:
            run.status = status
            run.updated_at = datetime.utcnow()
            if final_state.get("product_spec"):
                run.app_name = final_state["product_spec"].app_name
                run.product_spec_json = final_state["product_spec"].model_dump_json()
            if final_state.get("architecture_blueprint"):
                run.blueprint_json = final_state["architecture_blueprint"].model_dump_json()
            if final_state.get("qa_results"):
                run.qa_report_json = final_state["qa_results"].model_dump_json()
            if final_state.get("error_history"):
                run.error_summary = "\n".join(final_state["error_history"])
            run.stage_logs_json = json.dumps(final_state.get("stage_logs", []))
            await session.commit()


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(body: CreateRunRequest, session: AsyncSession = Depends(get_session)):
    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    run = Run(
        id=run_id,
        raw_idea=body.raw_idea,
        status="pending",
        app_name=None,
        form_answers_json=body.form_answers.model_dump_json(),
        created_at=now,
        updated_at=now,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    initial_state: RunState = {
        "run_id": run_id,
        "raw_idea": body.raw_idea,
        "form_answers": body.form_answers,
        "product_spec": None,
        "architecture_blueprint": None,
        "selected_modules": [],
        "file_plan": [],
        "changed_files": [],
        "qa_results": None,
        "retry_count": 0,
        "error_history": [],
        "final_status": "pending",
        "stage_logs": [],
    }
    asyncio.create_task(_run_pipeline(run_id, initial_state))
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
            yield f"data: {json.dumps({'heartbeat': True})}\n\n"
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


@router.get("/{run_id}/qa")
async def get_qa_report(run_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "qa_report": json.loads(run.qa_report_json) if run.qa_report_json else None,
        "error_summary": run.error_summary,
    }
```

- [ ] **Step 2: Run all tests**

```bash
cd incubator/backend && pytest -v
```

Expected: all pass (API tests may skip pipeline execution since it's mocked via DB state).

- [ ] **Step 3: Manual integration test**

```bash
# Terminal 1
cd incubator/backend && ANTHROPIC_API_KEY=your-key uvicorn app.main:app --reload

# Terminal 2 — create a run
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "raw_idea": "track caffeine intake",
    "form_answers": {
      "app_goal": "reduce caffeine consumption",
      "target_user": "health-conscious adults",
      "top_3_actions": ["log drink", "view daily total", "set reduction goal"],
      "must_have_screens": ["dashboard", "add entry", "history"],
      "works_offline": true,
      "needs_notifications": false,
      "core_data_entities": ["CaffeineEntry", "DailyGoal"],
      "style_notes": "clean minimal",
      "constraints_non_goals": "no social features",
      "include_payments_placeholder": false,
      "auth_required": true
    }
  }'

# Terminal 3 — stream events (replace RUN_ID)
curl -N http://localhost:8000/api/runs/RUN_ID/stream
```

Expected: SSE events appear as pipeline progresses.

- [ ] **Step 4: Commit**

```bash
git add incubator/backend/app/api/runs.py
git commit -m "feat: add async pipeline runner and SSE streaming endpoint"
```

---

## Phase 3 Complete

**What was built:**
- Claude API service with Opus/Sonnet routing
- Blueprint mapper converting `ProductSpec` → `ArchitectureBlueprint`
- SSE manager for per-run event queues
- All 9 LangGraph nodes (QA nodes added in Phase 4)
- LangGraph graph compiled and wired
- Async pipeline runner triggered on run creation
- SSE stream endpoint + artifacts/QA endpoints

**Review questions:**
1. Want the spec generation prompt tweaked before Phase 4?
2. Should `run_repo_editor` call Claude to do targeted edits, or is template scaffolding sufficient for v1?
