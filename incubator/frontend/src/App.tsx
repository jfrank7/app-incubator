import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import NewRun from './pages/NewRun'
import RunDetail from './pages/RunDetail'
import { api } from './api/client'
import type { RunListItem } from './types'

const STATUS_DOT: Record<string, string> = {
  pending: '#64748b',
  generating_spec: '#3b82f6',
  awaiting_spec_review: '#f59e0b',
  generating_blueprint: '#3b82f6',
  awaiting_blueprint_review: '#f59e0b',
  generating_shell: '#3b82f6',
  awaiting_shell_review: '#f59e0b',
  building_full: '#3b82f6',
  done: '#10b981',
  failed: '#ef4444',
}

function Sidebar({ runs, loading }: { runs: RunListItem[]; loading: boolean }) {
  return (
    <aside style={{
      width: 240,
      minWidth: 240,
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--surface)',
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 7,
            background: 'linear-gradient(135deg, #7c3aed, #3b82f6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 700, color: '#fff',
          }}>A</div>
          <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text)' }}>App Incubator</span>
        </div>
      </div>

      {/* New Run button */}
      <div style={{ padding: '12px 12px 8px' }}>
        <NavLink to="/" end style={({ isActive }) => ({
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 10px',
          borderRadius: 7,
          textDecoration: 'none',
          fontSize: 13,
          fontWeight: 500,
          background: isActive ? 'var(--accent-muted)' : 'transparent',
          color: isActive ? '#a78bfa' : 'var(--text-muted)',
          transition: 'all 0.15s',
        })}>
          <PlusIcon />
          New run
        </NavLink>
      </div>

      {/* Divider */}
      <div style={{ padding: '0 12px 8px' }}>
        <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-subtle)', padding: '4px 10px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Recent</div>
      </div>

      {/* Run list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px 12px' }}>
        {loading && (
          <div style={{ padding: '8px 10px', color: 'var(--text-subtle)', fontSize: 13 }}>Loading...</div>
        )}
        {runs.length === 0 && !loading && (
          <div style={{ padding: '8px 10px', color: 'var(--text-subtle)', fontSize: 13 }}>No runs yet</div>
        )}
        {runs.map(run => (
          <NavLink key={run.id} to={`/runs/${run.id}`} style={({ isActive }) => ({
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
            padding: '8px 10px',
            borderRadius: 7,
            textDecoration: 'none',
            marginBottom: 2,
            background: isActive ? 'var(--surface-2)' : 'transparent',
            border: isActive ? '1px solid var(--border)' : '1px solid transparent',
            transition: 'all 0.1s',
          })}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
                background: STATUS_DOT[run.status] ?? '#64748b',
                boxShadow: run.status.includes('generating') || run.status === 'building_full'
                  ? `0 0 6px ${STATUS_DOT[run.status]}`
                  : 'none',
              }} />
              <span style={{ fontSize: 13, color: 'var(--text)', fontWeight: 500, truncate: true, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {run.app_name ?? run.id.slice(0, 8)}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-subtle)', paddingLeft: 14 }}>
              {formatStatus(run.status)}
            </div>
          </NavLink>
        ))}
      </div>
    </aside>
  )
}

function formatStatus(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

export default function App() {
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loading, setLoading] = useState(true)

  const refreshRuns = () => {
    api.listRuns()
      .then(r => setRuns(r.slice(0, 30)))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    refreshRuns()
    const iv = setInterval(refreshRuns, 5000)
    return () => clearInterval(iv)
  }, [])

  return (
    <BrowserRouter>
      <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
        <Sidebar runs={runs} loading={loading} />
        <main style={{ flex: 1, overflowY: 'auto', background: 'var(--bg)' }}>
          <Routes>
            <Route path="/" element={<NewRun onRunCreated={refreshRuns} />} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
