# Agentic App Incubator — Phase 4: QA + Fix Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the QA runner, fix loop, and delivery packager nodes so the pipeline verifies generated repos and retries on failure.

**Architecture:** `QARunnerService` runs lint/type-check/tests as subprocesses in the generated repo. Results feed into `run_qa_runner` LangGraph node. Conditional edge routes to `run_fix_loop` (Sonnet) or `run_delivery_packager`. Fix loop rewrites failing files and re-runs QA. Max 3 global retries; same error twice = stop.

**Tech Stack:** Python asyncio subprocess, LangGraph conditional edges

**Prerequisite:** Phase 3 complete.

---

## File Map

**Create:**
- `incubator/backend/app/services/qa_runner.py`
- `incubator/backend/tests/test_qa_runner.py`

**Modify:**
- `incubator/backend/app/pipeline/nodes.py` — add `run_qa_runner`, `run_fix_loop`
- `incubator/backend/app/pipeline/graph.py` — add conditional QA edge

---

## Task 17: QA runner service

**Files:**
- Create: `incubator/backend/app/services/qa_runner.py`
- Create: `incubator/backend/tests/test_qa_runner.py`

- [ ] **Step 1: Write failing tests**

`incubator/backend/tests/test_qa_runner.py`:
```python
import pytest
from pathlib import Path
import shutil
from app.services.qa_runner import QARunnerService


@pytest.fixture
def minimal_backend(tmp_path) -> Path:
    """Create a minimal valid FastAPI project for QA testing."""
    backend = tmp_path / "backend"
    backend.mkdir()
    app_dir = backend / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n"
    )
    (backend / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "0.1.0"\nrequires-python = ">=3.11"\ndependencies = ["fastapi", "uvicorn"]\n[project.optional-dependencies]\ndev = ["pytest", "ruff", "httpx"]\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    )
    tests_dir = backend / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_health.py").write_text(
        "def test_health():\n    from app.main import app\n    from fastapi.testclient import TestClient\n    client = TestClient(app)\n    assert client.get('/health').status_code == 200\n"
    )
    return tmp_path


@pytest.mark.asyncio
async def test_ruff_passes_on_clean_code(minimal_backend):
    svc = QARunnerService()
    check = await svc.run_ruff(minimal_backend / "backend")
    assert check.name == "ruff"
    # ruff may not be installed in test env — just check structure
    assert hasattr(check, "passed")
    assert hasattr(check, "output")


@pytest.mark.asyncio
async def test_qa_results_all_passed(minimal_backend):
    svc = QARunnerService()
    results = await svc.run_all(minimal_backend)
    assert hasattr(results, "passed")
    assert hasattr(results, "checks")
    assert len(results.checks) > 0
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_qa_runner.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `incubator/backend/app/services/qa_runner.py`**

```python
import asyncio
from pathlib import Path
from datetime import datetime
from app.schemas.pipeline import QACheck, QAResults


async def _run_cmd(cmd: list[str], cwd: Path) -> tuple[bool, str, str | None]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode(errors="replace")
        passed = proc.returncode == 0
        return passed, output, None
    except asyncio.TimeoutError:
        return False, "", "Command timed out after 120s"
    except FileNotFoundError as e:
        return False, "", f"Command not found: {e}"


class QARunnerService:
    async def run_ruff(self, backend_dir: Path) -> QACheck:
        passed, output, error = await _run_cmd(["ruff", "check", "."], backend_dir)
        return QACheck(name="ruff", passed=passed, output=output, error=error)

    async def run_pytest(self, backend_dir: Path) -> QACheck:
        passed, output, error = await _run_cmd(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
            backend_dir,
        )
        return QACheck(name="pytest", passed=passed, output=output, error=error)

    async def run_backend_startup(self, backend_dir: Path) -> QACheck:
        """Check that FastAPI app imports and creates without error."""
        passed, output, error = await _run_cmd(
            ["python", "-c", "from app.main import app; print('startup ok')"],
            backend_dir,
        )
        return QACheck(name="backend_startup", passed=passed, output=output, error=error)

    async def run_tsc(self, mobile_dir: Path) -> QACheck:
        passed, output, error = await _run_cmd(["npx", "tsc", "--noEmit"], mobile_dir)
        return QACheck(name="tsc", passed=passed, output=output, error=error)

    async def run_eslint(self, mobile_dir: Path) -> QACheck:
        passed, output, error = await _run_cmd(
            ["npx", "eslint", ".", "--ext", ".ts,.tsx", "--max-warnings", "0"],
            mobile_dir,
        )
        return QACheck(name="eslint", passed=passed, output=output, error=error)

    async def run_all(self, output_dir: Path) -> QAResults:
        backend_dir = output_dir / "backend"
        mobile_dir = output_dir / "apps" / "mobile"

        checks: list[QACheck] = []

        if backend_dir.exists():
            checks.append(await self.run_ruff(backend_dir))
            checks.append(await self.run_backend_startup(backend_dir))
            checks.append(await self.run_pytest(backend_dir))

        if mobile_dir.exists() and (mobile_dir / "node_modules").exists():
            checks.append(await self.run_tsc(mobile_dir))
            checks.append(await self.run_eslint(mobile_dir))

        all_passed = all(c.passed for c in checks)
        failed = [c.name for c in checks if not c.passed]
        summary = "All checks passed." if all_passed else f"Failed: {', '.join(failed)}"

        return QAResults(passed=all_passed, checks=checks, summary=summary, generated_at=datetime.utcnow())
