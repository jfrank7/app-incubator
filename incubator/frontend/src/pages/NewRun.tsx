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

interface Props { onRunCreated: () => void }

export default function NewRun({ onRunCreated }: Props) {
  const navigate = useNavigate()
  const [idea, setIdea] = useState('')
  const [form, setForm] = useState<FormAnswers>(EMPTY_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)

  type ListField = 'top_3_actions' | 'must_have_screens' | 'core_data_entities'

  const updateList = (field: ListField, i: number, val: string) => {
    const list = [...form[field]]; list[i] = val
    setForm({ ...form, [field]: list })
  }
  const addListItem = (field: ListField) => setForm({ ...form, [field]: [...form[field], ''] })
  const removeListItem = (field: ListField, i: number) => {
    const list = form[field].filter((_, idx) => idx !== i)
    setForm({ ...form, [field]: list.length > 0 ? list : [''] })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!idea.trim()) { setError('Describe your app idea first'); return }
    setError(null)
    setLoading(true)
    try {
      const run = await api.createRun({ raw_idea: idea, form_answers: form })
      onRunCreated()
      navigate(`/runs/${run.id}`)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '48px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.5px', marginBottom: 8 }}>
          What are you building?
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 15 }}>
          Describe your mobile app idea and Claude will generate a complete Expo + FastAPI codebase.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Idea textarea */}
        <div style={{ marginBottom: 20 }}>
          <textarea
            value={idea}
            onChange={e => setIdea(e.target.value)}
            placeholder="e.g. A habit tracker where users log daily streaks, get reminded at a set time, and can share progress with friends..."
            rows={5}
            style={{
              width: '100%',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 10,
              padding: '14px 16px',
              color: 'var(--text)',
              fontSize: 15,
              resize: 'vertical',
              outline: 'none',
              fontFamily: 'inherit',
              lineHeight: 1.6,
              transition: 'border-color 0.15s',
            }}
            onFocus={e => e.currentTarget.style.borderColor = 'var(--accent)'}
            onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
          />
        </div>

        {/* Structured fields */}
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 10,
          overflow: 'hidden',
          marginBottom: 20,
        }}>
          {/* Always-visible core fields */}
          <div style={{ padding: 20 }}>
            <Label>What's the core goal?</Label>
            <Input
              value={form.app_goal}
              onChange={v => setForm({ ...form, app_goal: v })}
              placeholder="Help users track their daily water intake"
            />

            <Label mt>Who is this for?</Label>
            <Input
              value={form.target_user}
              onChange={v => setForm({ ...form, target_user: v })}
              placeholder="Health-conscious adults who want to build habits"
            />

            <Label mt>Top 3 user actions</Label>
            {form.top_3_actions.map((a, i) => (
              <ListInput key={i} value={a} placeholder={`Action ${i + 1}`}
                onChange={v => updateList('top_3_actions', i, v)}
                onRemove={() => removeListItem('top_3_actions', i)} />
            ))}
            <AddButton onClick={() => addListItem('top_3_actions')}>+ Add action</AddButton>

            {/* Toggle switches */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 20 }}>
              <Toggle label="Auth required" checked={form.auth_required ?? true}
                onChange={v => setForm({ ...form, auth_required: v })} />
              <Toggle label="Works offline" checked={form.works_offline}
                onChange={v => setForm({ ...form, works_offline: v })} />
              <Toggle label="Notifications" checked={form.needs_notifications}
                onChange={v => setForm({ ...form, needs_notifications: v })} />
              <Toggle label="Payments placeholder" checked={form.include_payments_placeholder ?? false}
                onChange={v => setForm({ ...form, include_payments_placeholder: v })} />
            </div>
          </div>

          {/* Advanced toggle */}
          <div
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{
              padding: '10px 20px',
              borderTop: '1px solid var(--border-subtle)',
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
              color: 'var(--text-muted)', fontSize: 13,
              userSelect: 'none',
              background: showAdvanced ? 'var(--surface-2)' : 'transparent',
            }}>
            <span style={{ transition: 'transform 0.15s', display: 'inline-block', transform: showAdvanced ? 'rotate(90deg)' : 'none' }}>›</span>
            Advanced details
          </div>

          {showAdvanced && (
            <div style={{ padding: '16px 20px 20px', borderTop: '1px solid var(--border-subtle)' }}>
              <Label>Must-have screens</Label>
              {form.must_have_screens.map((s, i) => (
                <ListInput key={i} value={s} placeholder="Screen name or description"
                  onChange={v => updateList('must_have_screens', i, v)}
                  onRemove={() => removeListItem('must_have_screens', i)} />
              ))}
              <AddButton onClick={() => addListItem('must_have_screens')}>+ Add screen</AddButton>

              <Label mt>Core data entities</Label>
              {form.core_data_entities.map((s, i) => (
                <ListInput key={i} value={s} placeholder="e.g. Entry, Goal, Achievement"
                  onChange={v => updateList('core_data_entities', i, v)}
                  onRemove={() => removeListItem('core_data_entities', i)} />
              ))}
              <AddButton onClick={() => addListItem('core_data_entities')}>+ Add entity</AddButton>

              <Label mt>Style notes</Label>
              <textarea value={form.style_notes} onChange={e => setForm({ ...form, style_notes: e.target.value })}
                placeholder="e.g. Dark theme, minimalist, gamified with streaks"
                rows={2} style={textareaStyle} />

              <Label mt>Constraints / non-goals</Label>
              <textarea value={form.constraints_non_goals} onChange={e => setForm({ ...form, constraints_non_goals: e.target.value })}
                placeholder="e.g. No social features, no real payments, MVP only"
                rows={2} style={textareaStyle} />
            </div>
          )}
        </div>

        {error && (
          <div style={{ background: 'var(--error-muted)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: '10px 14px', color: 'var(--error)', fontSize: 13, marginBottom: 16 }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '13px 20px',
            background: loading ? 'var(--text-subtle)' : 'linear-gradient(135deg, var(--accent), #3b82f6)',
            border: 'none',
            borderRadius: 9,
            color: '#fff',
            fontSize: 15,
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'opacity 0.15s',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
          }}>
          {loading ? (
            <>
              <Spinner /> Creating run...
            </>
          ) : (
            'Generate app →'
          )}
        </button>
      </form>
    </div>
  )
}

