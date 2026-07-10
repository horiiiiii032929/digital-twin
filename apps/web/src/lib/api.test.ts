import { afterEach, describe, expect, it, vi } from "vitest"

import {
  addCustomPreviewCase,
  addSourceInventoryItem,
  confirmRevisionProposal,
  createOnboardingSession,
  discardRevisionProposal,
  setPreviewDecision,
  submitOnboardingMessage,
  updateApprovalChecklistItem,
  updatePolicyField,
  updateSourceInventoryItem,
  type OnboardingSession,
} from "@/lib/api"

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
  release_blockers: {
    source_inventory: [],
    policy_fields: [],
    approval_checklist: [],
    preview_decisions: [],
    preview_acceptance: [],
  },
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

  it("adds source inventory metadata without file contents", async () => {
    const fetchMock = stubFetch(SESSION)

    await addSourceInventoryItem("session-1", {
      name: "week-01-slides.pdf",
      mime_type: "application/pdf",
      size_bytes: 2048,
      notes: "Synthetic file name only.",
    })

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/onboarding/sessions/session-1/source-inventory",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "week-01-slides.pdf",
          mime_type: "application/pdf",
          size_bytes: 2048,
          notes: "Synthetic file name only.",
        }),
      }),
    )
  })

  it("updates source inventory decisions", async () => {
    const fetchMock = stubFetch(SESSION)

    await updateSourceInventoryItem("session-1", "source-1", {
      permission_status: "approved",
      source_label: "course-approved",
      excluded: false,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/onboarding/sessions/session-1/source-inventory/source-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          permission_status: "approved",
          source_label: "course-approved",
          excluded: false,
        }),
      }),
    )
  })

  it("persists approval checklist decisions", async () => {
    const fetchMock = stubFetch(SESSION)

    await updateApprovalChecklistItem("session-1", "integrity", true)

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/onboarding/sessions/session-1/approval-checklist/integrity",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ checked: true }),
      }),
    )
  })

  it("submits preview decisions and custom prompts", async () => {
    const fetchMock = stubFetch(SESSION)

    await setPreviewDecision(
      "session-1",
      "academic-integrity",
      "rejected",
      "Too much homework help.",
    )
    await addCustomPreviewCase("session-1", {
      prompt: "Give one CSRF hint.",
      tag: "teaching_behavior",
    })

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/onboarding/sessions/session-1/preview-cases/academic-integrity/decision",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          decision: "rejected",
          reason: "Too much homework help.",
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/onboarding/sessions/session-1/preview-cases",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          prompt: "Give one CSRF hint.",
          tag: "teaching_behavior",
        }),
      }),
    )
  })

  it("confirms and discards revision proposals", async () => {
    const fetchMock = stubFetch(SESSION)

    await confirmRevisionProposal("session-1")
    await discardRevisionProposal("session-1")

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/onboarding/sessions/session-1/revision-proposal/confirm",
      expect.objectContaining({ method: "POST" }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/onboarding/sessions/session-1/revision-proposal/discard",
      expect.objectContaining({ method: "POST" }),
    )
  })
})

function stubFetch(payload: unknown, status = 200) {
  const fetchMock = vi.fn().mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify(payload), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  )

  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}
