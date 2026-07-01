import { useCallback, useEffect, useState } from "react"

import {
  addCustomPreviewCase,
  addSourceInventoryItem,
  confirmRevisionProposal,
  createOnboardingSession,
  discardRevisionProposal,
  type FieldStatus,
  type OnboardingSession,
  type PreviewDecisionValue,
  type PromptTag,
  type SourceInventoryItem,
  setPreviewDecision,
  submitOnboardingMessage,
  updateApprovalChecklistItem,
  updatePolicyField,
  updateSourceInventoryItem,
} from "@/lib/api"

type OnboardingState = {
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
  restart: () => Promise<void>
  sendMessage: (content: string) => Promise<void>
  addSource: (item: {
    name: string
    mime_type: string
    size_bytes: number
    notes?: string
  }) => Promise<void>
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
  addCustomPreview: (prompt: string, tag: PromptTag) => Promise<void>
  confirmRevision: () => Promise<void>
  discardRevision: () => Promise<void>
}

export function useOnboardingSession(): OnboardingState {
  const [session, setSession] = useState<OnboardingSession | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isAddingSource, setIsAddingSource] = useState(false)
  const [updatingSourceId, setUpdatingSourceId] = useState<string | null>(null)
  const [updatingFieldId, setUpdatingFieldId] = useState<string | null>(null)
  const [updatingApprovalItemId, setUpdatingApprovalItemId] = useState<
    string | null
  >(null)
  const [updatingPreviewId, setUpdatingPreviewId] = useState<string | null>(null)
  const [isAddingCustomPreview, setIsAddingCustomPreview] = useState(false)
  const [isResolvingRevision, setIsResolvingRevision] = useState(false)

  const startSession = useCallback(async () => {
    setIsStarting(true)
    setError(null)

    try {
      setSession(await createOnboardingSession())
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setIsStarting(false)
    }
  }, [])

  useEffect(() => {
    void startSession()
  }, [startSession])

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim()

      if (!trimmed || !session || isSubmitting) {
        return
      }

      setIsSubmitting(true)
      setError(null)

      try {
        setSession(await submitOnboardingMessage(session.session_id, trimmed))
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setIsSubmitting(false)
      }
    },
    [isSubmitting, session],
  )

  const editPolicyField = useCallback(
    async (
      fieldId: string,
      value: string | string[] | Record<string, unknown>,
      status: FieldStatus,
    ) => {
      if (!session || updatingFieldId) {
        return
      }

      setUpdatingFieldId(fieldId)
      setError(null)

      try {
        setSession(
          await updatePolicyField(session.session_id, fieldId, value, status),
        )
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setUpdatingFieldId(null)
      }
    },
    [session, updatingFieldId],
  )

  const addSource = useCallback(
    async (item: {
      name: string
      mime_type: string
      size_bytes: number
      notes?: string
    }) => {
      if (!session || isAddingSource) {
        return
      }

      setIsAddingSource(true)
      setError(null)

      try {
        setSession(await addSourceInventoryItem(session.session_id, item))
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setIsAddingSource(false)
      }
    },
    [isAddingSource, session],
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
      if (!session || updatingSourceId) {
        return
      }

      setUpdatingSourceId(sourceId)
      setError(null)

      try {
        setSession(
          await updateSourceInventoryItem(session.session_id, sourceId, updates),
        )
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setUpdatingSourceId(null)
      }
    },
    [session, updatingSourceId],
  )

  const updateApprovalItem = useCallback(
    async (itemId: string, checked: boolean) => {
      if (!session || updatingApprovalItemId) {
        return
      }

      setUpdatingApprovalItemId(itemId)
      setError(null)

      try {
        setSession(
          await updateApprovalChecklistItem(session.session_id, itemId, checked),
        )
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setUpdatingApprovalItemId(null)
      }
    },
    [session, updatingApprovalItemId],
  )

  const decidePreview = useCallback(
    async (
      previewCaseId: string,
      decision: PreviewDecisionValue,
      reason?: string,
    ) => {
      if (!session || updatingPreviewId) {
        return
      }

      setUpdatingPreviewId(previewCaseId)
      setError(null)

      try {
        setSession(
          await setPreviewDecision(
            session.session_id,
            previewCaseId,
            decision,
            reason,
          ),
        )
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setUpdatingPreviewId(null)
      }
    },
    [session, updatingPreviewId],
  )

  const addCustomPreview = useCallback(
    async (prompt: string, tag: PromptTag) => {
      const trimmed = prompt.trim()
      if (!session || isAddingCustomPreview || !trimmed) {
        return
      }

      setIsAddingCustomPreview(true)
      setError(null)

      try {
        setSession(
          await addCustomPreviewCase(session.session_id, {
            prompt: trimmed,
            tag,
          }),
        )
      } catch (caught) {
        setError(errorMessage(caught))
      } finally {
        setIsAddingCustomPreview(false)
      }
    },
    [isAddingCustomPreview, session],
  )

  const confirmRevision = useCallback(async () => {
    if (!session || isResolvingRevision) {
      return
    }

    setIsResolvingRevision(true)
    setError(null)

    try {
      setSession(await confirmRevisionProposal(session.session_id))
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setIsResolvingRevision(false)
    }
  }, [isResolvingRevision, session])

  const discardRevision = useCallback(async () => {
    if (!session || isResolvingRevision) {
      return
    }

    setIsResolvingRevision(true)
    setError(null)

    try {
      setSession(await discardRevisionProposal(session.session_id))
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setIsResolvingRevision(false)
    }
  }, [isResolvingRevision, session])

  return {
    session,
    error,
    isStarting,
    isSubmitting,
    isAddingSource,
    updatingSourceId,
    updatingFieldId,
    updatingApprovalItemId,
    updatingPreviewId,
    isAddingCustomPreview,
    isResolvingRevision,
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

function errorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message
  }

  return "Unexpected onboarding error."
}
