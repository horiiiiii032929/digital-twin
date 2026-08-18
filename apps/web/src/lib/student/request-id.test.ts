import { describe, expect, it } from "vitest"

import { createStudentRequestId } from "@/lib/student/request-id"

describe("student request IDs", () => {
  it("uses the browser UUID implementation when it is available", () => {
    expect(
      createStudentRequestId({ randomUUID: () => "request-uuid" }),
    ).toBe("request-uuid")
  })

  it("creates a stable-format fallback for non-secure LAN contexts", () => {
    expect(
      createStudentRequestId({
        randomUUID: null,
        now: () => 1234,
        random: () => 0.5,
      }),
    ).toBe("student-request-1234-i")
  })
})
