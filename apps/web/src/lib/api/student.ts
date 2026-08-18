import { ApiError } from "@/lib/api/client"
import type {
  StudentCitation,
  StudentConversation,
  StudentConversationView,
  StudentCourse,
  StudentTutorTurn,
} from "@/lib/api/types"

export const STUDENT_ACCOUNT_ID =
  import.meta.env.VITE_STUDENT_ACCOUNT_ID?.trim() || "student-a-synthetic"

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
  return { "X-Account-ID": accountId }
}

export function listStudentCourses(
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentCourse[]> {
  return studentRequest<StudentCourse[]>("/api/student/courses", {
    headers: studentHeaders(accountId),
  })
}

export function createStudentConversation(
  courseId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentConversation> {
  return studentRequest<StudentConversation>(
    `/api/student/courses/${courseId}/conversations`,
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
    `/api/student/conversations/${conversationId}`,
    { headers: studentHeaders(accountId) },
  )
}

export function submitStudentMessage(
  conversationId: string,
  content: string,
  requestId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentTutorTurn> {
  return studentRequest<StudentTutorTurn>(
    `/api/student/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: studentHeaders(accountId),
      body: JSON.stringify({ content, request_id: requestId }),
    },
  )
}

export function listStudentMessageCitations(
  messageId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<StudentCitation[]> {
  return studentRequest<StudentCitation[]>(
    `/api/student/messages/${messageId}/citations`,
    { headers: studentHeaders(accountId) },
  )
}

export async function loadStudentCitationCrop(
  messageId: string,
  citationId: string,
  accountId = STUDENT_ACCOUNT_ID,
): Promise<Blob> {
  const response = await fetch(
    `${API_BASE_URL}/api/student/messages/${messageId}/citations/${citationId}/crop`,
    { headers: studentHeaders(accountId) },
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
