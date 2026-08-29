import { pathSegment, request } from "@/lib/api/client"
import type {
  CourseMembership,
  OnboardingSession,
  ProfessorCourse,
  ProfessorIngestionJob,
  ProfessorIngestionResult,
  ProfessorLearningGapResult,
  ProfessorProactiveTrigger,
  ProfessorRelease,
  ProfessorTeachingProfile,
  ProfessorTeachingProfilePreview,
  ReleasePreflightResult,
} from "@/lib/api/types"

export const PROFESSOR_ACCOUNT_ID =
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

export function bindProfessorOnboardingSession(
  courseId: string,
  sessionId: string,
): Promise<OnboardingSession> {
  return professorRequest<OnboardingSession>(
    `/api/professor/courses/${pathSegment(courseId)}/onboarding-sessions/${pathSegment(sessionId)}/bind`,
    { method: "POST" },
  )
}

export function assignProfessorCourseStudent(
  courseId: string,
  studentAccountId: string,
): Promise<CourseMembership> {
  return professorRequest(`/api/professor/courses/${pathSegment(courseId)}/students`, {
    method: "POST",
    body: JSON.stringify({ student_account_id: studentAccountId }),
  })
}

export function listProfessorIngestionJobs(
  courseId: string,
): Promise<ProfessorIngestionJob[]> {
  return professorRequest<ProfessorIngestionJob[]>(
    `/api/professor/courses/${pathSegment(courseId)}/ingestion-jobs`,
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
}): Promise<ProfessorIngestionJob | ProfessorIngestionResult> {
  const query = new URLSearchParams({
    title,
    version: "1",
    display_allowed: "true",
    source_label: "course-approved",
  })
  return professorRequest<ProfessorIngestionJob | ProfessorIngestionResult>(
    `/api/professor/courses/${pathSegment(courseId)}/sources/${pathSegment(artifactId)}?${query}`,
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
    `/api/professor/ingestion-jobs/${pathSegment(jobId)}`,
  )
}

export function retryProfessorIngestionJob(
  jobId: string,
): Promise<ProfessorIngestionJob> {
  return professorRequest<ProfessorIngestionJob>(
    `/api/professor/ingestion-jobs/${pathSegment(jobId)}/retry`,
    { method: "POST" },
  )
}

export function cancelProfessorIngestionJob(
  jobId: string,
): Promise<ProfessorIngestionJob> {
  return professorRequest<ProfessorIngestionJob>(
    `/api/professor/ingestion-jobs/${pathSegment(jobId)}/cancel`,
    { method: "POST" },
  )
}

export function createProfessorRelease({
  courseId,
  sessionId,
  chunks = [],
  ingestionJobIds = [],
  teachingProfileId,
}: {
  courseId: string
  sessionId: string
  chunks?: Record<string, unknown>[]
  ingestionJobIds?: string[]
  teachingProfileId?: string
}): Promise<ProfessorRelease> {
  return professorRequest<ProfessorRelease>(
    `/api/professor/courses/${pathSegment(courseId)}/releases`,
    {
      method: "POST",
      body: JSON.stringify(
        buildProfessorReleasePayload(
          { sessionId, chunks, ingestionJobIds, teachingProfileId },
          SESSION_AUTH_ENABLED,
        ),
      ),
    },
  )
}

export function buildProfessorReleasePayload(
  {
    sessionId,
    chunks,
    ingestionJobIds,
    teachingProfileId,
  }: {
    sessionId: string
    chunks: Record<string, unknown>[]
    ingestionJobIds: string[]
    teachingProfileId?: string
  },
  sessionAuthEnabled: boolean,
) {
  return {
    session_id: sessionId,
    profile_id: "student-tutor",
    profile_version: "v1",
    chunks: sessionAuthEnabled ? [] : chunks,
    ingestion_job_ids: sessionAuthEnabled ? ingestionJobIds : [],
    ...(teachingProfileId
      ? { teaching_profile_id: teachingProfileId }
      : {}),
  }
}

export function listProfessorTeachingProfiles(
  courseId: string,
): Promise<ProfessorTeachingProfile[]> {
  return professorRequest<ProfessorTeachingProfile[]>(
    `/api/professor/courses/${pathSegment(courseId)}/teaching-profiles`,
  )
}

