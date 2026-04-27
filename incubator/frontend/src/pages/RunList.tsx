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
