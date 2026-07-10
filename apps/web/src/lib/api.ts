export type ChatRole = "assistant" | "instructor" | "system"

export type FieldStatus = "resolved" | "needs_review" | "blocks_release"

export type ReleaseStatus = "draft" | "blocked" | "approved"

export type TraceStatus = "complete" | "warning" | "blocked"

export type SourcePermissionStatus = "pending" | "approved" | "excluded"

export type SourceLabel =
  | "course-approved"
  | "professor-approved-external"
  | "system-suggested-trusted"
  | "unapproved-external"

export type PromptTag =
  | "source_grounding"
  | "academic_integrity"
  | "misconception"
  | "teaching_behavior"
  | "tone"
  | "other"

export type PreviewDecisionValue = "pending" | "accepted" | "rejected"

export type ChatMessage = {
  role: ChatRole
  content: string
}

export type SourceInventoryItem = {
  id: string
  name: string
  mime_type: string
  size_bytes: number
  permission_status: SourcePermissionStatus
  source_label: SourceLabel
  excluded: boolean
  sensitive: boolean
  notes: string
}

export type PolicyField = {
  id: string
  label: string
  status: FieldStatus
  value: string | string[] | Record<string, unknown>
  safe_default?: string | null
  warning?: string | null
}

export type PreviewAuditEntry = {
  source_title: string
  url: string
  source_type: string
  source_label: SourceLabel
  supports: string
  conflict_status: string
  selection_reason: string
}

export type PreviewCase = {
  id: string
  tag: PromptTag
  prompt: string
  generic_response: string
  configured_response: string
  policy_signals: string[]
  source_audit: PreviewAuditEntry[]
  warnings: string[]
  decision: PreviewDecisionValue
  decision_reason?: string | null
  policy_version: number
  generated_at?: string | null
}

export type PreviewDecisionRecord = {
  preview_case_id: string
  decision: PreviewDecisionValue
  reason?: string | null
  policy_version: number
  timestamp: string
  revision_resolved: boolean
}

export type EvidenceSnapshot = {
  id: string
  preview_case_id: string
  prompt: string
  configured_response: string
  source_audit: PreviewAuditEntry[]
  source_labels: SourceLabel[]
  warnings: string[]
  decision: PreviewDecisionValue
  policy_version: number
  timestamp: string
}

export type RevisionProposal = {
  id: string
  preview_case_id?: string | null
  feedback: string
  affected_policy_fields: string[]
  proposed_value: string
  rationale: string
  status: "pending" | "confirmed" | "discarded"
  created_at: string
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
  source_inventory: SourceInventoryItem[]
  policy: TutorPolicy | null
  policy_version: number
  preview_cases: PreviewCase[]
  preview_decisions: Record<string, PreviewDecisionRecord>
  evidence_snapshots: EvidenceSnapshot[]
  revision_proposal: RevisionProposal | null
  approval_checklist: ApprovalItem[]
  release_blockers: Record<string, string[]>
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
  value: string | string[] | Record<string, unknown>,
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

export function addSourceInventoryItem(
  sessionId: string,
  item: {
    name: string
    mime_type: string
    size_bytes: number
    permission_status?: SourcePermissionStatus
    source_label?: SourceLabel
    excluded?: boolean
    sensitive?: boolean | null
    notes?: string
  },
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/source-inventory`,
    {
      method: "POST",
      body: JSON.stringify(item),
    },
  )
}

export function updateSourceInventoryItem(
  sessionId: string,
  sourceId: string,
  updates: Partial<
    Pick<
      SourceInventoryItem,
      | "name"
      | "mime_type"
      | "size_bytes"
      | "permission_status"
      | "source_label"
      | "excluded"
      | "sensitive"
      | "notes"
    >
  >,
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/source-inventory/${sourceId}`,
    {
      method: "PATCH",
      body: JSON.stringify(updates),
    },
  )
}

export function updateApprovalChecklistItem(
  sessionId: string,
  itemId: string,
  checked: boolean,
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/approval-checklist/${itemId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ checked }),
    },
  )
}

export function setPreviewDecision(
  sessionId: string,
  previewCaseId: string,
  decision: PreviewDecisionValue,
  reason?: string,
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/preview-cases/${previewCaseId}/decision`,
    {
      method: "PATCH",
      body: JSON.stringify({ decision, reason }),
    },
  )
}

export function addCustomPreviewCase(
  sessionId: string,
  preview: {
    prompt: string
    tag: PromptTag
  },
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/preview-cases`,
    {
      method: "POST",
      body: JSON.stringify(preview),
    },
  )
}

export function confirmRevisionProposal(
  sessionId: string,
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/revision-proposal/confirm`,
    {
      method: "POST",
    },
  )
}

export function discardRevisionProposal(
  sessionId: string,
): Promise<OnboardingSession> {
  return request<OnboardingSession>(
    `/api/onboarding/sessions/${sessionId}/revision-proposal/discard`,
    {
      method: "POST",
    },
  )
}
