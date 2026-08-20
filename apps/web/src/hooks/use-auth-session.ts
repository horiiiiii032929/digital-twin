import { useCallback, useEffect, useState } from "react"

import {
  ApiError,
  changePassword,
  getCurrentSession,
  login,
  logout,
} from "@/lib/api"
import type { IdentityProfile } from "@/lib/api/types"

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
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getCurrentSession()
      .then((current) => {
        if (active) setProfile(current)
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
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    setSubmitting(true)
    setError(null)
    try {
      setProfile(await login(email, password))
    } catch (reason) {
      setError(errorMessage(reason, "Sign in failed."))
    } finally {
      setSubmitting(false)
    }
  }, [])

  const signOut = useCallback(async () => {
    setSubmitting(true)
    setError(null)
    try {
      await logout()
      setProfile(null)
    } catch (reason) {
      setError(errorMessage(reason, "Could not sign out."))
      throw reason
    } finally {
      setSubmitting(false)
    }
  }, [])

  const updatePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      setSubmitting(true)
      setError(null)
      try {
        await changePassword(currentPassword, newPassword)
        setProfile(null)
      } catch (reason) {
        const message = errorMessage(reason, "Could not change the password.")
        setError(message)
        throw reason
      } finally {
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
