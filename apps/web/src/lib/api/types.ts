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
  owner_account_id?: string | null
  course_id?: string | null
  revision: number
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

export type StudentCourse = {
  course_id: string
  title: string
  release_id: string
  profile_id: string
  profile_version: string
}

export type StudentConversation = {
  id: string
  student_id: string
  course_id: string
  release_id: string
  created_at: string
  updated_at: string
}

export type StudentChatMessage = {
  id: string
  conversation_id: string
  role: "student" | "tutor"
  content: string
  action: string
  client_request_id?: string | null
  response_to_message_id?: string | null
  created_at: string
}

export type StudentCitation = {
  id: string
  message_id: string
  course_id: string
  release_id: string
  source_artifact_id: string
  source_document_id: string
  source_version: number
  title: string
  locator: string
  source_checksum?: string | null
  page?: number | null
  region_id?: string | null
  region_kind?: string | null
  bounding_box?: [number, number, number, number] | null
  crop_ref?: string | null
}

export type StudentConversationView = {
  conversation: StudentConversation
  messages: StudentChatMessage[]
}

export type StudentTutorTurn = {
  student_message: StudentChatMessage
  tutor_message: StudentChatMessage
  citations: StudentCitation[]
  duplicate: boolean
}

export type OutreachChannel = "in-app" | "discord"

export type StudentOutreachPreference = {
  student_id: string
  course_id: string
  channel: OutreachChannel
  enabled: boolean
  timezone: string
  quiet_hours_start: string
  quiet_hours_end: string
  max_messages_per_7_days: number
  snoozed_until?: string | null
  destination_ref?: string | null
  private_destination: boolean
  updated_at: string
}

export type StudentProactiveMessage = {
  id: string
  trigger_id: string
  student_id: string
  course_id: string
  release_id: string
  channel: OutreachChannel
  content: string
  status: "queued" | "delivered" | "read" | "dismissed" | "cancelled" | "failed"
  created_at: string
  read_at?: string | null
  dismissed_at?: string | null
}

export type StudentProactiveMessageView = {
  message: StudentProactiveMessage
  citations: StudentCitation[]
}

export type AccountRole = "admin" | "professor" | "student"

export type IdentityProfile = {
  account_id: string
  email: string
  display_name: string
  role: AccountRole
}

export type ProfessorReleaseStatus = "draft" | "published" | "withdrawn"
export type ReleaseEvaluationStatus = "pending" | "passed" | "failed"

export type ProfessorReleaseSummary = {
  id: string
  course_id: string
  status: ProfessorReleaseStatus
  evaluation_status: ReleaseEvaluationStatus
  policy_version: number
  chunk_count: number
  created_at: string
}

export type ProfessorCourse = {
  course_id: string
  title: string
  student_account_ids: string[]
  releases: ProfessorReleaseSummary[]
}

export type CourseMembership = {
  account_id: string
  course_id: string
  role: "professor" | "student"
  active: boolean
}

export type IngestionJobStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"

export type ProfessorIngestionResult = {
  source_artifact_id: string
  source_version: number
  source_checksum: string
  document_id: string
  chunk_count: number
  region_count: number
  region_kind_counts: Record<string, number>
  processing_warnings: string[]
  chunks: Record<string, unknown>[]
}

export type ProfessorIngestionJob = {
  id: string
  course_id: string
  artifact_id: string
  title: string
  version: number
  status: IngestionJobStatus
  attempts: number
  max_attempts: number
  error_code?: string | null
  error_message?: string | null
  result?: ProfessorIngestionResult | null
  created_at: string
  updated_at: string
}

export type ProfessorRelease = ProfessorReleaseSummary & {
  profile_id: string
  profile_version: string
  policy: TutorPolicy
  chunks: Record<string, unknown>[]
  teaching_profile_id?: string | null
  teaching_profile_sha256?: string | null
}

export type TeachingProfileStatus =
  | "draft"
  | "approved"
  | "superseded"
  | "withdrawn"

export type ProfessorTeachingProfile = {
  schema_version: "1.0.0"
  profile_id: string
  course_id: string
  version: number
  status: TeachingProfileStatus
  tone: string
  depth: "concise" | "balanced" | "detailed"
  explanation_structure: string[]
  example_preferences: string[]
  misconception_handling: string
  integrity_limits: string
  help_ladder: string[]
  outreach_policy: string
  content_sha256: string
  preview_sha256?: string | null
  created_at: string
  approved_at?: string | null
  withdrawn_at?: string | null
}

