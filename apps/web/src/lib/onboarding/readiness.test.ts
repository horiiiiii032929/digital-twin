import { describe, expect, it } from "vitest"

import type { OnboardingSession } from "@/lib/api/types"
import {
  getNextAction,
  getReleaseReadiness,
  getStepStates,
} from "@/lib/onboarding/readiness"

function approvedSession(): OnboardingSession {
  return {
    session_id: "session-1",
    current_step: "complete",
    answers: {},
    messages: [],
    source_inventory: [
      {
        id: "source-1",
        name: "syllabus.pdf",
        mime_type: "application/pdf",
        size_bytes: 100,
        permission_status: "approved",
        source_label: "course-approved",
        excluded: false,
        sensitive: false,
        notes: "Synthetic metadata.",
      },
    ],
    policy: {
      status: "approved",
      release_status: "approved",
      safety_compliance: [],
      pedagogy: [],
      professor_review: [],
    },
    policy_version: 1,
    preview_cases: [
      {
        id: "preview-1",
        tag: "source_grounding",
        prompt: "What is the attendance policy?",
        generic_response: "Check the syllabus.",
        configured_response: "The synthetic syllabus says attendance is required.",
        policy_signals: [],
        source_audit: [],
        warnings: [],
        decision: "accepted",
        policy_version: 1,
      },
    ],
    preview_decisions: {},
    evidence_snapshots: [],
    revision_proposal: null,
    approval_checklist: [
      {
        id: "approval-1",
        label: "Approve release",
        blocks_release: true,
        checked: true,
      },
    ],
    release_blockers: {},
    trace: [],
  }
}

describe("readiness selectors", () => {
  it("reports the initial loading blocker without a session", () => {
    const readiness = getReleaseReadiness(null)

    expect(readiness.status).toBe("draft")
    expect(readiness.blockers).toEqual(["Start the onboarding session."])
    expect(getNextAction(null, readiness.blockers).title).toBe(
      "Starting onboarding session",
    )
  })

  it("derives a clear gate from approved evidence", () => {
    const session = approvedSession()
    const readiness = getReleaseReadiness(session)

    expect(readiness).toMatchObject({
      status: "approved",
      blockers: [],
      approvedSources: 1,
      acceptedPreviews: 1,
      pendingPreviews: 0,
      checklistBlockers: 0,
    })
    expect(getNextAction(session, readiness.blockers).title).toBe(
      "Release gate is clear",
    )
    expect(getStepStates(session).find((step) => step.id === "approval")?.state).toBe(
      "complete",
    )
  })

  it("keeps source metadata and policy generation as explicit gates", () => {
    const session = { ...approvedSession(), source_inventory: [], policy: null }
    const readiness = getReleaseReadiness(session)

    expect(readiness.blockers).toContain(
      "Add at least one approved source metadata item.",
    )
    expect(readiness.blockers).toContain(
      "Complete the instructor interview to generate policy.",
    )
    expect(getNextAction(session, readiness.blockers).title).toBe(
      "Add source metadata first",
    )
  })
})
