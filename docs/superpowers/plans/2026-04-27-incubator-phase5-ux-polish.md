> **SUPERSEDED** — See 2026-04-28-agentic-redesign.md

# Agentic App Incubator — Phase 5: UX Polish + E2E Validation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the frontend with run detail (live SSE progress), artifacts viewer, QA report view, and error display. Then run end-to-end validation generating the Caffeine Tracker sample app.

**Architecture:** React pages consuming SSE stream via `EventSource`. Artifacts and QA pages fetch from REST endpoints. E2E test submits Caffeine Tracker idea and verifies generated repo structure.

**Tech Stack:** React 18, React Router v6, EventSource API, TypeScript

**Prerequisite:** Phases 1–4 complete.

---

## File Map

**Create:**
- `incubator/frontend/src/pages/RunDetail.tsx`
- `incubator/frontend/src/pages/Artifacts.tsx`
- `incubator/frontend/src/pages/QAReport.tsx`
- `incubator/frontend/src/components/ProgressStream.tsx`
- `incubator/frontend/src/components/QAReportView.tsx`
- `incubator/frontend/src/components/FileTree.tsx`
- `incubator/backend/tests/test_e2e.py`

**Modify:**
- `incubator/frontend/src/App.tsx` — add RunDetail, Artifacts, QAReport routes

---

## Task 20: Run detail page with live SSE progress

**Files:**
- Create: `incubator/frontend/src/components/ProgressStream.tsx`
- Create: `incubator/frontend/src/pages/RunDetail.tsx`

- [ ] **Step 1: Write `incubator/frontend/src/components/ProgressStream.tsx`**

```tsx
import { useEffect, useRef, useState } from 'react'
import type { SSEEvent } from '../types'

interface Props {
  runId: string
  onDone: (finalStatus: string) => void
}

const STAGE_LABELS: Record<string, string> = {
  intake: 'Intake',
  spec_generator: 'Generating spec',
  spec_validator: 'Validating spec',
  architecture_mapper: 'Mapping architecture',
  template_selector: 'Selecting templates',
  scaffolder: 'Scaffolding files',
  task_planner: 'Planning tasks',
  repo_editor: 'Editing repo',
  qa_runner: 'Running QA',
  fix_loop: 'Fixing issues',
  delivery_packager: 'Packaging output',
}

interface StageStatus {
  label: string
  status: 'pending' | 'started' | 'completed' | 'failed'
}

export default function ProgressStream({ runId, onDone }: Props) {
  const [stages, setStages] = useState<Record<string, StageStatus>>({})
  const [logs, setLogs] = useState<string[]>([])
  const [connected, setConnected] = useState(false)
  const logsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const es = new EventSource(`/api/runs/${runId}/stream`)
    es.onopen = () => setConnected(true)

    es.onmessage = (e) => {
      const event: SSEEvent = JSON.parse(e.data)

      if (event.done) {
        onDone(event.final_status ?? 'done')
        es.close()
        return
      }

      if (event.stage && event.status) {
        setStages(prev => ({
          ...prev,
          [event.stage!]: {
            label: STAGE_LABELS[event.stage!] ?? event.stage!,
            status: event.status as StageStatus['status'],
          },
        }))
      }

      if (event.log) {
        setLogs(prev => [...prev.slice(-199), event.log!])
      }
    }

    es.onerror = () => {
      setConnected(false)
      es.close()
    }

    return () => es.close()
  }, [runId])

  useEffect(() => {
    logsRef.current?.scrollTo(0, logsRef.current.scrollHeight)
  }, [logs])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: connected ? '#16a34a' : '#dc2626', display: 'inline-block' }} />
        <span style={{ fontSize: 12, color: '#666' }}>{connected ? 'Connected' : 'Disconnected'}</span>
      </div>

      <div style={{ marginBottom: 16 }}>
        {Object.entries(STAGE_LABELS).map(([key, label]) => {
          const stage = stages[key]
          const color = !stage ? '#ddd' : stage.status === 'completed' ? '#16a34a' : stage.status === 'started' ? '#2563eb' : '#dc2626'
          return (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
              <span style={{ fontSize: 14, color: stage?.status === 'completed' ? '#111' : '#666' }}>{label}</span>
              {stage?.status === 'started' && <span style={{ fontSize: 12, color: '#2563eb' }}>running...</span>}
            </div>
          )
        })}
      </div>

      <div
        ref={logsRef}
        style={{ background: '#111', color: '#e2e8f0', fontFamily: 'monospace', fontSize: 12, padding: 12, borderRadius: 6, height: 200, overflowY: 'auto' }}
      >
        {logs.length === 0 && <span style={{ color: '#666' }}>Waiting for logs...</span>}
        {logs.map((line, i) => <div key={i}>{line}</div>)}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Write `incubator/frontend/src/pages/RunDetail.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Run } from '../types'
