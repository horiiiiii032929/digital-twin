import { describe, expect, it } from "vitest"

import {
  PROFESSOR_ONBOARDING_SESSION_KEY,
  clearProfessorOnboardingSessionId,
  professorOnboardingSessionKey,
  readProfessorOnboardingSessionId,
  writeProfessorOnboardingSessionId,
} from "@/lib/onboarding/session-index"

describe("professor onboarding session index", () => {
  it("scopes one resumable session identifier to each professor account", () => {
    const values = new Map<string, string>()
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    }

    writeProfessorOnboardingSessionId(storage, "professor/a", "session-a")

    expect(professorOnboardingSessionKey("professor/a")).toBe(
      `${PROFESSOR_ONBOARDING_SESSION_KEY}.professor%2Fa`,
    )
    expect(readProfessorOnboardingSessionId(storage, "professor/a")).toBe(
      "session-a",
    )
    expect(readProfessorOnboardingSessionId(storage, "professor-b")).toBeNull()

    clearProfessorOnboardingSessionId(storage, "professor/a")
    expect(readProfessorOnboardingSessionId(storage, "professor/a")).toBeNull()
  })

  it("rejects blank and oversized saved identifiers", () => {
    expect(
      readProfessorOnboardingSessionId(
        { getItem: () => " ".repeat(4) },
        "professor-a",
      ),
    ).toBeNull()
    expect(
      readProfessorOnboardingSessionId(
        { getItem: () => "s".repeat(129) },
        "professor-a",
      ),
    ).toBeNull()
  })
})
