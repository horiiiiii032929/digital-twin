export const STUDENT_CONVERSATION_INDEX_KEY =
  "course-digital-twin.student-conversations.v1"

export type StudentConversationIndex = {
  version: 1
  activeCourseId: string | null
  conversationByCourse: Record<string, string>
}

export const EMPTY_STUDENT_CONVERSATION_INDEX: StudentConversationIndex = {
  version: 1,
  activeCourseId: null,
  conversationByCourse: {},
}

export function readStudentConversationIndex(
  storage: Pick<Storage, "getItem">,
): StudentConversationIndex {
  try {
    const raw = storage.getItem(STUDENT_CONVERSATION_INDEX_KEY)
    if (!raw) return { ...EMPTY_STUDENT_CONVERSATION_INDEX }

    const parsed = JSON.parse(raw) as Partial<StudentConversationIndex>
    if (parsed.version !== 1 || !isStringRecord(parsed.conversationByCourse)) {
      return { ...EMPTY_STUDENT_CONVERSATION_INDEX }
    }

    return {
      version: 1,
      activeCourseId:
        typeof parsed.activeCourseId === "string" ? parsed.activeCourseId : null,
      conversationByCourse: { ...parsed.conversationByCourse },
    }
  } catch {
    return { ...EMPTY_STUDENT_CONVERSATION_INDEX }
  }
}

export function writeStudentConversationIndex(
  storage: Pick<Storage, "setItem">,
  index: StudentConversationIndex,
): void {
  storage.setItem(STUDENT_CONVERSATION_INDEX_KEY, JSON.stringify(index))
}

export function rememberStudentConversation(
  index: StudentConversationIndex,
  courseId: string,
  conversationId: string,
): StudentConversationIndex {
  return {
    version: 1,
    activeCourseId: courseId,
    conversationByCourse: {
      ...index.conversationByCourse,
      [courseId]: conversationId,
    },
  }
}

export function forgetStudentConversation(
  index: StudentConversationIndex,
  courseId: string,
): StudentConversationIndex {
  const conversationByCourse = { ...index.conversationByCourse }
  delete conversationByCourse[courseId]
  return { ...index, conversationByCourse }
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return (
    typeof value === "object" &&
    value !== null &&
    Object.values(value).every((entry) => typeof entry === "string")
  )
}
