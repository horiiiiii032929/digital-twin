import { afterEach, describe, expect, it, vi } from "vitest"

import {
  StudentApiError,
  createStudentConversation,
  getStudentConversation,
  dismissStudentOutreach,
  listStudentOutreach,
  listStudentOutreachPreferences,
  listStudentCourses,
  listStudentMessageCitations,
  loadStudentCitationCrop,
  markStudentOutreachRead,
  submitStudentMessage,
  updateStudentInAppOutreachPreference,
} from "@/lib/api/student"

describe("student API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("sends the synthetic account boundary on every student request", async () => {
    const fetchMock = stubFetch([])

    await listStudentCourses("student-a-synthetic")

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/student/courses",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Account-ID": "student-a-synthetic",
        }),
      }),
    )
  })

  it("uses the existing course, conversation, message, and citation routes", async () => {
    const fetchMock = stubFetch({})

    await createStudentConversation("course-a", "student-a")
    await getStudentConversation("conversation-a", "student-a")
    await submitStudentMessage(
      "conversation-a",
      "What is cache coherence?",
      "request-a",
      "student-a",
    )
    await listStudentMessageCitations("message-a", "student-a")
    await loadStudentCitationCrop("message-a", "citation-a", "student-a")

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/student/courses/course-a/conversations",
      expect.objectContaining({ method: "POST" }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/student/conversations/conversation-a",
      expect.any(Object),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/student/conversations/conversation-a/messages",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          content: "What is cache coherence?",
          request_id: "request-a",
        }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/student/messages/message-a/citations",
      expect.any(Object),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/student/messages/message-a/citations/citation-a/crop",
      expect.objectContaining({
        headers: expect.objectContaining({ "X-Account-ID": "student-a" }),
      }),
    )
  })

  it("preserves structured recovery codes from the API", async () => {
    stubFetch(
      {
        detail: {
          code: "release_unavailable",
          message: "The Digital Twin release has been withdrawn or replaced.",
        },
      },
      409,
    )

    await expect(
      submitStudentMessage(
        "conversation-a",
        "Retry this question",
        "request-a",
        "student-a",
      ),
    ).rejects.toEqual(
      new StudentApiError(
        "The Digital Twin release has been withdrawn or replaced.",
        409,
        "release_unavailable",
      ),
    )
  })

  it("uses private outreach preference and inbox routes", async () => {
    const fetchMock = stubFetch({})

    await listStudentOutreach("course a", "student-a")
    await listStudentOutreachPreferences("course a", "student-a")
    await updateStudentInAppOutreachPreference("course a", true, "student-a")
    await updateStudentInAppOutreachPreference(
      "course a",
      true,
      "student-a",
      "2026-09-07T10:00:00.000Z",
    )
    await markStudentOutreachRead("message a", "student-a")
    await dismissStudentOutreach("message a", "student-a")

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/student/outreach?course_id=course%20a",
      expect.any(Object),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/student/courses/course%20a/outreach-preferences",
      expect.any(Object),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/student/courses/course%20a/outreach-preferences/in-app",
      expect.objectContaining({ method: "PUT" }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/student/courses/course%20a/outreach-preferences/in-app",
      expect.objectContaining({
        method: "PUT",
        body: expect.stringContaining("2026-09-07T10:00:00.000Z"),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/student/outreach/message%20a/read",
      expect.objectContaining({ method: "POST" }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      "/api/student/outreach/message%20a/dismiss",
      expect.objectContaining({ method: "POST" }),
    )
  })

  it("encodes dynamic student path segments", async () => {
    const fetchMock = stubFetch({})

    await getStudentConversation("conversation ?one", "student-a")

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/student/conversations/conversation%20%3Fone",
      expect.any(Object),
    )
  })
})

function stubFetch(payload: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(payload),
    blob: vi.fn().mockResolvedValue(new Blob(["synthetic-crop"])),
  })
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}
