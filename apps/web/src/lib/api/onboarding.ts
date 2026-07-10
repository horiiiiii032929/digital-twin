import { request } from "@/lib/api/client"
import type {
  FieldStatus,
  OnboardingSession,
  PreviewDecisionValue,
  PromptTag,
  SourceInventoryItem,
  SourceLabel,
  SourcePermissionStatus,
} from "@/lib/api/types"

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
