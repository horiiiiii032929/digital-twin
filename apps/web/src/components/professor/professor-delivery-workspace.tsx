import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react"
import {
  ArrowLeft,
  BookOpenCheck,
  Check,
  CheckCircle2,
  CircleAlert,
  LoaderCircle,
  PackageCheck,
  Plus,
  RefreshCw,
  RotateCcw,
  Upload,
  UserPlus,
  Users,
  X,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { WorkspaceBrand } from "@/components/workspace/workspace-brand"
import { ProfessorAutonomyPanel } from "@/components/professor/professor-autonomy-panel"
import type { OnboardingController } from "@/hooks/use-onboarding-session"
import {
  assignProfessorCourseStudent,
  buildInlineProfessorIngestionJob,
  cancelProfessorIngestionJob,
  createProfessorCourse,
  createProfessorRelease,
  isProfessorIngestionJob,
  listProfessorCourses,
  listProfessorIngestionJobs,
  publishProfessorRelease,
  retryProfessorIngestionJob,
  runProfessorReleasePreflight,
  uploadProfessorCoursePdf,
} from "@/lib/api/professor"
import type {
  ProfessorCourse,
  ProfessorIngestionJob,
  ProfessorEvidenceChunkOption,
  ProfessorReleaseSummary,
  ReleasePreflightResult,
} from "@/lib/api/types"
import { cn } from "@/lib/utils"

export function ProfessorDeliveryWorkspace({
  controller,
  onOpenSetup,
}: {
  controller: OnboardingController
  onOpenSetup: () => void
}) {
  const [courses, setCourses] = useState<ProfessorCourse[]>([])
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null)
  const [jobs, setJobs] = useState<ProfessorIngestionJob[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [preflight, setPreflight] = useState<ReleasePreflightResult | null>(null)
  const [approvedTeachingProfileId, setApprovedTeachingProfileId] = useState<string | null>(null)
  const selectedCourseIdRef = useRef<string | null>(null)
  const inlineJobsByCourseRef = useRef(
    new Map<string, ProfessorIngestionJob[]>(),
  )

  const selectedCourse = useMemo(
    () => courses.find((course) => course.course_id === selectedCourseId) ?? null,
    [courses, selectedCourseId],
  )
  const selectedRelease = selectedCourse?.releases[0] ?? null
  const successfulJobs = jobs.filter(
    (job) => job.status === "succeeded" && job.result,
  )
  const hasActiveJob = jobs.some(
    (job) => job.status === "pending" || job.status === "running",
  )
  const evidenceChunks: ProfessorEvidenceChunkOption[] = successfulJobs.flatMap((job) =>
    (job.result?.chunks ?? []).flatMap((chunk) => {
      const id = typeof chunk.id === "string" ? chunk.id : null
      const sourceArtifactId = typeof chunk.source_artifact_id === "string"
        ? chunk.source_artifact_id
        : typeof chunk.document_id === "string"
          ? chunk.document_id
          : null
      const sourceSha256 = typeof chunk.source_checksum === "string"
        ? chunk.source_checksum
        : typeof chunk.content_hash === "string"
          ? chunk.content_hash
          : null
      const locator = typeof chunk.locator === "string" ? chunk.locator : null
      const text = typeof chunk.text === "string" ? chunk.text : null
      if (!id || !sourceArtifactId || !sourceSha256 || !locator || !text) return []
      const title = typeof chunk.document_id === "string" ? chunk.document_id : id
      return [{
        id,
        label: `${title} · ${locator}`,
        source_artifact_id: sourceArtifactId,
        source_version: typeof chunk.source_version === "number" ? chunk.source_version : 1,
        source_sha256: sourceSha256,
        locator,
        char_start: 0,
        char_end: text.length,
      }]
    }),
  )

  const refreshCourses = useCallback(async (preferredCourseId?: string) => {
    const next = await listProfessorCourses()
    setCourses(next)
    setSelectedCourseId((current) => {
      const preferred = preferredCourseId ?? current
      return next.some((course) => course.course_id === preferred)
        ? (preferred ?? null)
        : (next[0]?.course_id ?? null)
    })
  }, [])

  const refreshJobs = useCallback(async (courseId: string) => {
    const remoteJobs = await listProfessorIngestionJobs(courseId)
    if (selectedCourseIdRef.current !== courseId) return
    const inlineJobs = inlineJobsByCourseRef.current.get(courseId) ?? []
    const remoteIds = new Set(remoteJobs.map((job) => job.id))
    setJobs([
      ...remoteJobs,
      ...inlineJobs.filter((job) => !remoteIds.has(job.id)),
    ])
  }, [])

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const next = await listProfessorCourses()
        if (!active) return
        setCourses(next)
        setSelectedCourseId(next[0]?.course_id ?? null)
      } catch (reason) {
        if (active) setError(message(reason))
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    selectedCourseIdRef.current = selectedCourseId
    setJobs([])
    setApprovedTeachingProfileId(null)
    if (!selectedCourseId) {
      return
    }
    setPreflight(null)
    void refreshJobs(selectedCourseId).catch((reason) => setError(message(reason)))
  }, [refreshJobs, selectedCourseId])

  useEffect(() => {
    if (!selectedCourseId || !hasActiveJob) return
    let active = true
    let timer: number | undefined
    const poll = async () => {
      try {
        await refreshJobs(selectedCourseId)
      } catch (reason) {
        if (active) setError(message(reason))
      } finally {
        if (active) timer = window.setTimeout(poll, 1800)
      }
    }
    timer = window.setTimeout(poll, 1800)
    return () => {
      active = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [hasActiveJob, refreshJobs, selectedCourseId])

  async function runAction(key: string, action: () => Promise<void>) {
    setBusy(key)
    setError(null)
    setNotice(null)
    try {
      await action()
    } catch (reason) {
      setError(message(reason))
    } finally {
      setBusy(null)
    }
  }

  async function createCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    await runAction("create-course", async () => {
      const created = await createProfessorCourse(String(data.get("title") ?? ""))
      await refreshCourses(created.id)
      form.reset()
      setNotice("Course created. Add a student and upload approved evidence next.")
    })
  }

  async function assignStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedCourse) return
    const form = event.currentTarget
    const data = new FormData(form)
    await runAction("assign-student", async () => {
      await assignProfessorCourseStudent(
        selectedCourse.course_id,
        String(data.get("student_account_id") ?? ""),
      )
      await refreshCourses(selectedCourse.course_id)
      form.reset()
      setNotice("Student assigned to this course.")
    })
  }

  async function uploadSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedCourse) return
    const form = event.currentTarget
    const data = new FormData(form)
    const file = data.get("source")
    if (!(file instanceof File) || !file.name) {
      setError("Choose a PDF before uploading.")
      return
    }
    if (file.type !== "application/pdf") {
      setError("Only PDF course materials are accepted.")
      return
    }
    await runAction("upload", async () => {
      const title = String(data.get("source_title") ?? "").trim() || file.name
      const artifact = artifactId(file.name)
      const uploaded = await uploadProfessorCoursePdf({
        courseId: selectedCourse.course_id,
        artifactId: artifact,
        title,
        file,
        idempotencyKey: crypto.randomUUID(),
      })
      if (isProfessorIngestionJob(uploaded)) {
        await refreshJobs(selectedCourse.course_id)
      } else {
        const inlineJob = buildInlineProfessorIngestionJob({
          courseId: selectedCourse.course_id,
          artifactId: artifact,
          title,
          result: uploaded,
          timestamp: new Date().toISOString(),
        })
        const existing =
          inlineJobsByCourseRef.current.get(selectedCourse.course_id) ?? []
        inlineJobsByCourseRef.current.set(selectedCourse.course_id, [
          inlineJob,
          ...existing.filter((job) => job.id !== inlineJob.id),
        ])
        if (selectedCourseIdRef.current === selectedCourse.course_id) {
          setJobs((current) => [
            inlineJob,
            ...current.filter((job) => job.id !== inlineJob.id),
          ])
        }
      }
      form.reset()
      setNotice(
        isProfessorIngestionJob(uploaded)
          ? "Upload queued. It is safe to leave this page while the worker processes it."
          : "Upload processed. The evidence is ready for tutor review.",
      )
    })
  }

  async function createDraft() {
    const session = controller.session
    if (!selectedCourse || !session) return
    await runAction("create-draft", async () => {
      if (
        session.course_id !== null &&
        session.course_id !== undefined &&
        session.course_id !== selectedCourse.course_id
      ) {
        throw new Error(
          "This tutor setup belongs to another course. Start a new tutor setup for the selected course.",
        )
      }
      const newlyBound = !session.course_id
      if (newlyBound) {
        const bound = await controller.bindCourse(selectedCourse.course_id)
        if (!bound) throw new Error("Could not bind tutor setup to this course.")
      }
      const unreviewedJobs = successfulJobs.filter(
        (job) =>
          !session.source_inventory.some((source) =>
            source.notes.includes(`ingestion job ${job.id}`),
          ),
      )
      if (unreviewedJobs.length > 0) {
        for (const job of unreviewedJobs) {
          const recorded = await controller.addSource({
            name: job.title,
            mime_type: "application/pdf",
            size_bytes: 0,
            permission_status: "approved",
            source_label: "course-approved",
            excluded: false,
            sensitive: false,
            notes: `Approved upload ${job.artifact_id}; ingestion job ${job.id}.`,
          })
          if (!recorded) throw new Error("Could not record the approved source.")
        }
        setNotice(
          "New evidence was added to tutor setup. Review the updated source scope and approve the current configuration before creating the release draft.",
        )
        return
      }
      if (newlyBound) {
        setNotice(
          "Tutor setup is now bound to this course. Review and approve the current course configuration before creating the release draft.",
        )
        return
      }
      const chunks = successfulJobs.flatMap((job) => job.result?.chunks ?? [])
      if (!approvedTeachingProfileId) {
        throw new Error("Approve the professor teaching profile before creating a release.")
      }
      await createProfessorRelease({
        courseId: selectedCourse.course_id,
        sessionId: session.session_id,
        chunks,
        ingestionJobIds: successfulJobs.map((job) => job.id),
        teachingProfileId: approvedTeachingProfileId,
      })
      await refreshCourses(selectedCourse.course_id)
      setPreflight(null)
      setNotice("Release draft created from the current tutor policy and approved evidence.")
    })
  }

  async function runPreflight(release: ProfessorReleaseSummary) {
    await runAction("preflight", async () => {
      const result = await runProfessorReleasePreflight(release.id)
      setPreflight(result)
      await refreshCourses(release.course_id)
      setNotice(
        result.passed
          ? "All deterministic release checks passed."
          : "The release is blocked. Review the failed checks below.",
      )
    })
  }

  async function publish(release: ProfessorReleaseSummary) {
    await runAction("publish", async () => {
      await publishProfessorRelease(release.id)
      await refreshCourses(release.course_id)
      setNotice("Release published. Assigned students can now use the course tutor.")
    })
  }

  return (
    <main className="h-dvh overflow-hidden bg-[var(--shell)] text-foreground">
      <div className="grid h-full min-h-0 lg:grid-cols-[216px_minmax(0,1fr)]">
        <aside className="workspace-rail hidden min-h-0 flex-col lg:flex">
          <WorkspaceBrand />
          <nav className="flex flex-col gap-1 p-3 pt-4" aria-label="Professor workspace">
            <Button className="w-full justify-start" variant="ghost" onClick={onOpenSetup}>
              <BookOpenCheck data-icon="inline-start" />
              Twin setup
            </Button>
            <Button
              className="w-full justify-start bg-white shadow-[0_1px_2px_rgba(25,25,29,0.06),0_5px_14px_rgba(25,25,29,0.04)]"
              variant="ghost"
            >
              <PackageCheck data-icon="inline-start" />
              Course delivery
            </Button>
          </nav>
          <div className="border-t px-3 pt-4">
            <p className="px-2 text-xs font-semibold text-muted-foreground">Courses</p>
            <div className="mt-2 flex flex-col gap-1">
              {courses.map((course) => (
                <button
                  key={course.course_id}
                  className={cn(
                    "w-full truncate rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                    course.course_id === selectedCourseId
                      ? "bg-white font-medium text-[var(--accent-foreground)] shadow-[0_1px_2px_rgba(25,25,29,0.05)]"
                      : "text-muted-foreground hover:bg-white/80 hover:text-foreground",
                  )}
                  disabled={busy !== null}
                  onClick={() => setSelectedCourseId(course.course_id)}
                >
                  {course.title}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-col">
          <header className="workspace-header flex min-h-16 items-center gap-3 pl-3 pr-14 sm:pl-5 xl:pr-56">
            <Button
              className="lg:hidden"
              size="icon"
              variant="ghost"
              aria-label="Return to tutor setup"
              onClick={onOpenSetup}
            >
              <ArrowLeft aria-hidden="true" />
            </Button>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold sm:text-base">Course operations</h1>
              <p className="hidden text-xs text-muted-foreground sm:block">
                Evidence, releases, and governed autonomy.
              </p>
            </div>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto bg-[var(--shell)]">
            <div className="mx-auto max-w-7xl px-4 py-7 sm:px-6 sm:py-9">
              {error ? (
                <Alert className="mb-5" variant="destructive">
                  <CircleAlert />
                  <AlertTitle>Action could not be completed</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}
              {notice ? (
                <Alert className="mb-5 border-[var(--success-border)] bg-[var(--success-soft)]">
                  <CheckCircle2 className="text-[var(--success)]" />
                  <AlertDescription className="text-[var(--success)]">{notice}</AlertDescription>
                </Alert>
              ) : null}

              {courses.length > 0 ? (
                <label className="mb-5 block lg:hidden">
                  <span className="mb-1.5 block text-xs font-medium text-muted-foreground">
                    Course
                  </span>
                  <select
                    aria-label="Select course"
                    className="h-11 w-full rounded-lg border bg-white px-3 text-sm font-medium outline-none focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]"
                    disabled={busy !== null}
                    value={selectedCourseId ?? ""}
                    onChange={(event) => setSelectedCourseId(event.target.value)}
                  >
                    {courses.map((course) => (
                      <option key={course.course_id} value={course.course_id}>
                        {course.title}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}

              <section className="grid grid-cols-[minmax(0,1fr)] gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
                <div className="flex min-w-0 flex-col gap-5">
                  <CourseHeader course={selectedCourse} loading={loading} />
                  {selectedCourse ? (
                    <>
                      <ProfessorAutonomyPanel
                        course={selectedCourse}
                        evidenceChunks={evidenceChunks}
                        releaseId={selectedRelease?.id}
                        onApprovedProfileChange={setApprovedTeachingProfileId}
                      />
                      <EvidenceCard
                        busy={busy}
                        jobs={jobs}
                        onCancel={(job) =>
                          void runAction(`cancel-${job.id}`, async () => {
                            await cancelProfessorIngestionJob(job.id)
                            await refreshJobs(selectedCourse.course_id)
                          })
                        }
                        onRetry={(job) =>
                          void runAction(`retry-${job.id}`, async () => {
                            await retryProfessorIngestionJob(job.id)
                            await refreshJobs(selectedCourse.course_id)
                          })
                        }
                        onSubmit={uploadSource}
                      />
                      <ReleaseCard
                        busy={busy}
                        onboardingReady={
                          controller.session?.policy?.release_status === "approved"
                        }
                        profileReady={approvedTeachingProfileId !== null}
                        preflight={preflight}
                        release={selectedRelease}
                        sourceCount={successfulJobs.length}
                        onCreateDraft={() => void createDraft()}
                        onPreflight={(release) => void runPreflight(release)}
                        onPublish={(release) => void publish(release)}
                        onOpenSetup={onOpenSetup}
                      />
                    </>
                  ) : null}
                </div>

                <aside className="flex min-w-0 flex-col gap-5">
                  <CreateCourseCard busy={busy} onSubmit={createCourse} />
                  {selectedCourse ? (
                    <StudentsCard
                      busy={busy}
                      course={selectedCourse}
                      onSubmit={assignStudent}
                    />
                  ) : null}
                </aside>
              </section>
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}

function CourseHeader({
  course,
  loading,
}: {
  course: ProfessorCourse | null
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="flex min-h-28 items-center justify-center rounded-xl border bg-white">
        <LoaderCircle className="size-5 animate-spin text-muted-foreground" aria-label="Loading courses" />
      </div>
    )
  }
  if (!course) {
    return (
      <div className="rounded-xl border border-dashed bg-white px-6 py-10 text-center">
        <PackageCheck className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
        <h2 className="mt-4 text-lg font-semibold">Create your first course</h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
          A course is the private boundary connecting one professor configuration,
          approved evidence, and assigned students.
        </p>
      </div>
    )
  }
  const published = course.releases.find((release) => release.status === "published")
  return (
    <header className="workspace-card rounded-2xl border bg-white px-5 py-5 sm:px-6 sm:py-6">
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:justify-between">
        <div className="min-w-0">
          <p className="workspace-kicker">Professor workspace</p>
          <h2 className="mt-1 break-words text-2xl font-semibold tracking-[-0.03em]">
            {course.title}
          </h2>
        </div>
        <Badge className="shrink-0" variant={published ? "default" : "outline"}>
          {published ? "Published" : "Not published"}
        </Badge>
      </div>
      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t pt-4 text-xs font-medium text-muted-foreground">
        <span>{course.student_account_ids.length} assigned student{course.student_account_ids.length === 1 ? "" : "s"}</span>
        <span>{course.releases.length} release{course.releases.length === 1 ? "" : "s"}</span>
        <span>{published ? "Student access is live" : "Not visible to students"}</span>
      </div>
    </header>
  )
}

function CreateCourseCard({
  busy,
  onSubmit,
}: {
  busy: string | null
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>New course</CardTitle>
        <CardDescription>Create an isolated student and evidence workspace.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={onSubmit}>
          <Field
            label="Course title"
            maxLength={240}
            name="title"
            placeholder="e.g. CS3230 Design and Analysis"
          />
          <Button className="w-full" disabled={busy !== null} type="submit">
            <Plus aria-hidden="true" />
            {busy === "create-course" ? "Creating…" : "Create course"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

function StudentsCard({
  busy,
  course,
  onSubmit,
}: {
  busy: string | null
  course: ProfessorCourse
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="size-4" aria-hidden="true" /> Students
        </CardTitle>
        <CardDescription>Use the account ID shown after the admin creates an invitation.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {course.student_account_ids.length ? (
          <ul className="space-y-2">
            {course.student_account_ids.map((studentId) => (
              <li key={studentId} className="truncate rounded-lg bg-muted px-3 py-2 text-xs font-medium">
                {studentId}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No students assigned yet.</p>
        )}
        <form className="space-y-3 border-t pt-4" onSubmit={onSubmit}>
          <Field
            label="Student account ID"
            maxLength={128}
            name="student_account_id"
            placeholder="account-…"
          />
          <Button
            className="w-full"
            disabled={busy !== null}
            type="submit"
            variant="outline"
          >
            <UserPlus aria-hidden="true" />
            {busy === "assign-student" ? "Assigning…" : "Assign student"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

function EvidenceCard({
  busy,
  jobs,
  onSubmit,
  onRetry,
  onCancel,
}: {
  busy: string | null
  jobs: ProfessorIngestionJob[]
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onRetry: (job: ProfessorIngestionJob) => void
  onCancel: (job: ProfessorIngestionJob) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Course evidence</CardTitle>
        <CardDescription>
          PDFs are stored privately, processed in a recoverable worker, and retained with citation lineage.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <form className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end" onSubmit={onSubmit}>
          <Field
            label="Source title"
            maxLength={240}
            name="source_title"
            placeholder="Week 1 lecture"
          />
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium">PDF file</span>
            <input
              accept="application/pdf,.pdf"
              className="block h-10 w-full rounded-lg border bg-white px-3 py-2 text-xs file:mr-3 file:border-0 file:bg-transparent file:font-medium"
              name="source"
              required
              type="file"
            />
          </label>
          <Button disabled={busy !== null} type="submit">
            <Upload aria-hidden="true" />
            {busy === "upload" ? "Queueing…" : "Upload"}
          </Button>
        </form>

        <div className="border-t pt-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Processing history</h3>
            <span className="text-xs text-muted-foreground">{jobs.length} upload{jobs.length === 1 ? "" : "s"}</span>
          </div>
          {jobs.length ? (
            <ul className="divide-y rounded-lg border">
              {jobs.map((job) => (
                <li className="flex items-center gap-3 px-3 py-3" key={job.id}>
                  <JobIcon status={job.status} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{job.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {job.status === "succeeded"
                        ? `${job.result?.chunk_count ?? 0} chunks · ${job.result?.region_count ?? 0} page regions`
                        : job.error_message ?? formatStatus(job.status)}
                    </p>
                  </div>
                  {job.status === "failed" ? (
                    <Button
                      disabled={busy !== null}
                      size="sm"
                      variant="outline"
                      onClick={() => onRetry(job)}
                    >
                      <RotateCcw aria-hidden="true" /> Retry
                    </Button>
                  ) : null}
                  {job.status === "pending" || job.status === "running" ? (
                    <Button
                      disabled={busy !== null}
                      size="icon"
                      variant="ghost"
                      aria-label={`Cancel ${job.title}`}
                      onClick={() => onCancel(job)}
                    >
                      <X aria-hidden="true" />
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
              No course evidence has been uploaded.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function ReleaseCard({
  busy,
  onboardingReady,
  profileReady,
  preflight,
  release,
  sourceCount,
  onCreateDraft,
  onPreflight,
  onPublish,
  onOpenSetup,
}: {
  busy: string | null
  onboardingReady: boolean
  profileReady: boolean
  preflight: ReleasePreflightResult | null
  release: ProfessorReleaseSummary | null
  sourceCount: number
  onCreateDraft: () => void
  onPreflight: (release: ProfessorReleaseSummary) => void
  onPublish: (release: ProfessorReleaseSummary) => void
  onOpenSetup: () => void
}) {
  const publishedRelease = release?.status === "published"
  const draftRelease = release?.status === "draft"
  return (
    <Card>
      <CardHeader>
        <CardTitle>{publishedRelease ? "Current release and next draft" : "Release"}</CardTitle>
        <CardDescription>
          {publishedRelease
            ? "Students keep using the current published release while you prepare the next reviewed version."
            : "A release freezes the reviewed tutor policy and all currently successful evidence uploads."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="mb-2 text-xs font-semibold text-muted-foreground">
            {publishedRelease ? "Next release readiness" : "Release readiness"}
          </p>
          <ol className={cn("grid gap-2", publishedRelease ? "sm:grid-cols-3" : "sm:grid-cols-4")}>
          <ReleaseStep done={onboardingReady} label="Tutor approved" />
          <ReleaseStep done={profileReady} label="Profile approved" />
          <ReleaseStep done={sourceCount > 0} label="Evidence ready" />
          {!publishedRelease ? (
            <ReleaseStep done={Boolean(draftRelease && release?.evaluation_status === "passed")} label="Checks passed" />
          ) : null}
          </ol>
        </div>

        {!onboardingReady ? (
          <Alert>
            <CircleAlert />
            <AlertTitle>{publishedRelease ? "The next release draft is blocked" : "The first release is blocked"}</AlertTitle>
            <AlertDescription>
              {publishedRelease
                ? "The current published release remains active. Complete the new policy, preview, and approval checklist before creating its successor."
                : "Resolve the policy, preview, and approval checklist before creating a release."}
            </AlertDescription>
          </Alert>
        ) : null}

        {release ? (
          <div className="rounded-lg border bg-muted/30 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold">
                  {publishedRelease ? "Current published release" : "Draft release"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {release.chunk_count} chunks · policy v{release.policy_version}
                </p>
              </div>
              <div className="flex gap-2">
                <Badge variant="outline">{formatStatus(release.evaluation_status)}</Badge>
                <Badge>{formatStatus(release.status)}</Badge>
              </div>
            </div>
          </div>
        ) : null}

        {preflight ? (
          <ul className="divide-y rounded-lg border">
            {preflight.checks.map((check) => (
              <li className="flex items-start gap-3 px-3 py-3" key={check.id}>
                {check.passed ? (
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[var(--success)]" aria-hidden="true" />
                ) : (
                  <CircleAlert className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden="true" />
                )}
                <div>
                  <p className="text-sm font-medium">{check.label}</p>
                  <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{check.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="flex flex-wrap gap-2 border-t pt-4">
          {!onboardingReady ? (
            <Button variant="outline" onClick={onOpenSetup}>Review tutor setup</Button>
          ) : null}
          {(!release || release.status !== "draft") && onboardingReady ? (
            <Button
              disabled={busy !== null || sourceCount === 0 || !profileReady}
              onClick={onCreateDraft}
            >
              <Plus aria-hidden="true" />
              {busy === "create-draft" ? "Creating…" : "Create release draft"}
            </Button>
          ) : null}
          {release?.status === "draft" ? (
            <Button disabled={busy !== null} variant="outline" onClick={() => onPreflight(release)}>
              <RefreshCw aria-hidden="true" />
              {busy === "preflight" ? "Checking…" : "Run release checks"}
            </Button>
          ) : null}
          {release?.status === "draft" && release.evaluation_status === "passed" ? (
            <Button disabled={busy !== null} onClick={() => onPublish(release)}>
              <PackageCheck aria-hidden="true" />
              {busy === "publish" ? "Publishing…" : "Publish to students"}
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

function ReleaseStep({ done, label }: { done: boolean; label: string }) {
  return (
    <li className={cn("flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium", done ? "bg-[var(--success-soft)] text-[var(--success)]" : "bg-muted text-muted-foreground")}>
      {done ? <Check className="size-3.5" aria-hidden="true" /> : <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />}
      {label}
    </li>
  )
}

function JobIcon({ status }: { status: ProfessorIngestionJob["status"] }) {
  if (status === "succeeded") {
    return <CheckCircle2 className="size-4 shrink-0 text-[var(--success)]" aria-label="Succeeded" />
  }
  if (status === "failed" || status === "cancelled") {
    return <CircleAlert className="size-4 shrink-0 text-destructive" aria-label={formatStatus(status)} />
  }
  return <LoaderCircle className="size-4 shrink-0 animate-spin text-[var(--accent-strong)]" aria-label={formatStatus(status)} />
}

function Field({ label, ...props }: { label: string } & React.ComponentProps<"input">) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium">{label}</span>
      <input
        className="h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]"
        required
        {...props}
      />
    </label>
  )
}

function artifactId(filename: string): string {
  const stem = filename.replace(/\.pdf$/i, "").toLowerCase()
  const slug = stem.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")
  return `${slug || "course-source"}-${Date.now()}`
}

function formatStatus(value: string): string {
  const label = value.replaceAll("_", " ").replaceAll("-", " ")
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`
}

function message(reason: unknown): string {
  return reason instanceof Error ? reason.message : "The request failed. Please try again."
}
