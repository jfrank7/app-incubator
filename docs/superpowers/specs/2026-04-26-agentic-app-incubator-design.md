# Agentic App Incubator — Design Spec
**Date:** 2026-04-26

## Objective

Internal tool that converts a mobile app idea + structured form into a runnable Expo + FastAPI repo with default auth, payment placeholders, a deterministic generation pipeline, and a strict QA gate.

---

## Constraints (non-negotiable)

- Mobile framework: Expo + Expo Router + TypeScript
- Backend: FastAPI + SQLAlchemy + SQLite (dev)
- LLM: Claude API (Anthropic) — Opus for spec/arch stages, Sonnet for scaffolding/editing/QA
- Orchestration: LangGraph state machine
- Incubator UI: React + Vite SPA
- Generated repo location: `~/generated-apps/<run-id>/`
- Auth: always included
- Payments: placeholder only, never real Stripe in v1
- Fix loop cap: 3 global retries, stop-fast on same error twice

---

## Repo Structure

```
app-incubator/
  incubator/
    backend/
      app/
        api/          # FastAPI routes
        pipeline/     # LangGraph graph + node definitions
        services/     # Claude API callers, file generator, QA runner
        schemas/      # Pydantic models
        db/           # SQLAlchemy + SQLite, run metadata
        templates/    # Jinja2 .j2 templates for generated files
        main.py
      pyproject.toml
    frontend/
      src/
        pages/        # Idea input, run history, run detail, artifacts, QA
        components/   # Progress stream, QA report, file tree
      vite.config.ts
      package.json

~/generated-apps/
  <run-id>/
    apps/
      mobile/
        app/
        components/
        features/
          auth/
          home/
          utility_core/
          settings/
        lib/
          api/
          db/
          storage/
          config/
          telemetry/
        assets/
        package.json
        app.json
        tsconfig.json
    backend/
      app/
        api/
        auth/
        core/
        db/
        models/
        schemas/
        services/
        telemetry/
        main.py
      tests/
      pyproject.toml
    infra/
      docker/
        backend.Dockerfile
      docker-compose.yml
    incubator/
      product_spec.json
      architecture_blueprint.json
      generation_report.json
      qa_report.json
    README.md
    .env.example
```

---

## Pipeline (LangGraph)

Nodes execute in sequence. State is a `RunState` TypedDict passed through all nodes.

```
intake
→ spec_generator        (Opus)
→ spec_validator
→ architecture_mapper   (Opus)
→ template_selector
→ scaffolder            (Sonnet)
→ task_planner
→ repo_editor           (Sonnet)
→ qa_runner             (Sonnet)
→ fix_loop              (Sonnet) — conditional, max 3 iterations
→ delivery_packager
```

### RunState

```python
class RunState(TypedDict):
    run_id: str
    raw_idea: str
    form_answers: FormAnswers
    product_spec: ProductSpec | None
    architecture_blueprint: Blueprint | None
    selected_modules: list[str]
    file_plan: list[FilePlan]
    changed_files: list[str]
    qa_results: QAResults | None
    retry_count: int
    error_history: list[str]
    final_status: Literal["pending", "running", "done", "failed"]
```

### Fix loop policy

- Conditional edge: `qa_runner` → `fix_loop` if `not qa_results.passed and retry_count < 3`
- Same error string appears in `error_history` twice → stop, emit failure report
- Max per-file retries: 2
- On stop: write `qa_report.json` with precise failure summary

---

## Schemas

### FormAnswers
```python
class FormAnswers(BaseModel):
    app_goal: str
    target_user: str
    top_3_actions: list[str]          # exactly 3
    must_have_screens: list[str]
    works_offline: bool
    needs_notifications: bool
    core_data_entities: list[str]
    style_notes: str
    constraints_non_goals: str
    include_payments_placeholder: bool  # default False, "maybe later"
```

### ProductSpec
```python
class ProductSpec(BaseModel):
    app_name: str
    app_slug: str
    goal: str
    target_user: str
    screens: list[ScreenSpec]
    features: list[str]
    data_entities: list[EntitySpec]
    offline_support: bool
    notifications: bool
    auth_required: bool               # always True in v1
    payments_placeholder: bool
    style_notes: str
    non_goals: list[str]
```

### ArchitectureBlueprint
```python
class Blueprint(BaseModel):
    mobile_framework: Literal["expo"]
    backend_framework: Literal["fastapi"]
    selected_modules: list[str]
    file_plan: list[FilePlan]
    api_routes: list[APIRoute]
    db_entities: list[str]
    env_vars: list[EnvVar]
```

---

## Incubator UI (React/Vite SPA)

### Routes

| Route | Purpose |
|---|---|
| `/` | Idea input + structured form |
| `/runs` | Run history list |
| `/runs/:id` | Run detail: status, live progress log |
| `/runs/:id/artifacts` | File tree + JSON artifact viewer |
| `/runs/:id/qa` | QA report |

### Progress streaming

SSE endpoint `GET /api/runs/:id/stream` pushes events:
```json
{"stage": "spec_generator", "status": "started", "ts": "..."}
{"stage": "spec_generator", "status": "completed", "ts": "..."}
{"log": "Writing apps/mobile/app/(auth)/login.tsx", "ts": "..."}
```

Frontend `EventSource` consumes stream, updates run detail page in real time.

### Incubator API

