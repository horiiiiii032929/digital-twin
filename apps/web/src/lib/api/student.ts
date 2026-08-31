import { ApiError, pathSegment } from "@/lib/api/client"
import type {
  AutonomousGoalV1,
  StudentCitation,
  StudentConversation,
  StudentConversationView,
  StudentCourse,
  StudentOutreachPreference,
  StudentProactiveMessageView,
  StudentLearnerEvidence,
  StudentTutorTurn,
} from "@/lib/api/types"

export const STUDENT_ACCOUNT_ID =
  import.meta.env.VITE_STUDENT_ACCOUNT_ID?.trim() || "student-a-synthetic"

export const SESSION_AUTH_ENABLED =
  import.meta.env.VITE_AUTH_MODE === "session"

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? ""

export class StudentApiError extends ApiError {
  readonly code?: string

  constructor(message: string, status: number, code?: string) {
    super(message, status)
    this.name = "StudentApiError"
    this.code = code
  }
}

function studentHeaders(accountId: string): HeadersInit {
  return SESSION_AUTH_ENABLED ? {} : { "X-Account-ID": accountId }
}

export function listStudentCourses(
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentCourse[]> {
  return studentRequest<StudentCourse[]>("/api/student/courses", {
    headers: studentHeaders(accountId),
  })
}

export function listStudentAutonomousGoals(
  courseId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<AutonomousGoalV1[]> {
  return studentRequest<AutonomousGoalV1[]>(
    `/api/student/courses/${pathSegment(courseId)}/autonomous-goals`,
    { headers: studentHeaders(accountId) },
  )
}

export function listStudentOutreach(
  courseId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentProactiveMessageView[]> {
  return studentRequest<StudentProactiveMessageView[]>(
    `/api/student/outreach?course_id=${encodeURIComponent(courseId)}`,
    { headers: studentHeaders(accountId) },
  )
}

export function listStudentOutreachPreferences(
  courseId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentOutreachPreference[]> {
  return studentRequest<StudentOutreachPreference[]>(
    `/api/student/courses/${pathSegment(courseId)}/outreach-preferences`,
    { headers: studentHeaders(accountId) },
  )
}

export function updateStudentInAppOutreachPreference(
  courseId: string,
  enabled: boolean,
  accountId = STUDENT_ACCOUNT_ID,
  snoozedUntil?: string | null,
): Promise<StudentOutreachPreference> {
  return studentRequest<StudentOutreachPreference>(
    `/api/student/courses/${pathSegment(courseId)}/outreach-preferences/in-app`,
    {
      method: "PUT",
      headers: studentHeaders(accountId),
      body: JSON.stringify({
        enabled,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        quiet_hours_start: "22:00",
        quiet_hours_end: "08:00",
        max_messages_per_7_days: 3,
        snoozed_until: snoozedUntil ?? null,
      }),
    },
  )
}

export function markStudentOutreachRead(
  messageId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentProactiveMessageView> {
  return studentRequest<StudentProactiveMessageView>(
    `/api/student/outreach/${pathSegment(messageId)}/read`,
    { method: "POST", headers: studentHeaders(accountId) },
  )
}

export function dismissStudentOutreach(
  messageId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentProactiveMessageView> {
  return studentRequest<StudentProactiveMessageView>(
    `/api/student/outreach/${pathSegment(messageId)}/dismiss`,
    { method: "POST", headers: studentHeaders(accountId) },
  )
}

export function createStudentConversation(
  courseId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentConversation> {
  return studentRequest<StudentConversation>(
    `/api/student/courses/${pathSegment(courseId)}/conversations`,
    {
      method: "POST",
      headers: studentHeaders(accountId),
    },
  )
}

export function getStudentConversation(
  conversationId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentConversationView> {
  return studentRequest<StudentConversationView>(
    `/api/student/conversations/${pathSegment(conversationId)}`,
    { headers: studentHeaders(accountId) },
  )
}

export function getStudentLearnerEvidence(
  conversationId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentLearnerEvidence> {
  return studentRequest<StudentLearnerEvidence>(
    `/api/student/conversations/${pathSegment(conversationId)}/learner-evidence`,
    { headers: studentHeaders(accountId) },
  )
}

export function submitStudentMessage(
  conversationId: string,
  content: string,
  requestId: string,
  accountId = STUDENT_ACCOUNT_ID,
  respondingToOutreachMessageId?: string,
): Promise<StudentTutorTurn> {
  return studentRequest<StudentTutorTurn>(
    `/api/student/conversations/${pathSegment(conversationId)}/messages`,
    {
      method: "POST",
      headers: studentHeaders(accountId),
      body: JSON.stringify({
        content,
        request_id: requestId,
        ...(respondingToOutreachMessageId
          ? { responding_to_outreach_message_id: respondingToOutreachMessageId }
          : {}),
      }),
    },
  )
}

export function listStudentMessageCitations(
  messageId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentCitation[]> {
  return studentRequest<StudentCitation[]>(
    `/api/student/messages/${pathSegment(messageId)}/citations`,
    { headers: studentHeaders(accountId) },
  )
}

export async function loadStudentCitationCrop(
  messageId: string,
  citationId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<Blob> {
  const response = await fetch(
    `${API_BASE_URL}/api/student/messages/${pathSegment(messageId)}/citations/${pathSegment(citationId)}/crop`,
    { credentials: "include", headers: studentHeaders(accountId) },
  )
  if (!response.ok) {
    const error = await readStudentError(response)
    throw new StudentApiError(error.message, response.status, error.code)
  }
  return response.blob()
}

async function studentRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await readStudentError(response)
    throw new StudentApiError(error.message, response.status, error.code)
  }

  return response.json() as Promise<T>
}

async function readStudentError(
  response: Response,
): Promise<{ message: string; code?: string }> {
  try {
    const payload = (await response.json()) as {
      detail?: string | { code?: string; message?: string }
    }

    if (typeof payload.detail === "string") {
      return { message: payload.detail }
    }

    if (payload.detail?.message) {
      return {
        message: payload.detail.message,
        code: payload.detail.code,
      }
    }
  } catch {
    return { message: `Request failed with status ${response.status}` }
  }

  return { message: `Request failed with status ${response.status}` }
}
