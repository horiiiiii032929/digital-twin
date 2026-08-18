import { request } from "@/lib/api/client"
import type {
  ProfessorCourse,
  ProfessorIngestionJob,
  ProfessorRelease,
  ReleasePreflightResult,
} from "@/lib/api/types"

const PROFESSOR_ACCOUNT_ID =
  import.meta.env.VITE_PROFESSOR_ACCOUNT_ID?.trim() || "professor-synthetic"
const SESSION_AUTH_ENABLED = import.meta.env.VITE_AUTH_MODE === "session"

function professorRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  return request<T>(path, {
    ...options,
    headers: {
      ...(SESSION_AUTH_ENABLED
        ? {}
        : { "X-Account-ID": PROFESSOR_ACCOUNT_ID }),
      ...options.headers,
    },
  })
}

export function listProfessorCourses(): Promise<ProfessorCourse[]> {
  return professorRequest<ProfessorCourse[]>("/api/professor/courses")
}

export function createProfessorCourse(title: string): Promise<{
  id: string
  title: string
  owner_professor_id: string
}> {
  return professorRequest("/api/professor/courses", {
    method: "POST",
    body: JSON.stringify({ title }),
  })
}

export function assignProfessorCourseStudent(
  courseId: string,
  studentAccountId: string,
): Promise<void> {
  return professorRequest(`/api/professor/courses/${courseId}/students`, {
    method: "POST",
    body: JSON.stringify({ student_account_id: studentAccountId }),
  })
}

export function listProfessorIngestionJobs(
  courseId: string,
): Promise<ProfessorIngestionJob[]> {
  return professorRequest<ProfessorIngestionJob[]>(
    `/api/professor/courses/${courseId}/ingestion-jobs`,
  )
}

export function uploadProfessorCoursePdf({
  courseId,
  artifactId,
  title,
  file,
  idempotencyKey,
}: {
  courseId: string
  artifactId: string
  title: string
  file: File
  idempotencyKey: string
}): Promise<ProfessorIngestionJob> {
  const query = new URLSearchParams({
    title,
    version: "1",
    display_allowed: "true",
    source_label: "course-approved",
  })
  return professorRequest<ProfessorIngestionJob>(
    `/api/professor/courses/${courseId}/sources/${encodeURIComponent(artifactId)}?${query}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/pdf",
        "Idempotency-Key": idempotencyKey,
      },
      body: file,
    },
  )
}

export function getProfessorIngestionJob(
  jobId: string,
): Promise<ProfessorIngestionJob> {
  return professorRequest<ProfessorIngestionJob>(
    `/api/professor/ingestion-jobs/${jobId}`,
  )
}

export function retryProfessorIngestionJob(
  jobId: string,
): Promise<ProfessorIngestionJob> {
  return professorRequest<ProfessorIngestionJob>(
    `/api/professor/ingestion-jobs/${jobId}/retry`,
    { method: "POST" },
  )
}

export function cancelProfessorIngestionJob(
  jobId: string,
): Promise<ProfessorIngestionJob> {
  return professorRequest<ProfessorIngestionJob>(
    `/api/professor/ingestion-jobs/${jobId}/cancel`,
    { method: "POST" },
  )
}

export function createProfessorRelease({
  courseId,
  sessionId,
  chunks,
}: {
  courseId: string
  sessionId: string
  chunks: Record<string, unknown>[]
}): Promise<ProfessorRelease> {
  return professorRequest<ProfessorRelease>(
    `/api/professor/courses/${courseId}/releases`,
    {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        profile_id: "student-tutor",
        profile_version: "v1",
        chunks,
      }),
    },
  )
}

export function runProfessorReleasePreflight(
  releaseId: string,
): Promise<ReleasePreflightResult> {
  return professorRequest<ReleasePreflightResult>(
    `/api/professor/releases/${releaseId}/preflight`,
    { method: "POST" },
  )
}

export function publishProfessorRelease(
  releaseId: string,
): Promise<ProfessorRelease> {
  return professorRequest<ProfessorRelease>(
    `/api/professor/releases/${releaseId}/publish`,
    { method: "POST" },
  )
}
