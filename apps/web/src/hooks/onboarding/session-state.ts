import type { OnboardingSession } from "@/lib/api/types"

export type SessionState = {
  session: OnboardingSession | null
  error: string | null
  isStarting: boolean
  isSubmitting: boolean
  isAddingSource: boolean
  updatingSourceId: string | null
  updatingFieldId: string | null
  updatingApprovalItemId: string | null
  updatingPreviewId: string | null
  isAddingCustomPreview: boolean
  isResolvingRevision: boolean
}

export const initialSessionState: SessionState = {
  session: null,
  error: null,
  isStarting: true,
  isSubmitting: false,
  isAddingSource: false,
  updatingSourceId: null,
  updatingFieldId: null,
  updatingApprovalItemId: null,
  updatingPreviewId: null,
  isAddingCustomPreview: false,
  isResolvingRevision: false,
}

export type SessionOperation =
  | "message"
  | "source-add"
  | "source-update"
  | "policy-update"
  | "approval-update"
  | "preview-update"
  | "preview-add"
  | "revision-resolve"

type SessionAction =
  | { type: "start/pending" }
  | { type: "start/succeeded"; session: OnboardingSession }
  | { type: "start/failed"; error: string }
  | { type: "operation/pending"; operation: SessionOperation; id?: string }
  | {
      type: "operation/succeeded"
      operation: SessionOperation
      session: OnboardingSession
    }
  | { type: "operation/failed"; operation: SessionOperation; error: string }
  | { type: "operation/finished"; operation: SessionOperation }

export function sessionReducer(
  state: SessionState,
  action: SessionAction,
): SessionState {
  switch (action.type) {
    case "start/pending":
      return { ...state, isStarting: true, error: null }
    case "start/succeeded":
      return {
        ...state,
        session: action.session,
        isStarting: false,
        error: null,
      }
    case "start/failed":
      return { ...state, isStarting: false, error: action.error }
    case "operation/pending":
      return {
        ...state,
        ...operationPatch(action.operation, true, action.id),
        error: null,
      }
    case "operation/succeeded":
      return { ...state, session: action.session }
    case "operation/failed":
      return { ...state, error: action.error }
    case "operation/finished":
      return { ...state, ...operationPatch(action.operation, false) }
  }
}

export function errorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message
  }

  return "Unexpected onboarding error."
}

function operationPatch(
  operation: SessionOperation,
  active: boolean,
  id?: string,
): Partial<SessionState> {
  switch (operation) {
    case "message":
      return { isSubmitting: active }
    case "source-add":
      return { isAddingSource: active }
    case "source-update":
      return { updatingSourceId: active ? (id ?? null) : null }
    case "policy-update":
      return { updatingFieldId: active ? (id ?? null) : null }
    case "approval-update":
      return { updatingApprovalItemId: active ? (id ?? null) : null }
    case "preview-update":
      return { updatingPreviewId: active ? (id ?? null) : null }
    case "preview-add":
      return { isAddingCustomPreview: active }
    case "revision-resolve":
      return { isResolvingRevision: active }
  }
}
