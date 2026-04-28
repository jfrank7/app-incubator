import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Run, RunStatus, SSEEvent } from '../types'

interface LogEntry { ts: string; stage: string; message: string }

const STAGES: { key: RunStatus; label: string; model?: string }[] = [
  { key: 'generating_spec', label: 'Spec Generation', model: 'Opus' },
  { key: 'awaiting_spec_review', label: 'Spec Review', model: '' },
  { key: 'generating_blueprint', label: 'Blueprint', model: 'Opus' },
  { key: 'awaiting_blueprint_review', label: 'Blueprint Review', model: '' },
  { key: 'generating_shell', label: 'Shell Preview', model: 'Sonnet' },
  { key: 'awaiting_shell_review', label: 'Shell Review', model: '' },
  { key: 'building_full', label: 'File Generation', model: 'Sonnet' },
  { key: 'done', label: 'Complete', model: '' },
]

function stageIndex(status: RunStatus): number {
  return STAGES.findIndex(s => s.key === status)
}

export default function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<Run | null>(null)
  const [log, setLog] = useState<LogEntry[]>([])
  const [approving, setApproving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [spec, setSpec] = useState<object | null>(null)
  const [blueprint, setBlueprint] = useState<object | null>(null)
  const [expandedArtifact, setExpandedArtifact] = useState<'spec' | 'blueprint' | 'files' | null>(null)
  const [artifacts, setArtifacts] = useState<{ files: string[] } | null>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const esRef = useRef<EventSource | null>(null)

  const fetchRun = async () => {
    if (!id) return
    const r = await api.getRun(id)
    setRun(r)
    if (r.product_spec_json) {
      try { setSpec(JSON.parse(r.product_spec_json)) } catch {}
    }
    if (r.blueprint_json) {
      try { setBlueprint(JSON.parse(r.blueprint_json)) } catch {}
    }
  }

  useEffect(() => {
    if (!id) return
    fetchRun()

    // Open SSE stream
    const es = new EventSource(`/api/runs/${id}/stream`)
    esRef.current = es

    es.onmessage = (e) => {
      const data = e.data.trim()
      if (data === 'heartbeat ping') return
      try {
        const evt: SSEEvent = JSON.parse(data)
        setLog(prev => [...prev, { ts: new Date().toLocaleTimeString(), stage: evt.stage, message: evt.message }])
        if (evt.done) {
          fetchRun()
          if (evt.final_status === 'done') {
            api.getArtifacts(id).then(a => setArtifacts(a)).catch(() => {})
          }
        }
      } catch {}
    }

    es.onerror = () => es.close()

    return () => { es.close(); esRef.current = null }
  }, [id])

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  const approve = async (action: 'spec' | 'blueprint' | 'shell') => {
    if (!id || !run) return
    setApproving(true)
    setError(null)
    try {
      if (action === 'spec') await api.approveSpec(id, {})
      else if (action === 'blueprint') await api.approveBlueprint(id, {})
      else await api.approveShell(id)
      await fetchRun()
    } catch (e) {
      setError(String(e))
    } finally {
      setApproving(false)
    }
  }

  if (!run) return <LoadingState />

  const idx = stageIndex(run.status as RunStatus)
  const isFailed = run.status === 'failed'
  const isDone = run.status === 'done'

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '36px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 12, color: 'var(--text-subtle)', marginBottom: 6 }}>{run.id}</div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.3px', marginBottom: 6 }}>
          {run.app_name ?? 'Generating...'}
        </h1>
        <StatusBadge status={run.status as RunStatus} />
      </div>

      {/* Pipeline timeline */}
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
        marginBottom: 24,
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', fontSize: 12, fontWeight: 600, color: 'var(--text-subtle)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Pipeline
        </div>
        {STAGES.map((stage, i) => {
          const past = idx > i && !isFailed
          const current = idx === i || (isFailed && idx === i)
          const waiting = idx < i && !isFailed

          return (
            <div key={stage.key} style={{
              display: 'flex',
              alignItems: 'flex-start',
              padding: '13px 20px',
              borderBottom: i < STAGES.length - 1 ? '1px solid var(--border-subtle)' : 'none',
              background: current ? 'var(--surface-2)' : 'transparent',
            }}>
              {/* Status indicator */}
              <div style={{ width: 22, height: 22, flexShrink: 0, marginRight: 14, marginTop: 1 }}>
                {past && <CheckCircle />}
                {current && !isFailed && <SpinnerCircle />}
                {current && isFailed && <ErrorCircle />}
                {waiting && <PendingCircle />}
              </div>

              {/* Stage info */}
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 500, color: waiting ? 'var(--text-subtle)' : 'var(--text)' }}>
                    {stage.label}
                  </span>
                  {stage.model && (
                    <span style={{ fontSize: 11, padding: '2px 7px', borderRadius: 4, background: 'var(--accent-muted)', color: '#a78bfa', fontWeight: 500 }}>
                      {stage.model}
                    </span>
                  )}
                </div>
              </div>

              {/* Action buttons at review stages */}
              {current && !isFailed && stage.key === 'awaiting_spec_review' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  {spec && (
                    <GhostButton onClick={() => setExpandedArtifact(expandedArtifact === 'spec' ? null : 'spec')}>
                      {expandedArtifact === 'spec' ? 'Hide spec' : 'View spec'}
                    </GhostButton>
                  )}
                  <ApproveButton onClick={() => approve('spec')} loading={approving} />
                </div>
              )}
              {current && !isFailed && stage.key === 'awaiting_blueprint_review' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  {blueprint && (
                    <GhostButton onClick={() => setExpandedArtifact(expandedArtifact === 'blueprint' ? null : 'blueprint')}>
                      {expandedArtifact === 'blueprint' ? 'Hide blueprint' : 'View blueprint'}
                    </GhostButton>
                  )}
                  <ApproveButton onClick={() => approve('blueprint')} loading={approving} />
                </div>
              )}
              {current && !isFailed && stage.key === 'awaiting_shell_review' && (
                <ApproveButton onClick={() => approve('shell')} loading={approving} />
              )}
            </div>
          )
        })}
      </div>

      {/* Artifact preview panel */}
      {expandedArtifact === 'spec' && spec && (
        <ArtifactPanel title="Product Spec" data={spec} onClose={() => setExpandedArtifact(null)} />
      )}
      {expandedArtifact === 'blueprint' && blueprint && (
        <ArtifactPanel title="Architecture Blueprint" data={blueprint} onClose={() => setExpandedArtifact(null)} />
      )}

      {/* Done state */}
      {isDone && (
        <div style={{
          background: 'var(--success-muted)',
          border: '1px solid rgba(16,185,129,0.25)',
          borderRadius: 12,
          padding: '20px 24px',
          marginBottom: 24,
        }}>
          <div style={{ fontWeight: 600, color: 'var(--success)', marginBottom: 8 }}>App generated successfully</div>
          <code style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--mono)', display: 'block' }}>
            ~/generated-apps/{run.id}/
          </code>
          {artifacts && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--text-subtle)', marginBottom: 6 }}>Generated files ({artifacts.files.length})</div>
              <div style={{ maxHeight: 180, overflowY: 'auto', background: 'var(--surface)', borderRadius: 7, padding: '8px 12px' }}>
                {artifacts.files.map(f => (
                  <div key={f} style={{ fontSize: 12, fontFamily: 'var(--mono)', color: 'var(--text-muted)', padding: '2px 0' }}>{f}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ background: 'var(--error-muted)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 8, padding: '10px 14px', color: 'var(--error)', fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* Live log */}
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
      }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-subtle)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Live log</div>
          {!isDone && !isFailed && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 6px var(--success)' }} />
              <span style={{ fontSize: 11, color: 'var(--text-subtle)' }}>Live</span>
            </div>
          )}
        </div>
        <div ref={logRef} style={{ height: 280, overflowY: 'auto', padding: '12px 0', fontFamily: 'var(--mono)', fontSize: 12 }}>
          {log.length === 0 && (
            <div style={{ padding: '20px 16px', color: 'var(--text-subtle)', textAlign: 'center' }}>
              Waiting for events...
            </div>
          )}
          {log.map((entry, i) => (
            <div key={i} style={{ padding: '3px 16px', display: 'flex', gap: 12, alignItems: 'baseline' }}>
              <span style={{ color: 'var(--text-subtle)', flexShrink: 0 }}>{entry.ts}</span>
              <span style={{ color: '#a78bfa', flexShrink: 0, fontSize: 11 }}>[{entry.stage}]</span>
              <span style={{ color: 'var(--text-muted)' }}>{entry.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: RunStatus }) {
  const map: Record<string, { color: string; bg: string; label: string }> = {
    pending: { color: '#94a3b8', bg: 'rgba(148,163,184,0.1)', label: 'Pending' },
    done: { color: 'var(--success)', bg: 'var(--success-muted)', label: 'Done' },
    failed: { color: 'var(--error)', bg: 'var(--error-muted)', label: 'Failed' },
  }
  const style = map[status] ?? { color: 'var(--blue)', bg: 'var(--blue-muted)', label: status.replace(/_/g, ' ') }
  return (
    <span style={{ fontSize: 12, padding: '3px 9px', borderRadius: 5, background: style.bg, color: style.color, fontWeight: 500, textTransform: 'capitalize' }}>
      {style.label}
    </span>
  )
}

function ArtifactPanel({ title, data, onClose }: { title: string; data: object; onClose: () => void }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', marginBottom: 16 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{title}</span>
        <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>×</button>
      </div>
      <pre style={{ padding: 16, fontSize: 12, color: 'var(--text-muted)', overflowX: 'auto', maxHeight: 400, lineHeight: 1.5 }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}

function ApproveButton({ onClick, loading }: { onClick: () => void; loading: boolean }) {
  return (
    <button onClick={onClick} disabled={loading} style={{
      padding: '6px 14px', borderRadius: 7, border: 'none',
      background: 'var(--accent)', color: '#fff', fontSize: 13, fontWeight: 600,
      cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1,
      display: 'flex', alignItems: 'center', gap: 6,
    }}>
      {loading ? <><MiniSpinner /> Approving...</> : 'Approve →'}
    </button>
  )
}

function GhostButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      padding: '5px 12px', borderRadius: 7, border: '1px solid var(--border)',
      background: 'transparent', color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer',
    }}>
      {children}
    </button>
  )
}

function CheckCircle() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <circle cx="11" cy="11" r="10" fill="rgba(16,185,129,0.15)" stroke="var(--success)" strokeWidth="1.5"/>
      <path d="M7 11l3 3 5-5" stroke="var(--success)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function SpinnerCircle() {
  return (
    <div style={{
      width: 22, height: 22, borderRadius: '50%',
      border: '2px solid var(--accent-muted)',
      borderTopColor: 'var(--accent)',
      animation: 'spin 0.8s linear infinite',
    }} />
  )
}

function ErrorCircle() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <circle cx="11" cy="11" r="10" fill="var(--error-muted)" stroke="var(--error)" strokeWidth="1.5"/>
      <path d="M8 8l6 6M14 8l-6 6" stroke="var(--error)" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function PendingCircle() {
  return (
    <div style={{ width: 22, height: 22, borderRadius: '50%', border: '1.5px solid var(--border)', background: 'transparent' }} />
  )
}

function MiniSpinner() {
  return <div style={{ width: 12, height: 12, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', animation: 'spin 0.7s linear infinite' }} />
}

function LoadingState() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '50vh', color: 'var(--text-muted)' }}>
      Loading run...
    </div>
  )
}
