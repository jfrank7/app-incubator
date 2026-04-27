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
}
