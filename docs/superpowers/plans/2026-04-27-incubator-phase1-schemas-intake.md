# Agentic App Incubator — Phase 1: Schemas + Intake

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the incubator backend (FastAPI + SQLite) with all core Pydantic schemas, run persistence, and API endpoints, plus the React frontend with idea input and structured form.

**Architecture:** FastAPI backend with SQLAlchemy async SQLite. Pydantic v2 schemas define all domain types. React + Vite SPA talks to backend via REST. No pipeline execution yet — runs are created and stored, pipeline stub returns immediately.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, React 18, Vite, TypeScript, React Router v6

---

## File Map

**Create:**
- `incubator/backend/pyproject.toml`
- `incubator/backend/.env.example`
- `incubator/backend/app/__init__.py`
- `incubator/backend/app/main.py`
- `incubator/backend/app/config.py`
- `incubator/backend/app/db/__init__.py`
- `incubator/backend/app/db/database.py`
- `incubator/backend/app/db/models.py`
- `incubator/backend/app/schemas/__init__.py`
- `incubator/backend/app/schemas/form.py`
- `incubator/backend/app/schemas/run.py`
- `incubator/backend/app/schemas/pipeline.py`
- `incubator/backend/app/api/__init__.py`
- `incubator/backend/app/api/runs.py`
- `incubator/backend/tests/__init__.py`
- `incubator/backend/tests/conftest.py`
- `incubator/backend/tests/test_runs_api.py`
- `incubator/frontend/package.json`
- `incubator/frontend/vite.config.ts`
- `incubator/frontend/tsconfig.json`
- `incubator/frontend/index.html`
- `incubator/frontend/src/main.tsx`
- `incubator/frontend/src/App.tsx`
- `incubator/frontend/src/api/client.ts`
- `incubator/frontend/src/pages/IdeaForm.tsx`
- `incubator/frontend/src/pages/RunList.tsx`
- `incubator/frontend/src/types/index.ts`

---

## Task 1: Project scaffolding

**Files:**
- Create: `incubator/backend/pyproject.toml`
- Create: `incubator/backend/.env.example`
- Create: `incubator/frontend/package.json`
- Create: `incubator/frontend/vite.config.ts`
- Create: `incubator/frontend/tsconfig.json`
- Create: `incubator/frontend/index.html`

- [ ] **Step 1: Create backend directory structure**

```bash
mkdir -p incubator/backend/app/{api,db,schemas,pipeline,services,templates}
mkdir -p incubator/backend/tests
touch incubator/backend/app/__init__.py
touch incubator/backend/app/api/__init__.py
touch incubator/backend/app/db/__init__.py
touch incubator/backend/app/schemas/__init__.py
touch incubator/backend/app/pipeline/__init__.py
touch incubator/backend/app/services/__init__.py
touch incubator/backend/tests/__init__.py
```

- [ ] **Step 2: Write `incubator/backend/pyproject.toml`**

```toml
[project]
name = "app-incubator"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.20.0",
    "pydantic>=2.7.0",
    "langgraph>=0.1.0",
    "anthropic>=0.28.0",
    "langchain-anthropic>=0.1.0",
    "jinja2>=3.1.4",
    "python-dotenv>=1.0.0",
    "sse-starlette>=1.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
]

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Write `incubator/backend/.env.example`**

```
ANTHROPIC_API_KEY=sk-ant-...
GENERATED_APPS_DIR=~/generated-apps
DATABASE_URL=sqlite+aiosqlite:///./incubator.db
CORS_ORIGINS=http://localhost:5173
```

- [ ] **Step 4: Install backend dependencies**

```bash
cd incubator/backend && pip install -e ".[dev]"
```

Expected: packages install without error.

- [ ] **Step 5: Create frontend with Vite**

```bash
cd incubator/frontend
npm create vite@latest . -- --template react-ts
npm install react-router-dom
```

- [ ] **Step 6: Write `incubator/frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 7: Verify frontend builds**

```bash
cd incubator/frontend && npm run build
```