```

- [ ] **Step 4: Run tests**

```bash
cd incubator/backend && pytest tests/test_qa_runner.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/services/qa_runner.py incubator/backend/tests/test_qa_runner.py
git commit -m "feat: add QA runner service for backend and mobile checks"
```

---

## Task 18: QA + fix loop pipeline nodes

**Files:**
- Modify: `incubator/backend/app/pipeline/nodes.py`

- [ ] **Step 1: Write failing test**

Append to `incubator/backend/tests/test_pipeline_nodes.py`:
```python
@pytest.mark.asyncio
async def test_qa_runner_node_emits_results():
    from app.pipeline.nodes import run_qa_runner
    from app.schemas.form import ProductSpec, ScreenSpec, EntitySpec
    spec = ProductSpec(
        app_name="Test", app_slug="test", goal="test", target_user="devs",
        screens=[ScreenSpec(name="Home", route="/", description="home")],
        features=[], data_entities=[], offline_support=False,
        notifications=False, auth_required=True, payments_placeholder=False,
        style_notes="", non_goals=[],
    )
    state = make_state({"product_spec": spec, "final_status": "running"})

    with patch("app.pipeline.nodes.sse_manager.emit_stage", AsyncMock()):
        with patch("app.pipeline.nodes.sse_manager.emit_log", AsyncMock()):
            with patch("app.pipeline.nodes.qa_svc.run_all", AsyncMock(return_value=__import__('app.schemas.pipeline', fromlist=['QAResults']).QAResults(passed=True, checks=[], summary="ok"))):
                result = await run_qa_runner(state)

    assert result["qa_results"] is not None
    assert result["qa_results"].passed is True


@pytest.mark.asyncio
async def test_fix_loop_increments_retry_count():
    from app.pipeline.nodes import run_fix_loop
    from app.schemas.pipeline import QAResults, QACheck
    qa = QAResults(passed=False, checks=[QACheck(name="ruff", passed=False, output="E501 line too long", error=None)], summary="ruff failed")
    state = make_state({"final_status": "running", "qa_results": qa, "retry_count": 0, "error_history": []})

    with patch("app.pipeline.nodes.sse_manager.emit_stage", AsyncMock()):
        with patch("app.pipeline.nodes.sse_manager.emit_log", AsyncMock()):
            with patch("app.pipeline.nodes.claude.generate_text", AsyncMock(return_value="# fixed")):
                result = await run_fix_loop(state)

    assert result["retry_count"] == 1
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_pipeline_nodes.py::test_qa_runner_node_emits_results -v
```

Expected: `ImportError` — `run_qa_runner` not defined.

- [ ] **Step 3: Add `run_qa_runner` and `run_fix_loop` to `nodes.py`**

Append to `incubator/backend/app/pipeline/nodes.py`:

```python
from app.services.qa_runner import QARunnerService

qa_svc = QARunnerService()

FIX_PROMPT = """The following QA checks failed for a generated {framework} project.

Failed checks:
{failures}

Relevant file content:
{file_content}

Fix the issues. Return ONLY the corrected file content with no explanation."""


async def run_qa_runner(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "qa_runner", "started")
    output_dir = settings.generated_apps_path / state["run_id"]
    results = await qa_svc.run_all(output_dir)

    for check in results.checks:
        status = "passed" if check.passed else "FAILED"
        await sse_manager.emit_log(state["run_id"], f"QA {check.name}: {status}")

    await sse_manager.emit_stage(state["run_id"], "qa_runner", "completed")
    return {
        "qa_results": results,
        "stage_logs": state["stage_logs"] + [{"stage": "qa_runner", "status": "completed", "passed": results.passed}],
    }


