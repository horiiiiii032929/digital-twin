import { useCallback, useEffect, useReducer } from "react"

import {
  initialSessionState,
  errorMessage,
  sessionReducer,
  type SessionOperation,
  type SessionState,
} from "@/hooks/onboarding/session-state"
import {
  addCustomPreviewCase,
  addSourceInventoryItem,
  confirmRevisionProposal,
  createOnboardingSession,
  createSupervisorDemoSession,
  discardRevisionProposal,
  setPreviewDecision,
  submitOnboardingMessage,
  updateApprovalChecklistItem,
  updatePolicyField,
  updateSourceInventoryItem,
} from "@/lib/api/onboarding"
import type {
  FieldStatus,
  OnboardingSession,
  PreviewDecisionValue,
  PromptTag,
  SourceLabel,
  SourceInventoryItem,
  SourcePermissionStatus,
} from "@/lib/api/types"

export type OnboardingController = SessionState & {
  restart: () => Promise<void>
  sendMessage: (content: string) => Promise<boolean>
  addSource: (item: {
    name: string
    mime_type: string
    size_bytes: number
    permission_status?: SourcePermissionStatus
    source_label?: SourceLabel
    excluded?: boolean
    sensitive?: boolean | null
    notes?: string
  }) => Promise<boolean>
  editSource: (
    sourceId: string,
    updates: Partial<
      Pick<
        SourceInventoryItem,
        | "permission_status"
        | "source_label"
        | "excluded"
        | "sensitive"
        | "notes"
      >
    >,
  ) => Promise<void>
  editPolicyField: (
    fieldId: string,
    value: string | string[] | Record<string, unknown>,
    status: FieldStatus,
  ) => Promise<void>
  updateApprovalItem: (itemId: string, checked: boolean) => Promise<void>
  decidePreview: (
    previewCaseId: string,
    decision: PreviewDecisionValue,
    reason?: string,
  ) => Promise<void>
  addCustomPreview: (prompt: string, tag: PromptTag) => Promise<boolean>
  confirmRevision: () => Promise<void>
  discardRevision: () => Promise<void>
}

export function useOnboardingSession({
  supervisorDemo = false,
}: {
  supervisorDemo?: boolean
} = {}): OnboardingController {
  const [state, dispatch] = useReducer(sessionReducer, initialSessionState)

  const startSession = useCallback(async () => {
    dispatch({ type: "start/pending" })

    try {
      dispatch({
        type: "start/succeeded",
        session: await (supervisorDemo
          ? createSupervisorDemoSession()
          : createOnboardingSession()),
      })
    } catch (caught) {
      dispatch({ type: "start/failed", error: errorMessage(caught) })
    }
  }, [supervisorDemo])

  useEffect(() => {
    void startSession()
  }, [startSession])

  const runOperation = useCallback(
    async (
      operation: SessionOperation,
      command: () => Promise<OnboardingSession>,
      id?: string,
    ) => {
      dispatch({ type: "operation/pending", operation, id })

      try {
        const session = await command()
        dispatch({
          type: "operation/succeeded",
          operation,
          session,
        })
        return true
      } catch (caught) {
        dispatch({
          type: "operation/failed",
          operation,
          error: errorMessage(caught),
        })
        return false
      } finally {
        dispatch({ type: "operation/finished", operation })
      }
    },
    [],
  )

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim()
      if (!trimmed || !state.session || state.isSubmitting) {
        return false
      }

      return runOperation("message", () =>
        submitOnboardingMessage(state.session!.session_id, trimmed),
      )
    },
    [runOperation, state.isSubmitting, state.session],
  )

  const editPolicyField = useCallback(
    async (
      fieldId: string,
      value: string | string[] | Record<string, unknown>,
      status: FieldStatus,
    ) => {
      if (!state.session || state.updatingFieldId) {
        return
      }

      await runOperation(
        "policy-update",
        () => updatePolicyField(state.session!.session_id, fieldId, value, status),
        fieldId,
      )
    },
    [runOperation, state.session, state.updatingFieldId],
  )

  const addSource = useCallback(
    async (item: {
      name: string
      mime_type: string
      size_bytes: number
      permission_status?: SourcePermissionStatus
      source_label?: SourceLabel
      excluded?: boolean
      sensitive?: boolean | null
      notes?: string
    }) => {
      if (!state.session || state.isAddingSource) {
        return false
      }

      return runOperation("source-add", () =>
        addSourceInventoryItem(state.session!.session_id, item),
      )
    },
    [runOperation, state.isAddingSource, state.session],
  )

  const editSource = useCallback(
    async (
      sourceId: string,
      updates: Partial<
        Pick<
          SourceInventoryItem,
          | "permission_status"
          | "source_label"
          | "excluded"
          | "sensitive"
          | "notes"
        >
      >,
    ) => {
      if (!state.session || state.updatingSourceId) {
        return
      }

      await runOperation(
        "source-update",
        () =>
          updateSourceInventoryItem(
            state.session!.session_id,
            sourceId,
            updates,
          ),
        sourceId,
      )
    },
    [runOperation, state.session, state.updatingSourceId],
  )

  const updateApprovalItem = useCallback(
    async (itemId: string, checked: boolean) => {
      if (!state.session || state.updatingApprovalItemId) {
        return
      }

      await runOperation(
        "approval-update",
        () =>
          updateApprovalChecklistItem(state.session!.session_id, itemId, checked),
        itemId,
      )
    },
    [runOperation, state.session, state.updatingApprovalItemId],
  )

  const decidePreview = useCallback(
    async (
      previewCaseId: string,
      decision: PreviewDecisionValue,
      reason?: string,
    ) => {
      if (!state.session || state.updatingPreviewId) {
        return
      }

      await runOperation(
        "preview-update",
        () =>
          setPreviewDecision(
            state.session!.session_id,
            previewCaseId,
            decision,
            reason,
          ),
        previewCaseId,
      )
    },
    [runOperation, state.session, state.updatingPreviewId],
  )

  const addCustomPreview = useCallback(
    async (prompt: string, tag: PromptTag) => {
      const trimmed = prompt.trim()
      if (!state.session || state.isAddingCustomPreview || !trimmed) {
        return false
      }

      return runOperation("preview-add", () =>
        addCustomPreviewCase(state.session!.session_id, {
          prompt: trimmed,
          tag,
        }),
      )
    },
    [runOperation, state.isAddingCustomPreview, state.session],
  )

  const confirmRevision = useCallback(async () => {
    if (!state.session || state.isResolvingRevision) {
      return
    }

    await runOperation("revision-resolve", () =>
      confirmRevisionProposal(state.session!.session_id),
    )
  }, [runOperation, state.isResolvingRevision, state.session])

  const discardRevision = useCallback(async () => {
    if (!state.session || state.isResolvingRevision) {
      return
    }

    await runOperation("revision-resolve", () =>
      discardRevisionProposal(state.session!.session_id),
    )
  }, [runOperation, state.isResolvingRevision, state.session])

  return {
    ...state,
    restart: startSession,
    sendMessage,
    addSource,
    editSource,
    editPolicyField,
    updateApprovalItem,
    decidePreview,
    addCustomPreview,
    confirmRevision,
    discardRevision,
  }
}