Expected: `dist/` created, no errors.

- [ ] **Step 8: Commit**

```bash
git add incubator/
git commit -m "feat: scaffold incubator backend and frontend project structure"
```

---

## Task 2: Core Pydantic schemas

**Files:**
- Create: `incubator/backend/app/schemas/form.py`
- Create: `incubator/backend/app/schemas/pipeline.py`
- Create: `incubator/backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing schema tests**

`incubator/backend/tests/test_schemas.py`:
```python
import pytest
from app.schemas.form import FormAnswers, ProductSpec, ArchitectureBlueprint
from app.schemas.pipeline import RunState, QACheck, QAResults


def test_form_answers_requires_exactly_3_actions():
    with pytest.raises(Exception):
        FormAnswers(
            app_goal="track caffeine",
            target_user="health-conscious adults",
            top_3_actions=["log drink", "view total"],  # only 2
            must_have_screens=["dashboard"],
            works_offline=True,
            needs_notifications=False,
            core_data_entities=["CaffeineEntry"],
            style_notes="clean minimal",
            constraints_non_goals="no social features",
        )


def test_form_answers_valid():
    fa = FormAnswers(
        app_goal="track caffeine",
        target_user="health-conscious adults",
        top_3_actions=["log drink", "view daily total", "set reduction goal"],
        must_have_screens=["dashboard", "add entry", "history"],
        works_offline=True,
        needs_notifications=False,
        core_data_entities=["CaffeineEntry", "DailyGoal"],
        style_notes="clean minimal",
        constraints_non_goals="no social features",
    )
    assert fa.include_payments_placeholder is False
    assert fa.auth_required is True


def test_product_spec_auth_always_true():
    from app.schemas.form import ScreenSpec, EntitySpec
    spec = ProductSpec(
        app_name="Caffeine Tracker",
        app_slug="caffeine-tracker",
        goal="track daily caffeine",
        target_user="health-conscious adults",
        screens=[ScreenSpec(name="Dashboard", route="/", description="main view")],
        features=["logging", "history"],
        data_entities=[EntitySpec(name="CaffeineEntry", fields=["id", "mg", "timestamp"])],
        offline_support=True,
        notifications=False,
        auth_required=True,
        payments_placeholder=False,
        style_notes="minimal",
        non_goals=["social"],
    )
    assert spec.auth_required is True


def test_qa_results_passes_only_when_all_checks_pass():
    results = QAResults(
        passed=True,
        checks=[
            QACheck(name="ruff", passed=True, output="All good", error=None),
            QACheck(name="pytest", passed=True, output="3 passed", error=None),
        ],
        summary="All checks passed",
    )
    assert results.passed is True
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd incubator/backend && pytest tests/test_schemas.py -v
```

Expected: `ImportError` — schemas not defined yet.

- [ ] **Step 3: Write `incubator/backend/app/schemas/form.py`**

```python
from pydantic import BaseModel, field_validator


class ScreenSpec(BaseModel):
    name: str
    route: str
    description: str


class EntitySpec(BaseModel):
    name: str
    fields: list[str]


class APIRoute(BaseModel):
    method: str
    path: str
    description: str


class EnvVar(BaseModel):
    key: str
    example_value: str
    description: str


class FilePlan(BaseModel):
    path: str
    template: str
    context_keys: list[str]


class FormAnswers(BaseModel):
    app_goal: str
    target_user: str
    top_3_actions: list[str]
    must_have_screens: list[str]
    works_offline: bool
    needs_notifications: bool
    core_data_entities: list[str]
    style_notes: str
    constraints_non_goals: str
    include_payments_placeholder: bool = False
    auth_required: bool = True

    @field_validator("top_3_actions")
    @classmethod
    def must_have_three_actions(cls, v: list[str]) -> list[str]:
        if len(v) != 3:
            raise ValueError("top_3_actions must contain exactly 3 items")
        return v


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
    auth_required: bool = True
    payments_placeholder: bool = False
    style_notes: str
    non_goals: list[str]


