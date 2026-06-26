export type ChatRole = "assistant" | "instructor" | "system"

export type FieldStatus = "resolved" | "needs_review" | "blocks_release"

export type ReleaseStatus = "draft" | "blocked" | "approved"

export type TraceStatus = "complete" | "warning" | "blocked"

export type ChatMessage = {
  role: ChatRole
  content: string
}

export type PolicyField = {
  id: string
  label: string
  status: FieldStatus
  value: string | string[]
  safe_default?: string | null
  warning?: string | null
}

export type PreviewCase = {
  id: string
  prompt: string
  generic_response: string
  configured_response: string
  policy_signals: string[]
}

export type ApprovalItem = {
  id: string
  label: string
  blocks_release: boolean
  checked: boolean
}

export type WorkflowTraceItem = {
  id: string
  title: string
  detail: string
  status: TraceStatus
}

export type TutorPolicy = {
  status: ReleaseStatus
  release_status: ReleaseStatus
  safety_compliance: PolicyField[]
  pedagogy: PolicyField[]
  professor_review: PolicyField[]
}

export type OnboardingSession = {
  session_id: string
  current_step: string
  answers: Record<string, string>
  messages: ChatMessage[]
  policy: TutorPolicy | null
  preview_cases: PreviewCase[]
  approval_checklist: ApprovalItem[]
  trace: WorkflowTraceItem[]
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000"

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status)
  }

  return response.json() as Promise<T>
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      detail?: string | { message?: string }
    }

    if (typeof payload.detail === "string") {
      return payload.detail
    }

    if (payload.detail?.message) {
      return payload.detail.message
    }
  } catch {
    return `Request failed with status ${response.status}`
  }

  return `Request failed with status ${response.status}`
}

export function createOnboardingSession(): Promise<OnboardingSession> {
  return request<OnboardingSession>("/api/onboarding/sessions", {
    method: "POST",
  })
}

export function submitOnboardingMessage(
  sessionId: string,
  content: string,
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
  )
}

export function updatePolicyField(
  sessionId: string,
  fieldId: string,
  value: string | string[],
  status: FieldStatus,
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/policy-fields/${fieldId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ value, status }),
    },
  )
}
