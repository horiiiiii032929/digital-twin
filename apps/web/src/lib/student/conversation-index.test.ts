import { describe, expect, it } from "vitest"

import {
  EMPTY_STUDENT_CONVERSATION_INDEX,
  STUDENT_CONVERSATION_INDEX_KEY,
  forgetStudentConversation,
  isConversationForCurrentRelease,
  readStudentConversationIndex,
  rememberStudentConversation,
  studentConversationIndexKey,
  writeStudentConversationIndex,
} from "@/lib/student/conversation-index"

describe("student conversation index", () => {
  it("returns an empty versioned index for missing or invalid state", () => {
    expect(readStudentConversationIndex(memoryStorage())).toEqual(
      EMPTY_STUDENT_CONVERSATION_INDEX,
    )
    expect(
      readStudentConversationIndex(memoryStorage("not-json")),
    ).toEqual(EMPTY_STUDENT_CONVERSATION_INDEX)
    expect(
      readStudentConversationIndex(
        memoryStorage(JSON.stringify({ version: 2, conversationByCourse: {} })),
      ),
    ).toEqual(EMPTY_STUDENT_CONVERSATION_INDEX)
  })

  it("stores only the active course and conversation identifiers", () => {
    const values = new Map<string, string>()
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    }
    const index = rememberStudentConversation(
      EMPTY_STUDENT_CONVERSATION_INDEX,
      "course-a",
      "conversation-a",
    )

    writeStudentConversationIndex(storage, index)

    expect(readStudentConversationIndex(storage)).toEqual(index)
    expect(values.get(STUDENT_CONVERSATION_INDEX_KEY)).not.toContain(
      "student message",
    )
  })

  it("forgets a stale conversation without changing the active course", () => {
    const remembered = rememberStudentConversation(
      EMPTY_STUDENT_CONVERSATION_INDEX,
      "course-a",
      "conversation-a",
    )

    expect(forgetStudentConversation(remembered, "course-a")).toEqual({
      version: 1,
      activeCourseId: "course-a",
      conversationByCourse: {},
    })
  })

  it("isolates remembered conversations by signed-in account", () => {
    const values = new Map<string, string>()
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    }
    const first = rememberStudentConversation(
      EMPTY_STUDENT_CONVERSATION_INDEX,
      "course-a",
      "conversation-a",
    )

    writeStudentConversationIndex(storage, first, "student/a")

    expect(studentConversationIndexKey("student/a")).toBe(
      `${STUDENT_CONVERSATION_INDEX_KEY}.student%2Fa`,
    )
    expect(readStudentConversationIndex(storage, "student/a")).toEqual(first)
    expect(readStudentConversationIndex(storage, "student-b")).toEqual(
      EMPTY_STUDENT_CONVERSATION_INDEX,
    )
  })

  it("rejects conversations from another course or superseded release", () => {
    const course = {
      course_id: "course-a",
      title: "Course A",
      release_id: "release-2",
      profile_id: "student-tutor",
      profile_version: "v1",
    }
    const conversation = {
      id: "conversation-a",
      student_id: "student-a",
      course_id: "course-a",
      release_id: "release-2",
      created_at: "2026-08-20T00:00:00Z",
      updated_at: "2026-08-20T00:00:00Z",
    }

    expect(isConversationForCurrentRelease(conversation, course)).toBe(true)
    expect(
      isConversationForCurrentRelease(
        { ...conversation, release_id: "release-1" },
        course,
      ),
    ).toBe(false)
    expect(
      isConversationForCurrentRelease(
        { ...conversation, course_id: "course-b" },
        course,
      ),
    ).toBe(false)
  })
})

function memoryStorage(initial?: string) {
  return {
    getItem: (key: string) =>
      key === STUDENT_CONVERSATION_INDEX_KEY ? (initial ?? null) : null,
  }
}