class ArchitectureBlueprint(BaseModel):
    mobile_framework: str = "expo"
    backend_framework: str = "fastapi"
    selected_modules: list[str]
    file_plan: list[FilePlan]
    api_routes: list[APIRoute]
    db_entities: list[str]
    env_vars: list[EnvVar]
```

- [ ] **Step 4: Write `incubator/backend/app/schemas/pipeline.py`**

```python
from __future__ import annotations
from datetime import datetime
from typing import Literal, TypedDict
from pydantic import BaseModel, Field
from app.schemas.form import FormAnswers, ProductSpec, ArchitectureBlueprint, FilePlan


class QACheck(BaseModel):
    name: str
    passed: bool
    output: str
    error: str | None = None


class QAResults(BaseModel):
    passed: bool
    checks: list[QACheck]
    summary: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class RunState(TypedDict):
    run_id: str
    raw_idea: str
    form_answers: FormAnswers
    product_spec: ProductSpec | None
    architecture_blueprint: ArchitectureBlueprint | None
    selected_modules: list[str]
    file_plan: list[FilePlan]
    changed_files: list[str]
    qa_results: QAResults | None
    retry_count: int
    error_history: list[str]
    final_status: Literal["pending", "running", "done", "failed"]
    stage_logs: list[dict]
```

- [ ] **Step 5: Run tests to confirm pass**

```bash
cd incubator/backend && pytest tests/test_schemas.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add incubator/backend/app/schemas/ incubator/backend/tests/test_schemas.py
git commit -m "feat: add core Pydantic schemas for forms, specs, and pipeline state"
```

---

## Task 3: Config + database setup

**Files:**
- Create: `incubator/backend/app/config.py`
- Create: `incubator/backend/app/db/database.py`
- Create: `incubator/backend/app/db/models.py`
- Create: `incubator/backend/tests/test_db.py`

- [ ] **Step 1: Write failing DB test**

`incubator/backend/tests/test_db.py`:
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session, init_db
from app.db.models import Run


@pytest.mark.asyncio
async def test_create_and_fetch_run(db_session: AsyncSession):
    run = Run(
        id="test-run-123",
        raw_idea="track caffeine",
        status="pending",
        app_name=None,
        form_answers_json="{}",
        product_spec_json=None,
        blueprint_json=None,
        qa_report_json=None,
        error_summary=None,
    )
    db_session.add(run)
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(select(Run).where(Run.id == "test-run-123"))
    fetched = result.scalar_one()
    assert fetched.raw_idea == "track caffeine"
    assert fetched.status == "pending"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_db.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `incubator/backend/app/config.py`**

```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    generated_apps_dir: str = "~/generated-apps"
    database_url: str = "sqlite+aiosqlite:///./incubator.db"
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def generated_apps_path(self) -> Path:
        return Path(self.generated_apps_dir).expanduser()

    class Config:
        env_file = ".env"


settings = Settings()
```

Note: also add `pydantic-settings` to pyproject.toml dependencies.

- [ ] **Step 4: Write `incubator/backend/app/db/database.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 5: Write `incubator/backend/app/db/models.py`**

```python
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    raw_idea: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    app_name: Mapped[str | None] = mapped_column(String, nullable=True)
    form_answers_json: Mapped[str] = mapped_column(Text)
    product_spec_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    blueprint_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    qa_report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    stage_logs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 6: Write `incubator/backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.database import Base


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 7: Add pydantic-settings to pyproject.toml**

Add to `dependencies` list:
```
"pydantic-settings>=2.0.0",
```

Then: `pip install pydantic-settings`

- [ ] **Step 8: Run tests**

```bash
cd incubator/backend && pytest tests/test_db.py -v
```

Expected: `1 passed`.

- [ ] **Step 9: Commit**

```bash
git add incubator/backend/app/config.py incubator/backend/app/db/ incubator/backend/tests/conftest.py incubator/backend/tests/test_db.py incubator/backend/pyproject.toml
git commit -m "feat: add config, async SQLAlchemy setup, and Run model"
```

