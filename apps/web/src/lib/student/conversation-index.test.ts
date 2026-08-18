import { describe, expect, it } from "vitest"

import {
  EMPTY_STUDENT_CONVERSATION_INDEX,
  STUDENT_CONVERSATION_INDEX_KEY,
  forgetStudentConversation,
  readStudentConversationIndex,
  rememberStudentConversation,
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
})

function memoryStorage(initial?: string) {
  return {
    getItem: (key: string) =>
      key === STUDENT_CONVERSATION_INDEX_KEY ? (initial ?? null) : null,
  }
}
