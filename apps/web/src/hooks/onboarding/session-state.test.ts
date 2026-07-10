import { describe, expect, it } from "vitest"

import {
  errorMessage,
  initialSessionState,
  sessionReducer,
} from "@/hooks/onboarding/session-state"
import type { OnboardingSession } from "@/lib/api/types"

const SESSION: OnboardingSession = {
  session_id: "session-1",
  current_step: "source_permissions",
  answers: {},
  messages: [],
  source_inventory: [],
  policy: null,
  policy_version: 1,
  preview_cases: [],
  preview_decisions: {},
  evidence_snapshots: [],
  revision_proposal: null,
  approval_checklist: [],
  release_blockers: {},
  trace: [],
}

describe("session reducer", () => {
  it("tracks request state and clears prior errors", () => {
    const failed = sessionReducer(initialSessionState, {
      type: "operation/failed",
      operation: "source-update",
      error: "Source update failed.",
    })
    const pending = sessionReducer(failed, {
      type: "operation/pending",
      operation: "source-update",
      id: "source-1",
    })
    const finished = sessionReducer(pending, {
      type: "operation/finished",
      operation: "source-update",
    })

    expect(pending.error).toBeNull()
    expect(pending.updatingSourceId).toBe("source-1")
    expect(finished.updatingSourceId).toBeNull()
  })

  it("stores successful sessions and preserves request errors", () => {
    const succeeded = sessionReducer(initialSessionState, {
      type: "start/succeeded",
      session: SESSION,
    })
    const failed = sessionReducer(succeeded, {
      type: "operation/failed",
      operation: "message",
      error: "Message failed.",
    })

    expect(succeeded.session).toEqual(SESSION)
    expect(succeeded.isStarting).toBe(false)
    expect(failed.error).toBe("Message failed.")
  })

  it("normalizes unknown failures", () => {
    expect(errorMessage(new Error("API unavailable"))).toBe("API unavailable")
    expect(errorMessage({ reason: "unknown" })).toBe(
      "Unexpected onboarding error.",
    )
  })
})
