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
    expect(getNextAction(null, readiness.blockers)).toMatchObject({
      title: "Starting onboarding session",
      stage: "interview",
    })
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
    expect(getNextAction(session, readiness.blockers)).toMatchObject({
      title: "Release gate is clear",
      stage: "approval",
    })
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
    expect(getNextAction(session, readiness.blockers)).toMatchObject({
      title: "Add source metadata first",
      stage: "sources",
    })
  })

  it("routes release blockers to the review surface that can resolve them", () => {
    const session = approvedSession()

    expect(
      getNextAction(session, ["Accept all required preview evidence."]).stage,
    ).toBe("preview")
    expect(
      getNextAction(session, ["Complete the professor approval checklist."])
        .stage,
    ).toBe("approval")
  })

  it("does not count pending source metadata as an approved source", () => {
    const session = approvedSession()
    session.source_inventory[0].permission_status = "pending"

    const readiness = getReleaseReadiness(session)

    expect(readiness.approvedSources).toBe(0)
    expect(readiness.blockers).toContain(
      "Add at least one approved source metadata item.",
    )
    expect(getNextAction(session, readiness.blockers).stage).toBe("sources")
    expect(getStepStates(session)[0].state).toBe("blocked")
  })

  it("derives blocked preview and approval stages from unresolved records", () => {
    const session = approvedSession()
    session.preview_cases[0].decision = "pending"
    session.approval_checklist[0].checked = false
    session.release_blockers = {}

    const steps = getStepStates(session)

    expect(steps.find((step) => step.id === "preview")?.state).toBe("blocked")
    expect(steps.find((step) => step.id === "approval")?.state).toBe("blocked")
  })
})
