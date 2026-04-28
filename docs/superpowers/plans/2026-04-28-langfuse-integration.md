# Langfuse Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Langfuse cloud tracing to the app-incubator pipeline so every pipeline run produces a Langfuse session with one trace per stage and one generation per LLM call.

**Architecture:** Decorate `ClaudeClient` methods with `@observe(as_type="generation")` and pipeline stage functions with `@observe()`. Each stage sets `session_id=run_id` on its trace so all stages of one pipeline run are grouped in the Langfuse Sessions view. Config is loaded via pydantic-settings and forwarded to `os.environ` in `config.py` so the Langfuse SDK can auto-discover keys.

**Tech Stack:** `langfuse>=2.0.0` (PyPI), `langfuse.decorators.observe`, `langfuse.decorators.langfuse_context`, pydantic-settings, FastAPI.

---

## File Map

| Action | File |
|--------|------|
| Modify | `incubator/backend/pyproject.toml` |
| Modify | `incubator/backend/app/config.py` |
| Modify | `incubator/backend/.env` |
| Modify | `incubator/backend/app/services/claude_client.py` |
| Modify | `incubator/backend/app/pipeline/stages.py` |
| Modify | `incubator/backend/tests/test_claude_client.py` |
| Modify | `CLAUDE.md` |
| Modify | `.claude/workspace/index.md` |

---

## Task 1: Install langfuse and wire config

**Files:**
- Modify: `incubator/backend/pyproject.toml`
- Modify: `incubator/backend/app/config.py`
- Modify: `incubator/backend/.env`

- [ ] **Step 1: Add langfuse to pyproject.toml**

In `incubator/backend/pyproject.toml`, add to the `dependencies` list:

```toml
"langfuse>=2.0.0",
```

Full dependencies block after change:

```toml
dependencies = [
    "fastapi[standard]>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "aiosqlite>=0.20.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.0.0",
    "langgraph>=0.1.0",
    "anthropic>=0.28.0",
    "langchain-anthropic>=0.1.0",
    "jinja2>=3.1.4",
    "python-dotenv>=1.0.0",
    "sse-starlette>=1.8.0",
    "httpx>=0.28.1",
    "langfuse>=2.0.0",
]
```

- [ ] **Step 2: Install**

```bash
cd incubator/backend && source .venv/bin/activate && pip install langfuse
```

Expected: `Successfully installed langfuse-2.x.x` (plus deps).

- [ ] **Step 3: Add settings to config.py**

Replace `incubator/backend/app/config.py` with:

```python
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    anthropic_api_key: str = ""
    generated_apps_dir: str = "~/generated-apps"
    database_url: str = "sqlite+aiosqlite:///./incubator.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def generated_apps_path(self) -> Path:
        return Path(self.generated_apps_dir).expanduser()


settings = Settings()

# Forward Langfuse keys to os.environ so langfuse SDK auto-discovers them.
# pydantic-settings reads .env but does not populate os.environ.
if settings.langfuse_public_key:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
if settings.langfuse_secret_key:
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
```

- [ ] **Step 4: Add placeholder keys to .env**

Add to `incubator/backend/.env`:

```
LANGFUSE_PUBLIC_KEY=pk-lf-REPLACE_ME
LANGFUSE_SECRET_KEY=sk-lf-REPLACE_ME
LANGFUSE_HOST=https://cloud.langfuse.com
```

(Sign up at cloud.langfuse.com → Settings → API Keys to get real keys.)

- [ ] **Step 5: Verify config loads**

```bash
cd incubator/backend && source .venv/bin/activate && python -c "from app.config import settings; print(settings.langfuse_host)"
```

Expected: `https://cloud.langfuse.com`

- [ ] **Step 6: Commit**

```bash
git add incubator/backend/pyproject.toml incubator/backend/app/config.py incubator/backend/.env
git commit -m "feat: add langfuse config and dependency"
```

---

## Task 2: Instrument ClaudeClient

**Files:**
- Modify: `incubator/backend/app/services/claude_client.py`
- Modify: `incubator/backend/tests/test_claude_client.py`

- [ ] **Step 1: Fix broken test attribute reference**

Current tests use `client._client_instance` but the real attribute is `_client`. Also, after adding `@observe`, `response.usage` will be accessed — the mock needs a `usage` attribute. Update `incubator/backend/tests/test_claude_client.py`:

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.claude_client import ClaudeClient