import ProgressStream from '../components/ProgressStream'

const STATUS_COLOR: Record<string, string> = {
  pending: '#888',
  running: '#2563eb',
  done: '#16a34a',
  failed: '#dc2626',
}

export default function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<Run | null>(null)
  const [loading, setLoading] = useState(true)
  const [finalStatus, setFinalStatus] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api.getRun(id).then(r => { setRun(r); setLoading(false) })
  }, [id])

  const handleDone = (status: string) => {
    setFinalStatus(status)
    if (id) api.getRun(id).then(setRun)
  }

  if (loading) return <p style={{ padding: 32 }}>Loading...</p>
  if (!run) return <p style={{ padding: 32 }}>Run not found.</p>

  const isActive = run.status === 'running' || run.status === 'pending'

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 32 }}>
      <nav style={{ marginBottom: 24 }}>
        <Link to="/runs">← Run history</Link>
      </nav>

      <h1 style={{ marginBottom: 4 }}>{run.app_name ?? 'Generating...'}</h1>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 24 }}>
        <span style={{ color: STATUS_COLOR[finalStatus ?? run.status], fontWeight: 600 }}>
          {finalStatus ?? run.status}
        </span>
        <span style={{ color: '#888', fontSize: 12 }}>{new Date(run.created_at).toLocaleString()}</span>
      </div>

      <p style={{ color: '#666', marginBottom: 24 }}><em>{run.raw_idea}</em></p>

      {(isActive && !finalStatus) && (
        <section style={{ marginBottom: 32 }}>
          <h2>Generation progress</h2>
          <ProgressStream runId={run.id} onDone={handleDone} />
        </section>
      )}

      {(finalStatus === 'done' || run.status === 'done') && (
        <section style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: 16, marginBottom: 24 }}>
          <strong style={{ color: '#16a34a' }}>Generation complete</strong>
          <p style={{ marginTop: 8, marginBottom: 0 }}>
            App generated at <code>~/generated-apps/{run.id}/</code>
          </p>
          <div style={{ marginTop: 12, display: 'flex', gap: 12 }}>
            <Link to={`/runs/${run.id}/artifacts`}>View artifacts →</Link>
            <Link to={`/runs/${run.id}/qa`}>View QA report →</Link>
          </div>
        </section>
      )}

      {(finalStatus === 'failed' || run.status === 'failed') && (
        <section style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: 16, marginBottom: 24 }}>
          <strong style={{ color: '#dc2626' }}>Generation failed</strong>
          <p style={{ marginTop: 8, marginBottom: 8 }}>The pipeline could not complete successfully.</p>
          <Link to={`/runs/${run.id}/qa`}>View failure report →</Link>
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add incubator/frontend/src/components/ProgressStream.tsx incubator/frontend/src/pages/RunDetail.tsx
git commit -m "feat: add run detail page with live SSE progress stream"
```

---

## Task 21: Artifacts + QA report pages

**Files:**
- Create: `incubator/frontend/src/pages/Artifacts.tsx`
- Create: `incubator/frontend/src/pages/QAReport.tsx`
- Create: `incubator/frontend/src/components/QAReportView.tsx`

- [ ] **Step 1: Write `incubator/frontend/src/components/QAReportView.tsx`**

```tsx
interface QACheck {
  name: string
  passed: boolean
  output: string
  error: string | null
}

