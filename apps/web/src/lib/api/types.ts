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