export type ProfessorTeachingProfilePreview = {
  schema_version: "1.0.0"
  profile_id: string
  profile_content_sha256: string
  cases: Array<{
    case_id: string
    student_situation: string
    expected_behavior: string
  }>
  preview_sha256: string
}

export type ProfessorLearningGapAggregate = {
  aggregate_id: string
  topic_key: string
  signal_kind: string
  distinct_learners: number
  signal_count: number
  limitations: string[]
}

export type ProfessorLearningGapResult = {
  aggregation: {
    minimum_distinct_learners: number
    visible_aggregates: ProfessorLearningGapAggregate[]
    suppressed_group_count: number
    computed_at: string
  }
  proposals: Array<{
    proposal_id: string
    topic_key: string
    signal_kind: string
    observed_pattern: string
    suggested_follow_up: string
    distinct_learners: number
    signal_count: number
  }>
}

export type ProfessorProactiveTrigger = {
  id: string
  student_id: string
  course_id: string
  release_id: string
  channel: "in-app" | "discord"
  kind:
    | "scheduled-retrieval-practice"
    | "student-follow-up"
    | "misconception-follow-up"
    | "evidence-recovery"
  scheduled_for: string
  expires_at: string
  topic: string
  prompt: string
  source_chunk_id: string
  status: "pending" | "materialized" | "suppressed" | "cancelled"
  suppression_reason?: string | null
  created_at: string
  updated_at: string
}

export type AutonomousActionKind =
  | "ask-diagnostic-question"
  | "provide-hint-or-example"
  | "recommend-approved-source"
  | "issue-retrieval-practice"
  | "schedule-follow-up"
  | "send-in-app-check-in"
  | "summarize-progress"
  | "create-professor-insight-draft"
  | "no-action"

export type PedagogicalPolicyV2 = {
  schema_version: "2.1.0"
  course_id: string
  version: number
  approved_by: string
  approved_profile_id: string
  approved_profile_sha256: string
  approved_course_objectives: string[]
  autonomy_enabled: boolean
  paused: boolean
  kill_switch: boolean
  allowed_actions: AutonomousActionKind[]
  max_active_goals: number
  max_messages_per_7_days: number
  same_concept_cooldown_hours: number
  planning_calls_per_event: number
  generation_calls_per_event: number
  repair_calls_per_event: number
  provider_retries: number
  recursion_limit: number
  integrity_ceiling: string
  updated_at: string
}

export type AutonomousRecipientEligibilityV1 = {
  schema_version: "1.0.0"
  student_account_id: string
  account_active: boolean
  membership_active: boolean
  consent_active: boolean
  goal_eligible: boolean
  outreach_eligible: boolean
  ineligibility_reasons: string[]
}

export type AutonomousGoalV1 = {
  schema_version: "1.0.0"
  goal_id: string
  student_id: string
  course_id: string
  release_id: string
  policy_version: number
  profile_id: string
  profile_sha256: string
  graph_version: string
  planner_model: string
  generator_model: string
  approved_course_objective: string
  learner_subgoal: string
  success_condition: string
  priority: number
  attempt_limit: number
  attempt_count: number
  status: "active" | "completed" | "expired" | "cancelled"
  expires_at: string
  created_at: string
  updated_at: string
}

export type AutonomousActionV1 = {
  schema_version: "1.0.0"
  action_id: string
  plan_id: string
  opportunity_id: string
  goal_id?: string | null
  student_id: string
  course_id: string
  release_id: string
  policy_version: number
  profile_sha256: string
  graph_version: string
  generator_model: string
  kind: AutonomousActionKind
  status: "proposed" | "delivered" | "suppressed" | "failed" | "cancelled"
  proactive_trigger_id?: string | null
  structured_reason: string
  validation_results: Record<string, boolean>
  created_at: string
  updated_at: string
}

export type ReleasePreflightCheck = {
  id: string
  label: string
  passed: boolean
  detail: string
}

export type ReleasePreflightResult = {
  release_id: string
  passed: boolean
  checks: ReleasePreflightCheck[]
  evaluated_at: string
}
