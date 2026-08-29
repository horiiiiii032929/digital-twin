import { useCallback, useEffect, useState, type FormEvent } from "react"
import { BellRing, BrainCircuit, CheckCircle2, LoaderCircle, ShieldCheck, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  approveProfessorTeachingProfile,
  cancelProfessorProactiveTrigger,
  createProfessorTeachingProfile,
  listProfessorLearningGaps,
  listProfessorProactiveTriggers,
  listProfessorTeachingProfiles,
  previewProfessorTeachingProfile,
  scheduleProfessorProactiveTrigger,
} from "@/lib/api/professor"
import type {
  ProfessorCourse,
  ProfessorLearningGapResult,
  ProfessorProactiveTrigger,
  ProfessorTeachingProfile,
} from "@/lib/api/types"

export function ProfessorAutonomyPanel({
  course,
  releaseId,
  evidenceChunks,
  onApprovedProfileChange,
}: {
  course: ProfessorCourse
  releaseId?: string
  evidenceChunks: Array<{ id: string; label: string }>
  onApprovedProfileChange: (profileId: string | null) => void
}) {
  const [profiles, setProfiles] = useState<ProfessorTeachingProfile[]>([])
  const [triggers, setTriggers] = useState<ProfessorProactiveTrigger[]>([])
  const [learningGaps, setLearningGaps] = useState<ProfessorLearningGapResult | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const [nextProfiles, nextTriggers, nextGaps] = await Promise.all([
      listProfessorTeachingProfiles(course.course_id),
      listProfessorProactiveTriggers(course.course_id),
      releaseId
        ? listProfessorLearningGaps(course.course_id, releaseId)
        : Promise.resolve(null),
    ])
    setProfiles(nextProfiles)
    setTriggers(nextTriggers)
    setLearningGaps(nextGaps)
    onApprovedProfileChange(
      nextProfiles.find((profile) => profile.status === "approved")?.profile_id ?? null,
    )
  }, [course.course_id, onApprovedProfileChange, releaseId])

  useEffect(() => {
    let active = true
    void refresh().catch((reason) => {
      if (active) setError(message(reason))
    })
    return () => {
      active = false
    }
  }, [refresh])

  async function run(key: string, action: () => Promise<void>) {
    setBusy(key)
    setError(null)
    try {
      await action()
    } catch (reason) {
      setError(message(reason))
    } finally {
      setBusy(null)
    }
  }

  async function createProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    await run("profile", async () => {
      await createProfessorTeachingProfile(course.course_id, {
        tone: text(data, "tone"),
        depth: text(data, "depth") as "concise" | "balanced" | "detailed",
        explanation_structure: list(data, "explanation_structure"),
        example_preferences: list(data, "example_preferences"),
        misconception_handling: text(data, "misconception_handling"),
        integrity_limits: text(data, "integrity_limits"),
        help_ladder: list(data, "help_ladder"),
        outreach_policy: text(data, "outreach_policy"),
      })
      await refresh()
    })
  }

  async function approve(profile: ProfessorTeachingProfile) {
    await run(`approve-${profile.profile_id}`, async () => {
      const preview = await previewProfessorTeachingProfile(
        course.course_id,
        profile.profile_id,
      )
      await approveProfessorTeachingProfile(
        course.course_id,
        profile.profile_id,
        preview.preview_sha256,
      )
      await refresh()
    })
  }

  async function schedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    await run("schedule", async () => {
      await scheduleProfessorProactiveTrigger(course.course_id, {
        student_account_id: text(data, "student_account_id"),
        scheduled_for: new Date(text(data, "scheduled_for")).toISOString(),
        expires_at: new Date(text(data, "expires_at")).toISOString(),
        topic: text(data, "topic"),
        prompt: text(data, "prompt"),
        source_chunk_id: text(data, "source_chunk_id"),
      })
      form.reset()
      await refresh()
    })
  }

  const approved = profiles.find((profile) => profile.status === "approved")
  const draft = profiles.find((profile) => profile.status === "draft")

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BrainCircuit className="size-4" aria-hidden="true" /> Autonomous tutor controls
        </CardTitle>
        <CardDescription>
          Approve teaching behavior, inspect privacy-safe learning signals, and schedule consent-gated in-app support.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <section className="space-y-3" aria-labelledby="teaching-profile-heading">
          <div className="flex items-center justify-between gap-3">
            <h3 id="teaching-profile-heading" className="text-sm font-semibold">Professor teaching profile</h3>
            <Badge variant={approved ? "default" : "outline"}>
              {approved ? `Approved v${approved.version}` : "Approval required"}
            </Badge>
          </div>
          {draft ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-3">
              <div>
                <p className="text-sm font-medium">Draft v{draft.version}: {draft.tone}</p>
                <p className="mt-1 text-xs text-muted-foreground">Approval binds the exact ten-case preview and content hash.</p>
              </div>
              <Button disabled={busy !== null} onClick={() => void approve(draft)}>
                <ShieldCheck aria-hidden="true" />
                {busy === `approve-${draft.profile_id}` ? "Approving…" : "Preview and approve"}
              </Button>
            </div>
          ) : (
            <form className="grid gap-3 sm:grid-cols-2" onSubmit={createProfile}>
              <p className="sm:col-span-2 text-xs text-muted-foreground">
                {approved
                  ? "Edit the approved settings below to create a new reviewable version. The active release remains unchanged until the new version is approved."
                  : "Define the teaching behavior that the professor will review before it can be attached to a release."}
              </p>
              <Input label="Tone" name="tone" defaultValue={approved?.tone ?? "Encouraging, precise, and concise"} />
              <Select label="Depth" name="depth" options={["concise", "balanced", "detailed"]} defaultValue={approved?.depth ?? "balanced"} />
              <Input label="Explanation structure" name="explanation_structure" defaultValue={approved?.explanation_structure.join(", ") ?? "Concept, Example, Check understanding"} />
              <Input label="Example preferences" name="example_preferences" defaultValue={approved?.example_preferences.join(", ") ?? "Small worked example, Course terminology"} />
              <Input label="Misconception handling" name="misconception_handling" defaultValue={approved?.misconception_handling ?? "Name the misconception, contrast it with evidence, then check understanding."} />
              <Input label="Integrity limits" name="integrity_limits" defaultValue={approved?.integrity_limits ?? "Use attempt-first hints for assessed work; never provide a submission."} />
              <Input label="Help ladder" name="help_ladder" defaultValue={approved?.help_ladder.join(", ") ?? "Focused hint, Analogous example, Full explanation"} />
              <Input label="Outreach policy" name="outreach_policy" defaultValue={approved?.outreach_policy ?? "Only send professor-scheduled, cited prompts to opted-in students."} />
              <Button className="sm:col-span-2" disabled={busy !== null} type="submit">
                {busy === "profile" ? <LoaderCircle className="animate-spin" /> : <ShieldCheck />}
                {approved ? "Create updated draft" : "Create reviewable profile"}
              </Button>
            </form>
          )}
        </section>

        <section className="space-y-3 border-t pt-5" aria-labelledby="learning-gap-heading">
          <div className="flex items-center justify-between gap-3">
            <h3 id="learning-gap-heading" className="text-sm font-semibold">Learning-gap insights</h3>
            <span className="text-xs text-muted-foreground">Minimum 5 learners</span>
          </div>
          {learningGaps?.aggregation.visible_aggregates.length ? (
            <ul className="grid gap-2 sm:grid-cols-2">
              {learningGaps.aggregation.visible_aggregates.map((gap) => (
                <li key={gap.aggregate_id} className="rounded-lg border px-3 py-3">
                  <p className="text-sm font-medium">{format(gap.signal_kind)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{gap.distinct_learners} learners · {gap.signal_count} signals</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-lg border border-dashed px-4 py-4 text-sm text-muted-foreground">
              {learningGaps?.aggregation.suppressed_group_count
                ? "Small cohorts are suppressed until the privacy threshold is met."
                : "No privacy-safe aggregate is available yet."}
            </p>
          )}
        </section>

        <section className="space-y-3 border-t pt-5" aria-labelledby="outreach-heading">
          <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h3 id="outreach-heading" className="flex items-center gap-2 text-sm font-semibold"><BellRing className="size-4" /> Scheduled in-app outreach</h3>
            <Badge variant="outline">A1 automatic outreach remains shadow-only</Badge>
          </div>
          <form className="grid gap-3 sm:grid-cols-2" onSubmit={schedule}>
            <Select label="Student" name="student_account_id" options={course.student_account_ids} />
            <Select label="Evidence" name="source_chunk_id" options={evidenceChunks.map((item) => item.id)} />
            <Input label="Send at" name="scheduled_for" type="datetime-local" />
            <Input label="Expires at" name="expires_at" type="datetime-local" />
            <Input label="Topic" name="topic" placeholder="Review cache coherence" />
            <Input label="Prompt" name="prompt" placeholder="Explain the key invariant in your own words." />
            <Button className="sm:col-span-2" disabled={busy !== null || !approved || !course.student_account_ids.length || !evidenceChunks.length} type="submit">
              <BellRing /> {busy === "schedule" ? "Scheduling…" : "Schedule cited prompt"}
            </Button>
          </form>
          {triggers.length ? (
            <ul className="divide-y rounded-lg border">
              {triggers.map((trigger) => (
                <li key={trigger.id} className="flex items-center gap-3 px-3 py-3">
                  <CheckCircle2 className="size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{trigger.topic}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{format(trigger.status)} · {new Date(trigger.scheduled_for).toLocaleString()}</p>
                  </div>
                  {trigger.status === "pending" ? (
                    <Button size="icon" variant="ghost" aria-label={`Cancel ${trigger.topic}`} disabled={busy !== null} onClick={() => void run(`cancel-${trigger.id}`, async () => {
                      await cancelProfessorProactiveTrigger(course.course_id, trigger.id)
                      await refresh()
                    })}><X /></Button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </CardContent>
    </Card>
  )
}

function Input({ label, ...props }: { label: string } & React.ComponentProps<"input">) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span><input className="h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]" required {...props} /></label>
}

function Select({ label, name, options, defaultValue = "" }: { label: string; name: string; options: string[]; defaultValue?: string }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span><select className="h-10 w-full rounded-lg border bg-white px-3 text-sm" name={name} required defaultValue={defaultValue}><option value="" disabled>Select…</option>{options.map((option) => <option key={option} value={option}>{format(option)}</option>)}</select></label>
}

function text(data: FormData, name: string): string {
  return String(data.get(name) ?? "").trim()
}

function list(data: FormData, name: string): string[] {
  return text(data, name).split(",").map((item) => item.trim()).filter(Boolean)
}

function format(value: string): string {
  const label = value.replaceAll("_", " ").replaceAll("-", " ")
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`
}

function message(reason: unknown): string {
  return reason instanceof Error ? reason.message : "The request failed. Please try again."
}