export function createProfessorTeachingProfile(
  courseId: string,
  values: Omit<
    ProfessorTeachingProfile,
    | "schema_version"
    | "profile_id"
    | "course_id"
    | "version"
    | "status"
    | "content_sha256"
    | "preview_sha256"
    | "created_at"
    | "approved_at"
    | "withdrawn_at"
  >,
): Promise<ProfessorTeachingProfile> {
  return professorRequest(
    `/api/professor/courses/${pathSegment(courseId)}/teaching-profiles`,
    { method: "POST", body: JSON.stringify(values) },
  )
}

export function previewProfessorTeachingProfile(
  courseId: string,
  profileId: string,
): Promise<ProfessorTeachingProfilePreview> {
  return professorRequest(
    `/api/professor/courses/${pathSegment(courseId)}/teaching-profiles/${pathSegment(profileId)}/preview`,
  )
}

export function approveProfessorTeachingProfile(
  courseId: string,
  profileId: string,
  previewSha256: string,
): Promise<ProfessorTeachingProfile> {
  return professorRequest(
    `/api/professor/courses/${pathSegment(courseId)}/teaching-profiles/${pathSegment(profileId)}/approve`,
    { method: "POST", body: JSON.stringify({ preview_sha256: previewSha256 }) },
  )
}

export function listProfessorLearningGaps(
  courseId: string,
  releaseId: string,
): Promise<ProfessorLearningGapResult> {
  const query = new URLSearchParams({ release_id: releaseId })
  return professorRequest(
    `/api/professor/courses/${pathSegment(courseId)}/learning-gaps?${query}`,
  )
}

export function listProfessorProactiveTriggers(
  courseId: string,
): Promise<ProfessorProactiveTrigger[]> {
  return professorRequest(
    `/api/professor/courses/${pathSegment(courseId)}/proactive-triggers`,
  )
}

export function scheduleProfessorProactiveTrigger(
  courseId: string,
  values: {
    student_account_id: string
    scheduled_for: string
    expires_at: string
    topic: string
    prompt: string
    source_chunk_id: string
  },
): Promise<ProfessorProactiveTrigger> {
  return professorRequest(
    `/api/professor/courses/${pathSegment(courseId)}/proactive-triggers`,
    {
      method: "POST",
      body: JSON.stringify({
        ...values,
        channel: "in-app",
        kind: "scheduled-retrieval-practice",
        idempotency_key: crypto.randomUUID(),
      }),
    },
  )
}

export function cancelProfessorProactiveTrigger(
  courseId: string,
  triggerId: string,
): Promise<ProfessorProactiveTrigger> {
  return professorRequest(
    `/api/professor/courses/${pathSegment(courseId)}/proactive-triggers/${pathSegment(triggerId)}/cancel`,
    { method: "POST" },
  )
}

export function runProfessorReleasePreflight(
  releaseId: string,
): Promise<ReleasePreflightResult> {
  return professorRequest<ReleasePreflightResult>(
    `/api/professor/releases/${pathSegment(releaseId)}/preflight`,
    { method: "POST" },
  )
}

export function publishProfessorRelease(
  releaseId: string,
): Promise<ProfessorRelease> {
  return professorRequest<ProfessorRelease>(
    `/api/professor/releases/${pathSegment(releaseId)}/publish`,
    { method: "POST" },
  )
}

export function isProfessorIngestionJob(
  result: ProfessorIngestionJob | ProfessorIngestionResult,
): result is ProfessorIngestionJob {
  return "status" in result
}

export function buildInlineProfessorIngestionJob({
  courseId,
  artifactId,
  title,
  result,
  timestamp,
}: {
  courseId: string
  artifactId: string
  title: string
  result: ProfessorIngestionResult
  timestamp: string
}): ProfessorIngestionJob {
  return {
    id: `inline-${result.source_checksum.slice(0, 16)}`,
    course_id: courseId,
    artifact_id: artifactId,
    title,
    version: result.source_version,
    status: "succeeded",
    attempts: 1,
    max_attempts: 1,
    result,
    created_at: timestamp,
    updated_at: timestamp,
  }
}
