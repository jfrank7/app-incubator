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
  done?: boolean
  final_status?: string
  ts: string
}
