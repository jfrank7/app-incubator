import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
    const actions = [...form.top_3_actions]
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

  const removeListItem = (field: 'must_have_screens' | 'core_data_entities', i: number) => {
    const list = form[field].filter((_, idx) => idx !== i)
    setForm({ ...form, [field]: list.length > 0 ? list : [''] })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!idea.trim()) { setError('Idea is required'); return }
    setLoading(true)
    try {
      await api.createRun({ raw_idea: idea, form_answers: form })
      navigate('/runs')
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 32 }}>
      <h1>App Incubator</h1>
      <Link to="/runs">View run history &rarr;</Link>
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
            <div key={i} style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
              <input value={s} onChange={e => updateListField('must_have_screens', i, e.target.value)} style={{ flex: 1 }} required />
              <button type="button" onClick={() => removeListItem('must_have_screens', i)}>−</button>
            </div>
          ))}
          <button type="button" onClick={() => addListItem('must_have_screens')}>+ screen</button>

          <label>Core data entities</label>
          {form.core_data_entities.map((s, i) => (
            <div key={i} style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
              <input value={s} onChange={e => updateListField('core_data_entities', i, e.target.value)} style={{ flex: 1 }} required />
              <button type="button" onClick={() => removeListItem('core_data_entities', i)}>−</button>
            </div>
          ))}
          <button type="button" onClick={() => addListItem('core_data_entities')}>+ entity</button>

          <div style={{ marginTop: 12 }}>
            <label><input type="checkbox" checked={form.works_offline} onChange={e => setForm({ ...form, works_offline: e.target.checked })} /> Works offline</label>
            <label style={{ marginLeft: 16 }}><input type="checkbox" checked={form.needs_notifications} onChange={e => setForm({ ...form, needs_notifications: e.target.checked })} /> Needs notifications</label>
            <label style={{ marginLeft: 16 }}><input type="checkbox" checked={form.include_payments_placeholder ?? false} onChange={e => setForm({ ...form, include_payments_placeholder: e.target.checked })} /> Include payments placeholder</label>
            <label style={{ marginLeft: 16 }}><input type="checkbox" checked={form.auth_required ?? true} onChange={e => setForm({ ...form, auth_required: e.target.checked })} /> Require auth</label>
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