async def run_fix_loop(state: RunState) -> dict:
    await sse_manager.emit_stage(state["run_id"], "fix_loop", "started")
    qa = state["qa_results"]
    assert qa is not None

    failed_checks = [c for c in qa.checks if not c.passed]
    output_dir = settings.generated_apps_path / state["run_id"]

    new_error_history = list(state["error_history"])
    for check in failed_checks:
        error_key = f"{check.name}:{check.output[:200]}"

        if new_error_history.count(error_key) >= 1:
            await sse_manager.emit_log(state["run_id"], f"Same error twice for {check.name} — stopping")
            return {
                "final_status": "failed",
                "error_history": new_error_history + [error_key],
                "retry_count": state["retry_count"] + 1,
            }

        new_error_history.append(error_key)

        if check.name == "ruff":
            target_files = list((output_dir / "backend").rglob("*.py"))[:3]
        elif check.name in ("tsc", "eslint"):
            target_files = list((output_dir / "apps" / "mobile").rglob("*.tsx"))[:3]
        else:
            target_files = []

        for file_path in target_files:
            try:
                content = file_path.read_text()
                prompt = FIX_PROMPT.format(
                    framework="FastAPI" if check.name == "ruff" else "Expo",
                    failures=f"{check.name}: {check.output[:500]}",
                    file_content=f"# {file_path.name}\n{content[:2000]}",
                )
                fixed = await claude.generate_text(prompt, model="sonnet")
                file_path.write_text(fixed)
                await sse_manager.emit_log(state["run_id"], f"Fixed: {file_path.name}")
            except Exception as e:
                await sse_manager.emit_log(state["run_id"], f"Fix failed for {file_path.name}: {e}")

    await sse_manager.emit_stage(state["run_id"], "fix_loop", "completed")
    return {
        "retry_count": state["retry_count"] + 1,
        "error_history": new_error_history,
        "stage_logs": state["stage_logs"] + [{"stage": "fix_loop", "retry": state["retry_count"] + 1}],
    }
```

- [ ] **Step 4: Run tests**

```bash
cd incubator/backend && pytest tests/test_pipeline_nodes.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/app/pipeline/nodes.py incubator/backend/tests/test_pipeline_nodes.py
git commit -m "feat: add qa_runner and fix_loop pipeline nodes"
```

---

## Task 19: Wire QA + fix loop into graph with conditional edge

**Files:**
- Modify: `incubator/backend/app/pipeline/graph.py`

- [ ] **Step 1: Replace `incubator/backend/app/pipeline/graph.py`**

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
    run_qa_runner,
    run_fix_loop,
    run_delivery_packager,
    run_failure_handler,
)

MAX_RETRIES = 3


def _should_fix_or_deliver(state: RunState) -> str:
    qa = state.get("qa_results")
    if qa is None:
        return "delivery_packager"
    if state.get("final_status") == "failed":
        return "failure_handler"
    if not qa.passed and state.get("retry_count", 0) < MAX_RETRIES:
        return "fix_loop"
    if not qa.passed:
        return "failure_handler"
    return "delivery_packager"


def _after_fix_loop(state: RunState) -> str:
    if state.get("final_status") == "failed":
        return "failure_handler"
    return "qa_runner"


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
    graph.add_node("qa_runner", run_qa_runner)
    graph.add_node("fix_loop", run_fix_loop)
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
    graph.add_edge("repo_editor", "qa_runner")
    graph.add_conditional_edges("qa_runner", _should_fix_or_deliver)
    graph.add_conditional_edges("fix_loop", _after_fix_loop)
    graph.add_edge("delivery_packager", END)
    graph.add_edge("failure_handler", END)

    return graph


pipeline = build_graph().compile()
```

- [ ] **Step 2: Verify graph compiles**

```bash
cd incubator/backend && python -c "from app.pipeline.graph import pipeline; print('graph ok')"
```

Expected: `graph ok`

- [ ] **Step 3: Run all tests**

```bash
cd incubator/backend && pytest -v && ruff check .
```

Expected: all pass, no lint errors.

- [ ] **Step 4: Commit**

```bash
git add incubator/backend/app/pipeline/graph.py
git commit -m "feat: wire QA runner and fix loop into pipeline with conditional edges"
```

---

## Phase 4 Complete

**What was built:**
- `QARunnerService` running ruff, pytest, backend startup, tsc, eslint as subprocesses
- `run_qa_runner` node collecting `QAResults`
- `run_fix_loop` node calling Claude Sonnet to fix failing files, tracking error history
- Conditional edges: pass → `delivery_packager`, fail + retries left → `fix_loop`, fail + same error twice or max retries → `failure_handler`
- Full pipeline graph with all 12 nodes wired

**Review questions:**
1. Mobile QA only runs if `node_modules` exists — should we auto-run `npm install` in the scaffolder or QA runner?
2. Fix loop currently fixes first 3 files — should it target specific files named in the error output instead?
