import { describe, expect, it } from "vitest"

import { mergePolicyDrafts } from "@/lib/onboarding/policy-drafts"

describe("policy draft synchronization", () => {
  it("preserves an unsaved field while accepting server updates elsewhere", () => {
    const previousServer = {
      fieldA: { status: "needs_review" as const, value: "Original A" },
      fieldB: { status: "needs_review" as const, value: "Original B" },
    }
    const current = {
      ...previousServer,
      fieldA: { status: "needs_review" as const, value: "Unsaved A" },
    }
    const nextServer = {
      fieldA: previousServer.fieldA,
      fieldB: { status: "resolved" as const, value: "Saved B" },
    }

    expect(mergePolicyDrafts(current, previousServer, nextServer)).toEqual({
      fieldA: current.fieldA,
      fieldB: nextServer.fieldB,
    })
  })
})
