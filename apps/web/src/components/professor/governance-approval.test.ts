import { describe, expect, it } from "vitest"

import type { ProfessorTeachingProfilePreview } from "@/lib/api/types"

import { canApproveTeachingProfilePreview } from "./governance-approval"

function preview(overrides: Partial<ProfessorTeachingProfilePreview> = {}): ProfessorTeachingProfilePreview {
  return {
    schema_version: "1.0.0",
    profile_id: "profile-1",
    profile_content_sha256: "content-hash",
    preview_sha256: "preview-hash",
    cases: Array.from({ length: 10 }, (_, index) => ({
      case_id: `case-${index + 1}`,
      student_situation: `Situation ${index + 1}`,
      expected_behavior: `Behavior ${index + 1}`,
    })),
    ...overrides,
  }
}

describe("professor teaching-profile approval", () => {
  it("allows approval only for the displayed ten-case preview of the same profile", () => {
    expect(canApproveTeachingProfilePreview("profile-1", preview())).toBe(true)
  })

  it("blocks approval when the preview is absent, incomplete, mismatched, or unbound", () => {
    expect(canApproveTeachingProfilePreview("profile-1", null)).toBe(false)
    expect(canApproveTeachingProfilePreview("profile-1", preview({ cases: preview().cases.slice(0, 9) }))).toBe(false)
    expect(canApproveTeachingProfilePreview("profile-1", preview({ profile_id: "profile-2" }))).toBe(false)
    expect(canApproveTeachingProfilePreview("profile-1", preview({ preview_sha256: "" }))).toBe(false)
  })
})
