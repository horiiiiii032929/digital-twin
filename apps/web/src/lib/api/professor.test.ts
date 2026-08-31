import { afterEach, describe, expect, it, vi } from "vitest"

import {
  bindProfessorOnboardingSession,
  buildInlineProfessorIngestionJob,
  buildProfessorReleasePayload,
  cancelProfessorAutonomousGoal,
  createProfessorRelease,
  listProfessorAutonomousOutcomes,
  listProfessorCourses,
  isProfessorIngestionJob,
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
      ingestionJobIds: ["job-a"],
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
          ingestion_job_ids: [],
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

  it("binds tutor setup to a course before release", async () => {
    const fetchMock = stubFetch({})

    await bindProfessorOnboardingSession("course-a", "session-a")

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/professor/courses/course-a/onboarding-sessions/session-a/bind",
      expect.objectContaining({ method: "POST" }),
    )
  })

  it("never sends browser-returned chunks in session-auth staging mode", () => {
    expect(
      buildProfessorReleasePayload(
        {
          sessionId: "session-a",
          chunks: [{ id: "untrusted-browser-chunk" }],
          ingestionJobIds: ["server-job-a"],
        },
        true,
      ),
    ).toEqual({
      session_id: "session-a",
      profile_id: "student-tutor",
      profile_version: "v1",
      chunks: [],
      ingestion_job_ids: ["server-job-a"],
    })
  })

  it("keeps demo chunks and queued job identifiers mutually exclusive", () => {
    expect(
      buildProfessorReleasePayload(
        {
          sessionId: "session-a",
          chunks: [{ id: "inline-chunk" }],
          ingestionJobIds: ["must-not-be-sent"],
        },
        false,
      ),
    ).toEqual({
      session_id: "session-a",
      profile_id: "student-tutor",
      profile_version: "v1",
      chunks: [{ id: "inline-chunk" }],
      ingestion_job_ids: [],
    })
  })

  it("normalizes inline demo ingestion into a successful UI job", () => {
    const result = {
      source_artifact_id: "artifact-a",
      source_version: 2,
      source_checksum: "a".repeat(64),
      document_id: "document-a",
      chunk_count: 3,
      region_count: 4,
      region_kind_counts: { text: 4 },
      processing_warnings: [],
      chunks: [{ id: "chunk-a" }],
    }

    expect(isProfessorIngestionJob(result)).toBe(false)
    expect(
      buildInlineProfessorIngestionJob({
        courseId: "course-a",
        artifactId: "artifact-a",
        title: "Lecture A",
        result,
        timestamp: "2026-08-20T00:00:00Z",
      }),
    ).toMatchObject({
      id: `inline-${"a".repeat(16)}`,
      course_id: "course-a",
      artifact_id: "artifact-a",
      title: "Lecture A",
      status: "succeeded",
      result,
    })
  })

  it("encodes dynamic professor path segments", async () => {
    const fetchMock = stubFetch({})

    await bindProfessorOnboardingSession("course ?a", "session#one")

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/professor/courses/course%20%3Fa/onboarding-sessions/session%23one/bind",
      expect.objectContaining({ method: "POST" }),
    )
  })

  it("uses explicit autonomy goal cancellation and outcome audit routes", async () => {
    const fetchMock = stubFetch({})

    await cancelProfessorAutonomousGoal("course a", "goal/one")
    await listProfessorAutonomousOutcomes("course a", "student one")

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/professor/courses/course%20a/autonomous-goals/goal%2Fone/cancel",
      expect.objectContaining({ method: "POST" }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/professor/courses/course%20a/autonomous-outcomes?student_account_id=student+one",
      expect.any(Object),
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
