import { afterEach, describe, expect, it, vi } from "vitest"

import {
  createOnboardingSession,
  submitOnboardingMessage,
  updatePolicyField,
  type OnboardingSession,
} from "@/lib/api"

const SESSION: OnboardingSession = {
  session_id: "session-1",
  current_step: "source_permissions",
  answers: {},
  messages: [],
  policy: null,
  preview_cases: [],
  approval_checklist: [],
  trace: [],
}

describe("onboarding API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("creates onboarding sessions", async () => {
    const fetchMock = stubFetch(SESSION, 201)

    await expect(createOnboardingSession()).resolves.toEqual(SESSION)
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/onboarding/sessions",
      expect.objectContaining({ method: "POST" }),
    )
  })

  it("submits messages to an existing session", async () => {
    const fetchMock = stubFetch(SESSION)

    await submitOnboardingMessage("session-1", "Use public slides only.")
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/onboarding/sessions/session-1/messages",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ content: "Use public slides only." }),
      }),
    )
  })

  it("updates policy fields with explicit status", async () => {
    const fetchMock = stubFetch(SESSION)

    await updatePolicyField(
      "session-1",
      "academic_integrity_policy",
      "Hints only",
      "needs_review",
    )
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/onboarding/sessions/session-1/policy-fields/academic_integrity_policy",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          value: "Hints only",
          status: "needs_review",
        }),
      }),
    )
  })
})

function stubFetch(payload: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  )

  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}
