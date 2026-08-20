import type { StudentConversation, StudentCourse } from "@/lib/api/types"

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
  accountId?: string,
): StudentConversationIndex {
  try {
    const raw = storage.getItem(studentConversationIndexKey(accountId))
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
  accountId?: string,
): void {
  storage.setItem(studentConversationIndexKey(accountId), JSON.stringify(index))
}

export function studentConversationIndexKey(accountId?: string): string {
  const scope = accountId?.trim()
  return scope
    ? `${STUDENT_CONVERSATION_INDEX_KEY}.${encodeURIComponent(scope)}`
    : STUDENT_CONVERSATION_INDEX_KEY
}

export function isConversationForCurrentRelease(
  conversation: StudentConversation,
  course: StudentCourse,
): boolean {
  return (
    conversation.course_id === course.course_id &&
    conversation.release_id === course.release_id
  )
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