interface QAResults {
  passed: boolean
  checks: QACheck[]
  summary: string
  generated_at: string
}

interface Props {
  qa: QAResults
}

export default function QAReportView({ qa }: Props) {
  return (
    <div>
      <div style={{ marginBottom: 16, padding: '8px 16px', borderRadius: 6, background: qa.passed ? '#f0fdf4' : '#fef2f2', border: `1px solid ${qa.passed ? '#bbf7d0' : '#fecaca'}` }}>
        <strong style={{ color: qa.passed ? '#16a34a' : '#dc2626' }}>
          {qa.passed ? 'All checks passed' : 'QA failed'}
        </strong>
        <p style={{ margin: '4px 0 0', color: '#666' }}>{qa.summary}</p>
      </div>

      {qa.checks.map(check => (
        <div key={check.name} style={{ marginBottom: 16, border: '1px solid #e5e7eb', borderRadius: 6, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: check.passed ? '#16a34a' : '#dc2626', display: 'inline-block' }} />
            <strong style={{ fontFamily: 'monospace' }}>{check.name}</strong>
            <span style={{ marginLeft: 'auto', fontSize: 12, color: check.passed ? '#16a34a' : '#dc2626' }}>{check.passed ? 'PASS' : 'FAIL'}</span>
          </div>
          {(!check.passed || check.output) && (
            <pre style={{ margin: 0, padding: 12, fontSize: 12, background: '#1e1e1e', color: '#e2e8f0', overflowX: 'auto', maxHeight: 300 }}>
              {check.error ?? check.output}
            </pre>
          )}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Write `incubator/frontend/src/pages/QAReport.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import QAReportView from '../components/QAReportView'

export default function QAReport() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<{ qa_report: any; error_summary: string | null } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    fetch(`/api/runs/${id}/qa`)
      .then(r => r.json())
      .then(setData)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <p style={{ padding: 32 }}>Loading...</p>

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 32 }}>
      <nav style={{ marginBottom: 24 }}>
        <Link to={`/runs/${id}`}>← Run detail</Link>
      </nav>
      <h1>QA Report</h1>

      {data?.error_summary && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: 16, marginBottom: 24 }}>
          <strong style={{ color: '#dc2626' }}>Pipeline error</strong>
          <pre style={{ marginTop: 8, fontSize: 12, color: '#991b1b' }}>{data.error_summary}</pre>
        </div>
      )}

      {data?.qa_report ? (
        <QAReportView qa={data.qa_report} />
      ) : (
        <p style={{ color: '#888' }}>No QA report available yet.</p>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Write `incubator/frontend/src/pages/Artifacts.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

export default function Artifacts() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<{ product_spec: any; blueprint: any; stage_logs: any[] } | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'spec' | 'blueprint' | 'logs'>('spec')

  useEffect(() => {
    if (!id) return
    fetch(`/api/runs/${id}/artifacts`)
      .then(r => r.json())
      .then(setData)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <p style={{ padding: 32 }}>Loading...</p>

  const tabs: { key: typeof activeTab; label: string }[] = [
    { key: 'spec', label: 'Product spec' },
    { key: 'blueprint', label: 'Blueprint' },
    { key: 'logs', label: 'Stage logs' },
  ]

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 32 }}>
      <nav style={{ marginBottom: 24 }}>
        <Link to={`/runs/${id}`}>← Run detail</Link>
      </nav>
      <h1>Artifacts</h1>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{ padding: '6px 16px', borderRadius: 6, border: '1px solid #e5e7eb', background: activeTab === tab.key ? '#2563eb' : '#fff', color: activeTab === tab.key ? '#fff' : '#111', cursor: 'pointer' }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'spec' && (
        <pre style={{ background: '#1e1e1e', color: '#e2e8f0', padding: 16, borderRadius: 6, fontSize: 12, overflow: 'auto' }}>
          {data?.product_spec ? JSON.stringify(data.product_spec, null, 2) : 'No spec yet.'}
        </pre>
      )}

      {activeTab === 'blueprint' && (
        <pre style={{ background: '#1e1e1e', color: '#e2e8f0', padding: 16, borderRadius: 6, fontSize: 12, overflow: 'auto' }}>
          {data?.blueprint ? JSON.stringify(data.blueprint, null, 2) : 'No blueprint yet.'}
        </pre>
      )}

      {activeTab === 'logs' && (
        <div>
          {data?.stage_logs?.length ? data.stage_logs.map((log, i) => (
            <div key={i} style={{ display: 'flex', gap: 12, padding: '6px 0', borderBottom: '1px solid #f3f4f6', fontFamily: 'monospace', fontSize: 13 }}>
              <span style={{ color: '#2563eb', minWidth: 180 }}>{log.stage}</span>
              <span style={{ color: log.status === 'completed' ? '#16a34a' : '#888' }}>{log.status}</span>
            </div>
          )) : <p style={{ color: '#888' }}>No logs yet.</p>}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Update `incubator/frontend/src/App.tsx`** to add all routes

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import IdeaForm from './pages/IdeaForm'
import RunList from './pages/RunList'
import RunDetail from './pages/RunDetail'
import Artifacts from './pages/Artifacts'
import QAReport from './pages/QAReport'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IdeaForm />} />
        <Route path="/runs" element={<RunList />} />
        <Route path="/runs/:id" element={<RunDetail />} />
        <Route path="/runs/:id/artifacts" element={<Artifacts />} />
        <Route path="/runs/:id/qa" element={<QAReport />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd incubator/frontend && npm run build
```

Expected: no TypeScript errors, `dist/` created.

- [ ] **Step 6: Commit**

```bash
git add incubator/frontend/src/
git commit -m "feat: add artifacts viewer, QA report page, and complete frontend routing"
```

---

## Task 22: E2E smoke test — Caffeine Tracker generation

**Files:**
- Create: `incubator/backend/tests/test_e2e.py`

This test validates the full pipeline generates expected output for the Caffeine Tracker sample app. It calls Claude — skip in CI unless `ANTHROPIC_API_KEY` is set.

- [ ] **Step 1: Write `incubator/backend/tests/test_e2e.py`**

```python
import os
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping E2E test",
)

CAFFEINE_PAYLOAD = {
    "raw_idea": "Build a mobile app that helps users track daily caffeine intake and reduce consumption gradually.",
    "form_answers": {
        "app_goal": "Help users reduce caffeine consumption over time",
        "target_user": "Health-conscious adults who want to reduce caffeine dependency",
        "top_3_actions": [
            "Log a caffeine drink with amount",
            "View today's total caffeine intake",
            "Set and track a daily reduction goal",
        ],
        "must_have_screens": ["login", "dashboard", "add entry", "history", "settings", "subscription placeholder"],
        "works_offline": True,
        "needs_notifications": False,
        "core_data_entities": ["CaffeineEntry", "DailyGoal", "User"],
        "style_notes": "Clean, minimal health app aesthetic. Calming colors.",
        "constraints_non_goals": "No social features. No real-time sync. Simple utility only.",
        "include_payments_placeholder": True,
        "auth_required": True,
    },
}


@pytest.mark.asyncio
async def test_caffeine_tracker_generation_e2e():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create run
        r = await client.post("/api/runs", json=CAFFEINE_PAYLOAD)
        assert r.status_code == 201, f"Create run failed: {r.text}"
        run_id = r.json()["id"]

        # 2. Poll until done (up to 10 min)
        import asyncio
        for _ in range(120):
            await asyncio.sleep(5)
            r = await client.get(f"/api/runs/{run_id}")
            status = r.json()["status"]
            if status in ("done", "failed"):
                break

        assert status == "done", f"Run ended with status: {status}"

        # 3. Check artifacts endpoint
        r = await client.get(f"/api/runs/{run_id}/artifacts")
        assert r.status_code == 200
        artifacts = r.json()
        assert artifacts["product_spec"] is not None
        assert artifacts["blueprint"] is not None

        # 4. Check generated files on disk
        from app.config import settings
        output_dir = settings.generated_apps_path / run_id
        assert output_dir.exists(), f"Output dir not found: {output_dir}"

        expected_paths = [
            "apps/mobile/package.json",
            "apps/mobile/app.json",
            "apps/mobile/app/_layout.tsx",
            "apps/mobile/app/(auth)/login.tsx",
            "apps/mobile/app/(auth)/signup.tsx",
            "backend/app/main.py",
            "backend/app/auth/router.py",
            "backend/pyproject.toml",
            "incubator/product_spec.json",
            "incubator/architecture_blueprint.json",
            "incubator/generation_report.json",
        ]
        for rel_path in expected_paths:
            full = output_dir / rel_path
            assert full.exists(), f"Expected file missing: {rel_path}"
            assert full.stat().st_size > 0, f"File is empty: {rel_path}"

        # 5. Verify spec has expected content
        import json
        spec = json.loads((output_dir / "incubator/product_spec.json").read_text())
        assert "caffeine" in spec["app_name"].lower() or "caffeine" in spec["app_slug"].lower()
        assert spec["auth_required"] is True
        assert spec["payments_placeholder"] is True

        print(f"\nE2E PASS — app generated at {output_dir}")
        print(f"App name: {spec['app_name']}")
        print(f"Modules: {artifacts['blueprint']['selected_modules']}")
```

- [ ] **Step 2: Run unit tests to confirm they still pass**

```bash
cd incubator/backend && pytest -v -k "not e2e"
```

Expected: all pass.

- [ ] **Step 3: Run E2E test (requires ANTHROPIC_API_KEY)**

```bash
cd incubator/backend && ANTHROPIC_API_KEY=your-key pytest tests/test_e2e.py -v -s
```

Expected: `PASS` with app generated at `~/generated-apps/<run-id>/`. May take 3–10 min.

- [ ] **Step 4: Manually verify generated app boots**

```bash
# Backend
cd ~/generated-apps/<run-id>/backend
pip install -e .
uvicorn app.main:app --reload
curl http://localhost:8000/health  # expect {"status":"ok"}

# Mobile
cd ~/generated-apps/<run-id>/apps/mobile
npm install
npx expo start
```

Expected: Expo dev server starts, login screen renders on simulator.

- [ ] **Step 5: Commit**

```bash
git add incubator/backend/tests/test_e2e.py
git commit -m "feat: add E2E test for Caffeine Tracker generation pipeline"
```

---

## Task 23: Final lint + cleanup

- [ ] **Step 1: Run all backend tests**

```bash
cd incubator/backend && pytest -v -k "not e2e"
```

Expected: all pass.

- [ ] **Step 2: Lint backend**

```bash
cd incubator/backend && ruff check .
```

Expected: no errors.

- [ ] **Step 3: Build frontend**

```bash
cd incubator/frontend && npm run build
```

Expected: no TypeScript errors.

- [ ] **Step 4: Verify incubator starts**

```bash
# Terminal 1
cd incubator/backend && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd incubator/frontend && npm run dev
```

Open `http://localhost:5173` — confirm idea form loads, submit creates run, run detail shows progress.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete agentic app incubator MVP — all 5 phases"
```

---

## Phase 5 Complete — MVP Done

**What was built:**
- Full React frontend: idea form, run history, run detail with live SSE, artifacts viewer, QA report
- E2E test validating Caffeine Tracker generation end-to-end
- Complete incubator: FastAPI backend + LangGraph pipeline + React SPA

**All acceptance criteria met:**
1. ✅ Local incubator web app starts
2. ✅ User enters idea + completes structured form
3. ✅ Incubator generates ProductSpec + ArchitectureBlueprint JSON
4. ✅ Fixed Expo + FastAPI architecture selected
5. ✅ Repo scaffolded from base templates + modules
6. ✅ Default auth + payment placeholders included
7. ✅ Verification runs automatically
8. ✅ QA report emitted
9. ✅ Sample app (Caffeine Tracker) boots locally
10. ✅ Failures surfaced clearly when generation cannot complete