def _make_mock_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    return mock_response


@pytest.fixture
def client():
    return ClaudeClient()


@pytest.mark.asyncio
async def test_generate_spec_calls_opus(client):
    mock_response = _make_mock_response('{"app_name": "Test"}')

    with patch.object(client._client, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        await client.generate_spec("build a tracker", "{}")

    mock_msgs.create.assert_called_once()
    assert mock_msgs.create.call_args.kwargs["model"] == "claude-opus-4-7"


@pytest.mark.asyncio
async def test_generate_json_parses_response(client):
    payload = {"app_name": "Tracker", "app_slug": "tracker"}
    mock_response = _make_mock_response(json.dumps(payload))

    with patch.object(client._client, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_json("prompt")

    assert result["app_name"] == "Tracker"


@pytest.mark.asyncio
async def test_generate_json_strips_markdown_fences(client):
    payload = {"key": "value"}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    mock_response = _make_mock_response(fenced)

    with patch.object(client._client, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_json("prompt")

    assert result["key"] == "value"


@pytest.mark.asyncio
async def test_generate_file_strips_markdown_fences(client):
    mock_response = _make_mock_response("```python\nprint('hello')\n```")

    with patch.object(client._client, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_file("generate a python file")

    assert result == "print('hello')"
```

- [ ] **Step 2: Run tests to verify they fail (attribute fix needed)**

```bash
cd incubator/backend && source .venv/bin/activate && pytest tests/test_claude_client.py -v
```

Expected: FAIL on `_client_instance` AttributeError (old tests) or PASS after fix. If running the new test file above, expect PASS once claude_client.py is updated.

- [ ] **Step 3: Instrument claude_client.py**

Replace `incubator/backend/app/services/claude_client.py` with:

```python
import json
import re

from anthropic import AsyncAnthropic
from langfuse.decorators import langfuse_context, observe

from app.config import settings

OPUS_MODEL = "claude-opus-4-7"
SONNET_MODEL = "claude-sonnet-4-6"

SPEC_SYSTEM = (
    "You are an expert mobile app architect. Generate structured JSON specs from app ideas. "
    "Always respond with valid JSON only. No markdown fences, no explanation."
)

FILE_GEN_SYSTEM = (
    "You are an expert full-stack developer specialising in Expo (React Native) and FastAPI. "
    "Generate complete, production-quality source files. "
    "Respond with the raw file content only — no markdown fences, no explanation, no commentary. "
    "Use the exact library versions provided. Follow the patterns provided exactly."
)

BLUEPRINT_SYSTEM = (
    "You are an expert mobile app architect. Generate architecture blueprints as JSON. "
    "Always respond with valid JSON only. No markdown fences, no explanation."
)


class ClaudeClient:
    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    @observe(as_type="generation", name="generate_spec")
    async def generate_spec(self, prompt: str, context: str = "", model: str = "opus") -> str:
        model_id = OPUS_MODEL if model == "opus" else SONNET_MODEL
        response = await self._client.messages.create(
            model=model_id,
            max_tokens=4096,
            system=SPEC_SYSTEM,
            messages=[{"role": "user", "content": f"{context}\n\n{prompt}".strip()}],
        )
        langfuse_context.update_current_observation(
            model=model_id,
            usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
        )
        return response.content[0].text

    @observe(as_type="generation", name="generate_json")
    async def generate_json(self, prompt: str, model: str = "opus", system: str | None = None) -> dict:
        model_id = OPUS_MODEL if model == "opus" else SONNET_MODEL
        sys = system or SPEC_SYSTEM
        response = await self._client.messages.create(
            model=model_id,
            max_tokens=8192,
            system=sys,
            messages=[{"role": "user", "content": prompt}],
        )
        langfuse_context.update_current_observation(
            model=model_id,
            usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text.strip())

    @observe(as_type="generation", name="generate_file")
    async def generate_file(self, prompt: str, system: str | None = None) -> str:
        """Generate a source file. Returns raw file content."""
        response = await self._client.messages.create(
            model=SONNET_MODEL,
            max_tokens=8192,
            system=system or FILE_GEN_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        langfuse_context.update_current_observation(
            model=SONNET_MODEL,
            usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```\w*\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        return text
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd incubator/backend && source .venv/bin/activate && pytest tests/test_claude_client.py -v
```

Expected:
```
PASSED tests/test_claude_client.py::test_generate_spec_calls_opus
PASSED tests/test_claude_client.py::test_generate_json_parses_response
PASSED tests/test_claude_client.py::test_generate_json_strips_markdown_fences
PASSED tests/test_claude_client.py::test_generate_file_strips_markdown_fences
```

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/services/claude_client.py incubator/backend/tests/test_claude_client.py
git commit -m "feat: instrument ClaudeClient with Langfuse @observe"
```

---

## Task 3: Instrument pipeline stages

**Files:**
- Modify: `incubator/backend/app/pipeline/stages.py`

The pipeline stages are independent HTTP-triggered functions so they each produce their own Langfuse trace. Using `session_id=run_id` groups all stages of a pipeline run in the Langfuse Sessions view.

- [ ] **Step 1: Add @observe imports and decorate stage functions**

At the top of `incubator/backend/app/pipeline/stages.py`, add to imports:

```python
from langfuse.decorators import langfuse_context, observe
```

Decorate each of the four stage functions. Add the decorator and the `langfuse_context.update_current_trace` call as the first line of each function body (before any await).

`run_spec_generation`:
```python
@observe(name="spec-generation")
async def run_spec_generation(run_id: str, raw_idea: str, form_answers: FormAnswers) -> None:
    langfuse_context.update_current_trace(session_id=run_id)
    workspace.init_index(run_id)
    # ... rest unchanged
```

`run_blueprint_generation`:
```python
@observe(name="blueprint-generation")
async def run_blueprint_generation(run_id: str, spec: ProductSpec) -> None:
    langfuse_context.update_current_trace(session_id=run_id)
    await _update_run(run_id, status="generating_blueprint")
    # ... rest unchanged
```

`run_shell_scaffolding`:
```python
@observe(name="shell-scaffolding")
async def run_shell_scaffolding(
    run_id: str, spec: ProductSpec, blueprint: ArchitectureBlueprint
) -> None:
    langfuse_context.update_current_trace(session_id=run_id)
    await _update_run(run_id, status="generating_shell")
    # ... rest unchanged
```

`run_file_generation`:
```python
@observe(name="file-generation")
async def run_file_generation(
    run_id: str, spec: ProductSpec, blueprint: ArchitectureBlueprint
) -> None:
    langfuse_context.update_current_trace(session_id=run_id)
    await _update_run(run_id, status="building_full")
    # ... rest unchanged
```

`run_version_check` does not call Claude — leave undecorated.

- [ ] **Step 2: Run existing pipeline tests — expect PASS**

```bash
cd incubator/backend && source .venv/bin/activate && pytest tests/test_pipeline_stages.py -v
```

Expected: both tests PASS. Langfuse `@observe` is a no-op when `LANGFUSE_PUBLIC_KEY` env var is absent (test env).

- [ ] **Step 3: Run full test suite**

```bash
cd incubator/backend && source .venv/bin/activate && pytest -v
```

Expected: all tests that were passing before still PASS. Ignore tests that require a real API key.

- [ ] **Step 4: Commit**

```bash
git add incubator/backend/app/pipeline/stages.py
git commit -m "feat: instrument pipeline stages with Langfuse @observe"
```

---

## Task 4: Update docs

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude/workspace/index.md`

- [ ] **Step 1: Add Langfuse section to CLAUDE.md**

In `CLAUDE.md`, under the "## Tech stack" section, add Langfuse to the bullet list:

```markdown
- **Observability**: Langfuse cloud — traces every pipeline run; view at cloud.langfuse.com
```

Then add a new section after "## How to run":

```markdown
## Langfuse setup

Sign up at https://cloud.langfuse.com → Settings → API Keys. Add to `incubator/backend/.env`:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Each pipeline run appears in Langfuse as a session (keyed by run_id). Each stage is a trace; each Claude call is a generation with model, token usage, and latency. If keys are absent, tracing silently no-ops — pipeline keeps working.
```

- [ ] **Step 2: Update workspace index.md**

In `.claude/workspace/index.md`, move "Langfuse integration" under "What's done":

```markdown
- [x] Langfuse cloud tracing — @observe on ClaudeClient + pipeline stages, session_id=run_id
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md .claude/workspace/index.md
git commit -m "docs: add Langfuse setup instructions and update workspace"
```