```
POST /api/runs                 # create run, start pipeline async
GET  /api/runs                 # list runs (id, status, app_name, created_at)
GET  /api/runs/:id             # run detail + current status
GET  /api/runs/:id/stream      # SSE progress
GET  /api/runs/:id/artifacts   # file manifest + JSON artifacts
GET  /api/runs/:id/qa          # QA report
```

---

## Template System

All generated files rendered from Jinja2 `.j2` templates. No string-patching.

### Mobile base template modules

| Module | Always included |
|---|---|
| `auth` | Yes |
| `onboarding` | No |
| `dashboard` | Yes |
| `settings` | Yes |
| `profile` | No |
| `list_detail_crud` | No |
| `form_flow` | No |
| `search_filter` | No |
| `local_persistence` | Yes |
| `notifications_placeholder` | Per form answer |
| `payments_placeholder` | Per form answer |
| `analytics_hook` | Yes (minimal) |

### Mobile base includes (always)
- Expo Router shell (file-based routing)
- Auth screens: login, signup, forgot password
- API client (`lib/api/client.ts`) with JWT attach + refresh
- SecureStore session management
- expo-sqlite local DB layer
- Loading/error state components
- Backend health check on startup

### Backend base includes (always)
- FastAPI app + CORS
- JWT auth: `/auth/register`, `/auth/login`, `/auth/refresh`
- SQLAlchemy + SQLite (Alembic configured)
- `/health` endpoint
- Protected example resource route
- Billing stubs: `services/billing.py`, `api/billing.py`, webhook placeholder
- Request logging middleware
- Basic error traces

---

## QA Gate

### Checks

**Backend:**
```bash
ruff check .
python -m pytest tests/
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
curl -f http://localhost:8000/health
```

**Mobile:**
```bash
npx tsc --noEmit
npx eslint src/ --ext .ts,.tsx
npx expo export --platform ios --output-dir /tmp/expo-check
```

### QAResults schema
```python
class QACheck(BaseModel):
    name: str
    passed: bool
    output: str
    error: str | None

class QAResults(BaseModel):
    passed: bool
    checks: list[QACheck]
    summary: str
    generated_at: datetime
```

### On failure
1. Feed `QAResults` + relevant file contents to Sonnet with targeted fix prompt
2. Re-run checks
3. If same error in `error_history` → stop immediately
4. After 3 loops → stop, write `qa_report.json` with all failures listed precisely

---

## Observability

### Incubator
- Stage start/end timestamps stored in DB per run
- File change log stored per run
- QA events logged per check
- Failure reasons stored in `RunState.error_history` + DB

### Generated backend
- Request log middleware (stdout)
- `/health` endpoint
- Basic exception handler with trace logging

### Generated mobile
- Minimal error logging hook in `lib/telemetry/`

---

## Delivery Output (per run)

- `~/generated-apps/<run-id>/apps/mobile/` — Expo app
- `~/generated-apps/<run-id>/backend/` — FastAPI backend
- `~/generated-apps/<run-id>/README.md` — local run instructions
- `~/generated-apps/<run-id>/.env.example`
- `~/generated-apps/<run-id>/incubator/product_spec.json`
- `~/generated-apps/<run-id>/incubator/architecture_blueprint.json`
- `~/generated-apps/<run-id>/incubator/generation_report.json`
- `~/generated-apps/<run-id>/incubator/qa_report.json`

---

## Implementation Phases

### Phase 1 — Schemas + intake
- Pydantic schemas: `FormAnswers`, `ProductSpec`, `Blueprint`, `RunState`, `QAResults`
- SQLite DB: run metadata table
- Incubator backend: `POST /api/runs`, `GET /api/runs`, `GET /api/runs/:id`
- React UI: idea input page + structured form

### Phase 2 — Template foundation
- Jinja2 mobile base template (all always-included modules)
- Jinja2 FastAPI base template
- Module system: module manifest + conditional template inclusion
- Scaffolder service: renders templates → writes files to `~/generated-apps/<run-id>/`

### Phase 3 — Generation pipeline
- LangGraph graph wiring all nodes
- Claude API service (Opus/Sonnet routing)
- `spec_generator` node: prompt → `ProductSpec`
- `architecture_mapper` node: spec → `Blueprint` + `selected_modules`
- `scaffolder` node: blueprint → files on disk
- `repo_editor` node: targeted file edits from task plan
- Async pipeline execution + SSE streaming

### Phase 4 — QA + fix loop
- `qa_runner` node: runs all checks, produces `QAResults`
- `fix_loop` node: Claude Sonnet fix prompt + re-run
- Fix loop conditional edge + stop-fast logic
- `delivery_packager` node: writes all JSON artifacts + README

### Phase 5 — UX polish
- Run history page
- Run detail with live SSE progress
- Artifacts viewer
- QA report view
- Error/failure display

---

## First Proving App: Caffeine Tracker

Used to validate end-to-end generation:
- Screens: login/signup, dashboard, add entry, history, settings, subscription placeholder
- Entities: User, CaffeineEntry, DailyGoal
- Modules: auth, dashboard, list_detail_crud, form_flow, local_persistence, payments_placeholder
- Offline: yes
- Notifications: no

---

## Out of Scope (v1)

- Multi-stack support
- Real Stripe billing
- Third-party auth providers
- Cloud/Kubernetes deployment
- App store publishing
- Social/real-time/multiplayer features
- Enterprise roles beyond basic auth
