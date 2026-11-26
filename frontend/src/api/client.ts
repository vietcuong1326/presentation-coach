const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers || {})
  headers.set('Content-Type', 'application/json')

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorBody: any
    try {
      errorBody = await response.json()
    } catch {
      errorBody = { error: { code: 'HTTP_ERROR', message: `HTTP ${response.status}` } }
    }
    throw new Error(errorBody?.error?.message || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

export interface MemberInput {
  name: string
  start_time_seconds?: number | null
  end_time_seconds?: number | null
  display_order?: number
}

export interface ProjectInput {
  title: string
  topic?: string
  objectives?: string
  target_audience?: string
  presentation_type: 'INDIVIDUAL' | 'GROUP'
  expected_duration_seconds?: number | null
  members?: MemberInput[]
}

export interface ProjectData extends ProjectInput {
  id: string
  user_id: string
  members: (MemberInput & { id: string; project_id: string })[]
  warnings: string[]
  created_at: string
  updated_at: string
}

export interface SlideContent {
  page_number: number
  text: string
}

export interface UploadedFileResponse {
  id: string
  project_id: string
  user_id: string
  file_role: 'SLIDES' | 'AUDIO' | 'VIDEO' | 'REPORT'
  original_filename: string
  mime_type: string
  size_bytes: number
  processing_status: string
  storage_path: string
  created_at: string
  extracted_slides?: SlideContent[]
}

export interface EvaluationStatusResponse {
  id: string
  project_id: string
  user_id: string
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'PARTIAL' | 'FAILED'
  error_code?: string | null
  error_message?: string | null
  rubric_version: string
  created_at: string
  completed_at?: string | null
}

export interface EvaluationListItem extends EvaluationStatusResponse {
  project_title?: string
  presentation_type?: string
}

export interface StrengthItem {
  title: string
  description: string
  evidence_ids: string[]
  related_criteria: string[]
}

export interface ImprovementItem {
  id: string
  title: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  scope: 'GROUP' | 'INDIVIDUAL'
  member_id?: string | null
  observation: string
  impact: string
  recommendation: string
  example?: string | null
  evidence_ids: string[]
  related_criteria: string[]
}

export interface CriterionResult {
  criterion_id: string
  scope: 'GROUP' | 'INDIVIDUAL'
  member_id?: string | null
  status: 'EVALUATED' | 'NOT_EVALUATED' | 'PENDING'
  score: number | null
  level: 'SUPERIOR' | 'EXCELLENT' | 'VERY_GOOD' | 'SATISFACTORY' | 'UNACCEPTABLE' | null
  reason: string
  evidence_ids: string[]
  confidence: number | null
}

export interface PriorityAction {
  title: string
  steps: string[]
  related_feedback_ids: string[]
}

export interface AnalysisReportPayload {
  evaluation_summary: {
    headline: string
    overall_feedback: string
    evidence_coverage: {
      evaluated_criteria: number
      not_evaluated_criteria: number
    }
  }
  strengths: StrengthItem[]
  improvements: ImprovementItem[]
  criterion_results: CriterionResult[]
  priority_actions: PriorityAction[]
}

export interface AnalysisReportData {
  id: string
  evaluation_id: string
  version: number
  report_json: AnalysisReportPayload
  evaluated_count: number
  not_evaluated_count: number
  created_at: string
}

export interface ChatMessage {
  id: string
  session_id?: string
  role: 'USER' | 'ASSISTANT'
  content: string
  created_at: string
}

export interface ChatSession {
  id: string
  evaluation_id: string
  user_id: string
  title?: string | null
  created_at: string
  messages: ChatMessage[]
}

export interface ChatResponse {
  session_id: string
  message: ChatMessage
}

export interface ChatHistoryResponse {
  evaluation_id: string
  sessions: ChatSession[]
}

export const api = {
  getHealth: () => apiFetch<{ status: string }>('/health'),
  getMe: (token: string) => apiFetch<{ user: { id: string; email: string; role: string } }>('/api/auth/me', {}, token),

  // Projects API
  listProjects: (token: string) => apiFetch<ProjectData[]>('/api/projects', {}, token),
  createProject: (token: string, data: ProjectInput) => apiFetch<ProjectData>('/api/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  }, token),
  getProject: (token: string, id: string) => apiFetch<ProjectData>(`/api/projects/${id}`, {}, token),
  deleteProject: (token: string, id: string) => apiFetch<{ status: string }>(`/api/projects/${id}`, {
    method: 'DELETE',
  }, token),

  // File Upload API
  uploadProjectFile: async (
    token: string,
    projectId: string,
    file: File,
    fileRole: string
  ): Promise<UploadedFileResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_role', fileRole)

    const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/files`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    })

    if (!response.ok) {
      let errorBody: any
      try {
        errorBody = await response.json()
      } catch {
        errorBody = { error: { message: `HTTP ${response.status}` } }
      }
      throw new Error(errorBody?.error?.message || `Upload failed with status ${response.status}`)
    }
    return response.json() as Promise<UploadedFileResponse>
  },

  // Evaluations API
  createEvaluation: (token: string, projectId: string) => apiFetch<{ id: string; status: string }>(
    `/api/projects/${projectId}/evaluations`,
    { method: 'POST' },
    token
  ),
  listEvaluations: (token: string, limit: number = 30) =>
    apiFetch<EvaluationListItem[]>(`/api/evaluations?limit=${limit}`, {}, token),
  listProjectEvaluations: (token: string, projectId: string) =>
    apiFetch<EvaluationListItem[]>(`/api/projects/${projectId}/evaluations`, {}, token),
  getEvaluationStatus: (token: string, evalId: string) => apiFetch<EvaluationStatusResponse>(
    `/api/evaluations/${evalId}`,
    {},
    token
  ),
  getEvaluationReport: (token: string, evalId: string) => apiFetch<any>(
    `/api/evaluations/${evalId}/report`,
    {},
    token
  ),
  getEvaluationTranscript: (token: string, evalId: string) => apiFetch<any>(
    `/api/evaluations/${evalId}/transcript`,
    {},
    token
  ),
  deleteEvaluation: (token: string, evalId: string) => apiFetch<{ status: string }>(
    `/api/evaluations/${evalId}`,
    { method: 'DELETE' },
    token
  ),

  // Chat API
  sendChatMessage: (token: string, evalId: string, message: string, sessionId?: string) =>
    apiFetch<ChatResponse>(
      `/api/evaluations/${evalId}/chat`,
      {
        method: 'POST',
        body: JSON.stringify({ message, session_id: sessionId || null }),
      },
      token
    ),
  getChatHistory: (token: string, evalId: string) =>
    apiFetch<ChatHistoryResponse>(
      `/api/evaluations/${evalId}/chat`,
      {},
      token
    ),
}
