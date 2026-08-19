import { afterEach, describe, expect, it, vi } from "vitest"

import {
  createProfessorRelease,
  listProfessorCourses,
  publishProfessorRelease,
  runProfessorReleasePreflight,
  uploadProfessorCoursePdf,
} from "@/lib/api/professor"

describe("professor API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("uses the synthetic professor boundary outside session mode", async () => {
    const fetchMock = stubFetch([])

    await listProfessorCourses()

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/professor/courses",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Account-ID": "professor-synthetic",
        }),
      }),
    )
  })

  it("uploads PDF bytes with an idempotency key", async () => {
    const fetchMock = stubFetch({})
    const file = new File(["%PDF-synthetic"], "lecture.pdf", {
      type: "application/pdf",
    })

    await uploadProfessorCoursePdf({
      courseId: "course-a",
      artifactId: "lecture-a",
      title: "Lecture A",
      file,
      idempotencyKey: "upload-a",
    })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/professor/courses/course-a/sources/lecture-a?"),
      expect.objectContaining({
        method: "PUT",
        body: file,
        headers: expect.objectContaining({
          "Content-Type": "application/pdf",
          "Idempotency-Key": "upload-a",
        }),
      }),
    )
  })

  it("creates, checks, and publishes through explicit release routes", async () => {
    const fetchMock = stubFetch({})

    await createProfessorRelease({
      courseId: "course-a",
      sessionId: "session-a",
      chunks: [{ id: "chunk-a" }],
    })
    await runProfessorReleasePreflight("release-a")
    await publishProfessorRelease("release-a")

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/professor/courses/course-a/releases",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          session_id: "session-a",
          profile_id: "student-tutor",
          profile_version: "v1",
          chunks: [{ id: "chunk-a" }],
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/professor/releases/release-a/preflight",
      expect.objectContaining({ method: "POST" }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/professor/releases/release-a/publish",
      expect.objectContaining({ method: "POST" }),
    )
  })
})

function stubFetch(payload: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(payload),
  })
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}
