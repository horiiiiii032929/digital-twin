export const PROFESSOR_ONBOARDING_SESSION_KEY =
  "course-digital-twin.professor-onboarding.v1"

export function professorOnboardingSessionKey(accountId: string): string {
  return `${PROFESSOR_ONBOARDING_SESSION_KEY}.${encodeURIComponent(accountId.trim())}`
}

export function readProfessorOnboardingSessionId(
  storage: Pick<Storage, "getItem">,
  accountId: string,
): string | null {
  try {
    const value = storage.getItem(professorOnboardingSessionKey(accountId))?.trim()
    return value && value.length <= 128 ? value : null
  } catch {
    return null
  }
}

export function writeProfessorOnboardingSessionId(
  storage: Pick<Storage, "setItem">,
  accountId: string,
  sessionId: string,
): void {
  storage.setItem(professorOnboardingSessionKey(accountId), sessionId)
}

export function clearProfessorOnboardingSessionId(
  storage: Pick<Storage, "removeItem">,
  accountId: string,
): void {
  storage.removeItem(professorOnboardingSessionKey(accountId))
}