// ── Micro components ──────────────────────────────────────────────────────────

const textareaStyle: React.CSSProperties = {
  width: '100%', background: 'var(--bg)', border: '1px solid var(--border)',
  borderRadius: 7, padding: '10px 12px', color: 'var(--text)', fontSize: 14,
  resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.5, outline: 'none',
  marginTop: 6,
}

function Label({ children, mt }: { children: React.ReactNode; mt?: boolean }) {
  return <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 6, marginTop: mt ? 16 : 0 }}>{children}</div>
}

function Input({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 7, padding: '9px 12px', color: 'var(--text)', fontSize: 14, fontFamily: 'inherit', outline: 'none' }} />
  )
}

function ListInput({ value, onChange, onRemove, placeholder }: { value: string; onChange: (v: string) => void; onRemove: () => void; placeholder?: string }) {
  return (
    <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={{ flex: 1, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 7, padding: '8px 12px', color: 'var(--text)', fontSize: 14, fontFamily: 'inherit', outline: 'none' }} />
      <button type="button" onClick={onRemove}
        style={{ width: 32, height: 32, borderRadius: 7, border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-subtle)', cursor: 'pointer', fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', alignSelf: 'center' }}>×</button>
    </div>
  )
}

function AddButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick}
      style={{ fontSize: 12, color: 'var(--accent)', background: 'transparent', border: 'none', cursor: 'pointer', padding: '2px 0', marginTop: 2 }}>
      {children}
    </button>
  )
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' }}>
      <div
        onClick={() => onChange(!checked)}
        style={{
          width: 36, height: 20, borderRadius: 10,
          background: checked ? 'var(--accent)' : 'var(--border)',
          position: 'relative', transition: 'background 0.2s', flexShrink: 0,
        }}>
        <div style={{
          position: 'absolute', top: 2, left: checked ? 18 : 2,
          width: 16, height: 16, borderRadius: '50%', background: '#fff',
          transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
        }} />
      </div>
      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
    </label>
  )
}

function Spinner() {
  return (
    <div style={{
      width: 14, height: 14, borderRadius: '50%',
      border: '2px solid rgba(255,255,255,0.3)',
      borderTopColor: '#fff',
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}