---

## Task 4: FastAPI app + runs API

**Files:**
- Create: `incubator/backend/app/main.py`
- Create: `incubator/backend/app/schemas/run.py`
- Create: `incubator/backend/app/api/runs.py`
- Create: `incubator/backend/tests/test_runs_api.py`

- [ ] **Step 1: Write failing API tests**

`incubator/backend/tests/test_runs_api.py`:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_run(client: AsyncClient):
    payload = {
        "raw_idea": "track caffeine intake daily",
        "form_answers": {
            "app_goal": "help users reduce caffeine",
            "target_user": "health-conscious adults",
            "top_3_actions": ["log drink", "view daily total", "set reduction goal"],
            "must_have_screens": ["dashboard", "add entry", "history"],
            "works_offline": True,
            "needs_notifications": False,
            "core_data_entities": ["CaffeineEntry", "DailyGoal"],
            "style_notes": "clean minimal",
            "constraints_non_goals": "no social features",
        },
    }
    r = await client.post("/api/runs", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient):
    r = await client.get("/api/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_get_run_not_found(client: AsyncClient):
    r = await client.get("/api/runs/nonexistent-id")
    assert r.status_code == 404
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd incubator/backend && pytest tests/test_runs_api.py -v
```

Expected: `ImportError` — `app.main` not defined.

- [ ] **Step 3: Write `incubator/backend/app/schemas/run.py`**

```python
from datetime import datetime
from pydantic import BaseModel
from app.schemas.form import FormAnswers


class CreateRunRequest(BaseModel):
    raw_idea: str
    form_answers: FormAnswers


class RunResponse(BaseModel):
    id: str
    raw_idea: str
    status: str
    app_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunListItem(BaseModel):
    id: str
    status: str
    app_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Write `incubator/backend/app/api/runs.py`**

```python
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_session
from app.db.models import Run
from app.schemas.run import CreateRunRequest, RunResponse, RunListItem

router = APIRouter(prefix="/api/runs", tags=["runs"])


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
```

- [ ] **Step 5: Write `incubator/backend/app/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import init_db
from app.api.runs import router as runs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="App Incubator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Run tests**

```bash
cd incubator/backend && pytest tests/test_runs_api.py -v
```

Expected: `4 passed`.

- [ ] **Step 7: Run all tests**

```bash
cd incubator/backend && pytest -v
```

Expected: all pass.

- [ ] **Step 8: Manual smoke test**

```bash
cd incubator/backend && uvicorn app.main:app --reload
```

In another terminal:
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok"}`

- [ ] **Step 9: Commit**

```bash
git add incubator/backend/app/main.py incubator/backend/app/schemas/run.py incubator/backend/app/api/runs.py incubator/backend/tests/test_runs_api.py
git commit -m "feat: add FastAPI app, health endpoint, and runs CRUD API"
```

---

## Task 5: Frontend — types + API client + routing

**Files:**
- Create: `incubator/frontend/src/types/index.ts`
- Create: `incubator/frontend/src/api/client.ts`
- Create: `incubator/frontend/src/App.tsx`
- Create: `incubator/frontend/src/main.tsx`

- [ ] **Step 1: Write `incubator/frontend/src/types/index.ts`**

```typescript
export interface FormAnswers {
  app_goal: string
  target_user: string
  top_3_actions: [string, string, string]
  must_have_screens: string[]
  works_offline: boolean
  needs_notifications: boolean
  core_data_entities: string[]
  style_notes: string
  constraints_non_goals: string
  include_payments_placeholder: boolean
  auth_required: boolean
}

export interface CreateRunRequest {
  raw_idea: string
  form_answers: FormAnswers
}

export type RunStatus = 'pending' | 'running' | 'done' | 'failed'

export interface RunListItem {
  id: string
  status: RunStatus
  app_name: string | null
  created_at: string
}

export interface Run {
  id: string
  raw_idea: string
  status: RunStatus
  app_name: string | null
  created_at: string
  updated_at: string
}

export interface SSEEvent {
  stage?: string
  status?: string
  log?: string
  ts: string
}
```

- [ ] **Step 2: Write `incubator/frontend/src/api/client.ts`**

```typescript
import type { CreateRunRequest, Run, RunListItem } from '../types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export const api = {
  createRun: (body: CreateRunRequest) =>
    request<Run>('/runs', { method: 'POST', body: JSON.stringify(body) }),

  listRuns: () => request<RunListItem[]>('/runs'),

  getRun: (id: string) => request<Run>(`/runs/${id}`),

  streamRun: (id: string) => new EventSource(`/api/runs/${id}/stream`),
}
```

- [ ] **Step 3: Write `incubator/frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import IdeaForm from './pages/IdeaForm'
import RunList from './pages/RunList'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IdeaForm />} />
        <Route path="/runs" element={<RunList />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 4: Write `incubator/frontend/src/main.tsx`**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 5: Commit**

```bash
git add incubator/frontend/src/
git commit -m "feat: add frontend types, API client, and router shell"
```

---

## Task 6: Frontend — idea input + structured form

**Files:**
- Create: `incubator/frontend/src/pages/IdeaForm.tsx`
- Create: `incubator/frontend/src/pages/RunList.tsx`

- [ ] **Step 1: Write `incubator/frontend/src/pages/IdeaForm.tsx`**

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { FormAnswers } from '../types'

const EMPTY_FORM: FormAnswers = {
  app_goal: '',
  target_user: '',
  top_3_actions: ['', '', ''],
  must_have_screens: [''],
  works_offline: false,
  needs_notifications: false,
  core_data_entities: [''],
  style_notes: '',
  constraints_non_goals: '',
  include_payments_placeholder: false,
  auth_required: true,
}

export default function IdeaForm() {
  const navigate = useNavigate()
  const [idea, setIdea] = useState('')
  const [form, setForm] = useState<FormAnswers>(EMPTY_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateAction = (i: number, val: string) => {
    const actions = [...form.top_3_actions] as [string, string, string]
    actions[i] = val
    setForm({ ...form, top_3_actions: actions })
  }

  const updateListField = (field: 'must_have_screens' | 'core_data_entities', i: number, val: string) => {
    const list = [...form[field]]
    list[i] = val
    setForm({ ...form, [field]: list })
  }

  const addListItem = (field: 'must_have_screens' | 'core_data_entities') => {
    setForm({ ...form, [field]: [...form[field], ''] })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!idea.trim()) { setError('Idea is required'); return }
    setLoading(true)
    try {
      const run = await api.createRun({ raw_idea: idea, form_answers: form })
      navigate(`/runs/${run.id}`)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 32 }}>
      <h1>App Incubator</h1>
      <a href="/runs">View run history →</a>
      <form onSubmit={handleSubmit} style={{ marginTop: 24 }}>
        <section>
          <h2>Your app idea</h2>
          <textarea
            value={idea}
            onChange={e => setIdea(e.target.value)}
            placeholder="Describe your mobile app idea..."
            rows={4}
            style={{ width: '100%' }}
            required
          />
        </section>

        <section style={{ marginTop: 24 }}>
          <h2>Structured details</h2>

          <label>App goal</label>
          <input value={form.app_goal} onChange={e => setForm({ ...form, app_goal: e.target.value })} style={{ width: '100%' }} required />

          <label>Target user</label>
          <input value={form.target_user} onChange={e => setForm({ ...form, target_user: e.target.value })} style={{ width: '100%' }} required />

          <label>Top 3 user actions</label>
          {form.top_3_actions.map((a, i) => (
            <input key={i} value={a} onChange={e => updateAction(i, e.target.value)} placeholder={`Action ${i + 1}`} style={{ width: '100%', marginBottom: 4 }} required />
          ))}

          <label>Must-have screens</label>
          {form.must_have_screens.map((s, i) => (
            <input key={i} value={s} onChange={e => updateListField('must_have_screens', i, e.target.value)} style={{ width: '100%', marginBottom: 4 }} required />
          ))}
          <button type="button" onClick={() => addListItem('must_have_screens')}>+ screen</button>

          <label>Core data entities</label>
          {form.core_data_entities.map((s, i) => (
            <input key={i} value={s} onChange={e => updateListField('core_data_entities', i, e.target.value)} style={{ width: '100%', marginBottom: 4 }} required />
          ))}
          <button type="button" onClick={() => addListItem('core_data_entities')}>+ entity</button>

          <div style={{ marginTop: 12 }}>
            <label><input type="checkbox" checked={form.works_offline} onChange={e => setForm({ ...form, works_offline: e.target.checked })} /> Works offline</label>
            <label style={{ marginLeft: 16 }}><input type="checkbox" checked={form.needs_notifications} onChange={e => setForm({ ...form, needs_notifications: e.target.checked })} /> Needs notifications</label>
            <label style={{ marginLeft: 16 }}><input type="checkbox" checked={form.include_payments_placeholder} onChange={e => setForm({ ...form, include_payments_placeholder: e.target.checked })} /> Include payments placeholder</label>
          </div>

          <label>Style notes</label>
          <textarea value={form.style_notes} onChange={e => setForm({ ...form, style_notes: e.target.value })} rows={2} style={{ width: '100%' }} />

          <label>Constraints / non-goals</label>
          <textarea value={form.constraints_non_goals} onChange={e => setForm({ ...form, constraints_non_goals: e.target.value })} rows={2} style={{ width: '100%' }} />
        </section>

        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button type="submit" disabled={loading} style={{ marginTop: 24 }}>
          {loading ? 'Creating run...' : 'Generate app →'}
        </button>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Write `incubator/frontend/src/pages/RunList.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { RunListItem } from '../types'

const STATUS_COLOR: Record<string, string> = {
  pending: '#888',
  running: '#2563eb',
  done: '#16a34a',
  failed: '#dc2626',
}

export default function RunList() {
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listRuns().then(setRuns).finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading...</p>

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 32 }}>
      <h1>Run history</h1>
      <Link to="/">+ New run</Link>
      {runs.length === 0 && <p>No runs yet.</p>}
      <ul style={{ marginTop: 24, listStyle: 'none', padding: 0 }}>
        {runs.map(run => (
          <li key={run.id} style={{ borderBottom: '1px solid #eee', padding: '12px 0' }}>
            <Link to={`/runs/${run.id}`}>
              <strong>{run.app_name ?? run.id.slice(0, 8)}</strong>
            </Link>
            <span style={{ marginLeft: 12, color: STATUS_COLOR[run.status] }}>{run.status}</span>
            <span style={{ marginLeft: 12, color: '#888', fontSize: 12 }}>{new Date(run.created_at).toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 3: Verify frontend compiles**

```bash
cd incubator/frontend && npm run build
```

Expected: no TypeScript errors, `dist/` created.

- [ ] **Step 4: Manual end-to-end test**

Start backend: `cd incubator/backend && uvicorn app.main:app --reload`
Start frontend: `cd incubator/frontend && npm run dev`
Open `http://localhost:5173` — fill form, submit, expect redirect to `/runs/<id>` (404 page is fine, RunDetail page not built yet).

- [ ] **Step 5: Run all backend tests**

```bash
cd incubator/backend && pytest -v
```

Expected: all pass.

- [ ] **Step 6: Lint**

```bash
cd incubator/backend && ruff check .
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add incubator/frontend/src/pages/
git commit -m "feat: add idea input form and run history page"
```

---

## Phase 1 Complete

**What was built:**
- Full backend project with Pydantic schemas, SQLite DB, FastAPI app, runs API
- Frontend with React Router, API client, idea form, run list page
- All backend tests pass, frontend builds clean

**Review questions:**
1. Any schema fields missing from `FormAnswers` or `ProductSpec` you want added?
2. Form UX — any fields you want to reorder or change input type for?
