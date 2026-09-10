import { useCallback, useEffect, useRef, useState } from "react"

import {
  ApiError,
  changePassword,
  getCurrentSession,
  login,
  logout,
} from "@/lib/api"
import type { IdentityProfile } from "@/lib/api/types"
import { advanceSessionRevision, onSessionExpired, sessionRevision } from "@/lib/api/session-state"

export type AuthSessionController = {
  profile: IdentityProfile | null
  loading: boolean
  submitting: boolean
  error: string | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  updatePassword: (currentPassword: string, newPassword: string) => Promise<void>
}

export function useAuthSession(): AuthSessionController {
  const [profile, setProfile] = useState<IdentityProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const inFlight = useRef(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const revision = sessionRevision()
    const unsubscribe = onSessionExpired(() => {
      setProfile(null)
      setError("Your session has expired. Sign in again to continue.")
    })
    getCurrentSession()
      .then((current) => {
        if (active && revision === sessionRevision()) setProfile(current)
      })
      .catch((reason: unknown) => {
        if (active && (!(reason instanceof ApiError) || reason.status !== 401)) {
          setError(errorMessage(reason, "Could not check your session."))
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
      unsubscribe()
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    if (inFlight.current) return
    inFlight.current = true
    advanceSessionRevision()
    setSubmitting(true)
    setError(null)
    try {
      setProfile(await login(email, password))
    } catch (reason) {
      setError(errorMessage(reason, "Sign in failed."))
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }, [])

  const signOut = useCallback(async () => {
    if (inFlight.current) return
    inFlight.current = true
    setSubmitting(true)
    setError(null)
    try {
      await logout()
      advanceSessionRevision()
      setProfile(null)
    } catch (reason) {
      setError(errorMessage(reason, "Could not sign out."))
      throw reason
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }, [])

  const updatePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      if (inFlight.current) return
      inFlight.current = true
      setSubmitting(true)
      setError(null)
      try {
        await changePassword(currentPassword, newPassword)
        advanceSessionRevision()
        setProfile(null)
      } catch (reason) {
        const message = errorMessage(reason, "Could not change the password.")
        setError(message)
        throw reason
      } finally {
        inFlight.current = false
        setSubmitting(false)
      }
    },
    [],
  )

  return {
    profile,
    loading,
    submitting,
    error,
    signIn,
    signOut,
    updatePassword,
  }
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback
}
