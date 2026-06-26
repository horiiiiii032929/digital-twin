import { useCallback, useEffect, useState } from "react"

import {
  createOnboardingSession,
  type FieldStatus,
  type OnboardingSession,
  submitOnboardingMessage,
  updatePolicyField,
} from "@/lib/api"

type OnboardingState = {
  session: OnboardingSession | null
  error: string | null
  isStarting: boolean
  isSubmitting: boolean
  updatingFieldId: string | null
  restart: () => Promise<void>
  sendMessage: (content: string) => Promise<void>
  editPolicyField: (
    fieldId: string,
    value: string | string[],
    status: FieldStatus,
  ) => Promise<void>
}

export function useOnboardingSession(): OnboardingState {
  const [session, setSession] = useState<OnboardingSession | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [updatingFieldId, setUpdatingFieldId] = useState<string | null>(null)

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
    async (fieldId: string, value: string | string[], status: FieldStatus) => {
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

  return {
    session,
    error,
    isStarting,
    isSubmitting,
    updatingFieldId,
    restart: startSession,
    sendMessage,
    editPolicyField,
  }
}

function errorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message
  }

  return "Unexpected onboarding error."
}
