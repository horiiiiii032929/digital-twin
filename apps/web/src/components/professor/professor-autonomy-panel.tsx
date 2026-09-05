import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react"
import {
  Activity,
  BellRing,
  BookOpenText,
  BrainCircuit,
  Check,
  CheckCircle2,
  Eye,
  LoaderCircle,
  Pause,
  Power,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  RotateCcw,
  Target,
  UsersRound,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  approveProfessorTeachingProfile,
  cancelProfessorAutonomousGoal,
  cancelProfessorProactiveTrigger,
  createProfessorAutonomousGoal,
  createProfessorCourseDomainModel,
  createProfessorTeachingProfile,
  getProfessorAutonomyPolicy,
  getProfessorCourseDomainModel,
  getProfessorTutoringRuntimeProfile,
  listProfessorAutonomousActions,
  listProfessorAutonomousGoals,
  listProfessorAutonomousOutcomes,
  listProfessorAutonomyTraces,
  listProfessorAutonomyRecipients,
  listProfessorLearningGaps,
  listProfessorLearnerBeliefEvidence,
  listProfessorProactiveTriggers,
  listProfessorTeachingProfiles,
  previewProfessorTeachingProfile,
  scheduleProfessorProactiveTrigger,
  updateProfessorAutonomyPolicy,
  updateProfessorTutoringRuntimeProfile,
} from "@/lib/api/professor"
import type {
  AutonomousActionKind,
  AutonomousActionV1,
  AutonomousGoalV1,
  AutonomousOutcomeV1,
  AutonomousRecipientEligibilityV1,
  AgentTraceV2,
  CourseDomainModelV1,
  CourseTutoringMode,
  CourseTutoringRuntimeProfileV1,
  PedagogicalPolicyV2,
  ProfessorCourse,
  ProfessorLearningGapResult,
  ProfessorLearnerBeliefEvidence,
  ProfessorEvidenceChunkOption,
  ProfessorProactiveTrigger,
  ProfessorTeachingProfile,
  ProfessorTeachingProfilePreview,
} from "@/lib/api/types"
import { cn } from "@/lib/utils"

import { canApproveTeachingProfilePreview } from "./governance-approval"

type GovernanceView = "overview" | "boundary" | "learners" | "outreach" | "activity"
type PolicyStateAction = "activate" | "pause" | "kill"

export function ProfessorAutonomyPanel({
  course,
  releaseId,
  evidenceChunks,
  onApprovedProfileChange,
}: {
  course: ProfessorCourse
  releaseId?: string
  evidenceChunks: ProfessorEvidenceChunkOption[]
  onApprovedProfileChange: (profileId: string | null) => void
}) {
  const [view, setView] = useState<GovernanceView>("overview")
  const [profiles, setProfiles] = useState<ProfessorTeachingProfile[]>([])
  const [profilePreview, setProfilePreview] = useState<ProfessorTeachingProfilePreview | null>(null)
  const [triggers, setTriggers] = useState<ProfessorProactiveTrigger[]>([])
  const [policy, setPolicy] = useState<PedagogicalPolicyV2 | null>(null)
  const [goals, setGoals] = useState<AutonomousGoalV1[]>([])
  const [actions, setActions] = useState<AutonomousActionV1[]>([])
  const [outcomes, setOutcomes] = useState<AutonomousOutcomeV1[]>([])
  const [recipients, setRecipients] = useState<AutonomousRecipientEligibilityV1[]>([])
  const [learningGaps, setLearningGaps] = useState<ProfessorLearningGapResult | null>(null)
  const [domainModel, setDomainModel] = useState<CourseDomainModelV1 | null>(null)
  const [runtimeProfile, setRuntimeProfile] = useState<CourseTutoringRuntimeProfileV1 | null>(null)
  const [learnerEvidence, setLearnerEvidence] = useState<ProfessorLearnerBeliefEvidence[]>([])
  const [traces, setTraces] = useState<AgentTraceV2[]>([])
  const [editingPolicy, setEditingPolicy] = useState(false)
  const [pendingPolicyAction, setPendingPolicyAction] = useState<PolicyStateAction | null>(null)
  const [pendingTriggerCancel, setPendingTriggerCancel] = useState<string | null>(null)
  const [pendingGoalCancel, setPendingGoalCancel] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const refreshSequence = useRef(0)

  const refresh = useCallback(async () => {
    const sequence = ++refreshSequence.current
    const [nextProfiles, nextTriggers, nextGaps, nextPolicy, nextGoals, nextActions, nextOutcomes, nextRecipients, nextDomainModel, nextRuntimeProfile, nextLearnerEvidence, nextTraces] = await Promise.all([
      listProfessorTeachingProfiles(course.course_id),
      listProfessorProactiveTriggers(course.course_id),
      releaseId ? listProfessorLearningGaps(course.course_id, releaseId) : Promise.resolve(null),
      getProfessorAutonomyPolicy(course.course_id),
      listProfessorAutonomousGoals(course.course_id),
      listProfessorAutonomousActions(course.course_id),
      listProfessorAutonomousOutcomes(course.course_id),
      listProfessorAutonomyRecipients(course.course_id),
      releaseId
        ? getProfessorCourseDomainModel(course.course_id, releaseId)
        : Promise.resolve(null),
      getProfessorTutoringRuntimeProfile(course.course_id),
      listProfessorLearnerBeliefEvidence(course.course_id),
      listProfessorAutonomyTraces(course.course_id),
    ])
    if (sequence !== refreshSequence.current) return
    setProfiles(nextProfiles)
    setTriggers(nextTriggers)
    setLearningGaps(nextGaps)
    setPolicy(nextPolicy)
    setGoals(nextGoals)
    setActions(nextActions)
    setOutcomes(nextOutcomes)
    setRecipients(nextRecipients)
    setDomainModel(nextDomainModel)
    setRuntimeProfile(nextRuntimeProfile)
    setLearnerEvidence(nextLearnerEvidence)
    setTraces(nextTraces)
    onApprovedProfileChange(nextProfiles.find((profile) => profile.status === "approved")?.profile_id ?? null)
  }, [course.course_id, onApprovedProfileChange, releaseId])

  useEffect(() => {
    let active = true
    setProfilePreview(null)
    setPendingPolicyAction(null)
    setPendingTriggerCancel(null)
    setPendingGoalCancel(null)
    void refresh().catch((reason) => {
      if (active) setError(message(reason))
    })
    return () => {
      active = false
      refreshSequence.current += 1
    }
  }, [refresh])

  async function run(key: string, action: () => Promise<void>, success?: string) {
    setBusy(key)
    setError(null)
    setNotice(null)
    try {
      await action()
      if (success) setNotice(success)
    } catch (reason) {
      setError(message(reason))
    } finally {
      setBusy(null)
    }
  }

  async function createProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
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
      setProfilePreview(null)
      await refresh()
    }, "Draft profile created. Review its ten behavior cases before approval.")
  }

  async function createDomainModel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!releaseId) return
    const form = event.currentTarget
    const data = new FormData(form)
    const evidence = evidenceChunks.find((item) => item.id === text(data, "evidence_id"))
    if (!evidence) {
      setError("Select one current release evidence range for the concept.")
      return
    }
    const conceptId = stableId(text(data, "concept_label"))
    const objectiveId = stableId(text(data, "objective_statement"))
    const misconception = text(data, "misconception")
    await run("domain-model", async () => {
      await createProfessorCourseDomainModel(course.course_id, {
        release_id: releaseId,
        version: 1,
        objectives: [{
          objective_id: `objective-${objectiveId}`,
          statement: text(data, "objective_statement"),
          concept_ids: [`concept-${conceptId}`],
        }],
        concepts: [{
          concept_id: `concept-${conceptId}`,
          label: text(data, "concept_label"),
          description: text(data, "concept_description"),
          prerequisite_concept_ids: [],
          canonical_ranges: [{
            source_artifact_id: evidence.source_artifact_id,
            source_version: evidence.source_version,
            source_sha256: evidence.source_sha256,
            locator: evidence.locator,
            char_start: evidence.char_start,
            char_end: evidence.char_end,
          }],
        }],
        misconceptions: misconception ? [{
          misconception_id: `misconception-${stableId(misconception)}`,
          concept_id: `concept-${conceptId}`,
          description: misconception,
          diagnostic_cues: list(data, "diagnostic_cues").length
            ? list(data, "diagnostic_cues")
            : [misconception],
        }] : [],
      })
      form.reset()
      await refresh()
    }, "The release-bound course model is approved and immutable.")
  }

  async function setRuntimeMode(mode: CourseTutoringMode) {
    const reason = mode === "grounded-assistant"
      ? "Professor initiated immediate T0 safety rollback."
      : mode === "bounded-tutoring-graph"
        ? "Professor selected the historical bounded T1 control."
        : "Professor selected governed T1-v2 inside the approved policy."
    await run("runtime-mode", async () => {
      await updateProfessorTutoringRuntimeProfile(course.course_id, mode, reason)
      await refresh()
    }, mode === "grounded-assistant"
      ? "T0 rollback is active and pending autonomous work was cancelled."
      : "The course tutoring runtime has been updated.")
  }

  async function preparePreview(profile: ProfessorTeachingProfile) {
    await run(`preview-${profile.profile_id}`, async () => {
      setProfilePreview(await previewProfessorTeachingProfile(course.course_id, profile.profile_id))
    }, "Preview loaded. Approval remains blocked until you review the displayed cases.")
  }

  async function approveDisplayedPreview(profile: ProfessorTeachingProfile) {
    if (!canApproveTeachingProfilePreview(profile.profile_id, profilePreview)) return
    await run(`approve-${profile.profile_id}`, async () => {
      await approveProfessorTeachingProfile(course.course_id, profile.profile_id, profilePreview.preview_sha256)
      setProfilePreview(null)
      await refresh()
    }, "Teaching profile approved and bound to the reviewed preview hash.")
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
    }, "The cited in-app check-in has been scheduled.")
  }

  async function savePolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const selectedActions = data.getAll("allowed_actions").map(String) as AutonomousActionKind[]
    if (!selectedActions.length) {
      setError("Select at least one permitted tutoring action.")
      return
    }
    await run("policy", async () => {
      await updateProfessorAutonomyPolicy(course.course_id, {
        approved_course_objectives: list(data, "approved_course_objectives"),
        allowed_actions: [...new Set([...selectedActions, "no-action" as const])],
        autonomy_enabled: policy?.autonomy_enabled ?? data.get("autonomy_enabled") === "on",
        paused: policy?.paused ?? false,
        kill_switch: policy?.kill_switch ?? false,
      })
      setEditingPolicy(false)
      await refresh()
    }, "The autonomy boundary has been saved as a new immutable policy version.")
  }

  async function confirmPolicyState() {
    if (!policy || !pendingPolicyAction) return
    const action = pendingPolicyAction
    await run("policy-state", async () => {
      const state = action === "activate"
        ? { autonomy_enabled: true, paused: false, kill_switch: false }
        : action === "pause"
          ? { autonomy_enabled: true, paused: true, kill_switch: false }
          : { autonomy_enabled: false, paused: false, kill_switch: true }
      await updateProfessorAutonomyPolicy(course.course_id, {
        approved_course_objectives: policy.approved_course_objectives,
        allowed_actions: policy.allowed_actions,
        ...state,
      })
      setPendingPolicyAction(null)
      await refresh()
    }, policyActionSuccess(action))
  }

  async function createGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    await run("goal", async () => {
      await createProfessorAutonomousGoal(course.course_id, {
        student_account_id: text(data, "student_account_id"),
        approved_course_objective: text(data, "approved_course_objective"),
        learner_subgoal: text(data, "learner_subgoal"),
        success_condition: text(data, "success_condition"),
        expires_at: new Date(text(data, "expires_at")).toISOString(),
      })
      form.reset()
      await refresh()
    }, "A bounded learner goal has been created inside the approved course objective.")
  }

  const approved = profiles.find((profile) => profile.status === "approved")
  const draft = profiles.find((profile) => profile.status === "draft")
  const activeGoals = goals.filter((goal) => goal.status === "active")
  const pendingTriggers = triggers.filter((trigger) => trigger.status === "pending")
  const deliveredActions = actions.filter((action) => action.status === "delivered")
  const policyStatus = policy?.kill_switch ? "Stopped" : policy?.paused ? "Paused" : policy?.autonomy_enabled ? "Active" : "Off"
  const blockers = useMemo(() => [
    !approved ? "Approve the professor teaching profile" : null,
    !policy ? "Define the autonomy boundary" : null,
    policy && !policy.autonomy_enabled ? "Activate the approved autonomy policy" : null,
    !releaseId ? "Publish a release with approved evidence" : null,
  ].filter((item): item is string => item !== null), [approved, policy, releaseId])

  return (
    <Card className="workspace-card overflow-hidden rounded-2xl">
      <CardHeader className="border-b bg-white pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="workspace-kicker">Digital Twin control room</p>
            <CardTitle className="mt-1 flex items-center gap-2 text-lg"><BrainCircuit className="size-4" aria-hidden="true" /> Governed autonomous tutor</CardTitle>
            <CardDescription className="mt-1 max-w-2xl">Approve its teaching boundary, activate bounded autonomy, and inspect every learner-facing decision.</CardDescription>
          </div>
          <Badge variant="outline">R1.2 local release</Badge>
        </div>

        <dl className="mt-5 grid grid-cols-2 overflow-hidden rounded-xl bg-[var(--shell)] sm:grid-cols-4">
          <SummaryItem label="Profile" value={approved ? `Approved v${approved.version}` : "Needs review"} ready={Boolean(approved)} />
          <SummaryItem label="Autonomy" value={policyStatus} ready={policyStatus === "Active"} />
          <SummaryItem label="Active goals" value={`${activeGoals.length}`} ready={activeGoals.length > 0} />
          <SummaryItem label="Delivered actions" value={`${deliveredActions.length}`} ready={deliveredActions.length > 0} />
        </dl>

        <nav className="mt-2 grid grid-cols-2 gap-1 rounded-xl bg-[var(--shell)] p-1 sm:flex" aria-label="Tutor governance views" role="tablist">
          {GOVERNANCE_VIEWS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              aria-controls={`governance-${item.id}`}
              className={cn(
                "rounded-lg px-3 py-2 text-left text-xs font-semibold transition-colors sm:shrink-0 sm:text-center",
                view === item.id
                  ? "bg-white text-foreground shadow-[0_1px_3px_rgba(25,25,29,0.08)]"
                  : "text-muted-foreground hover:bg-white/60 hover:text-foreground",
              )}
              onClick={() => setView(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </CardHeader>

      <CardContent className="p-0">
        <div className="space-y-3 px-4 pt-4 sm:px-5">
          {error ? <Alert variant="destructive" role="alert"><ShieldAlert aria-hidden="true" /><AlertTitle>Governance action failed</AlertTitle><AlertDescription>{error}</AlertDescription></Alert> : null}
          {notice ? <Alert className="border-[var(--success-border)] bg-[var(--success-soft)]" role="status" aria-live="polite"><CheckCircle2 className="text-[var(--success)]" aria-hidden="true" /><AlertDescription className="text-[var(--success)]">{notice}</AlertDescription></Alert> : null}
        </div>

        <div id={`governance-${view}`} role="tabpanel" className="p-4 sm:p-5">
          {view === "overview" ? <Overview actions={actions} blockers={blockers} policy={policy} pendingTriggers={pendingTriggers.length} onNavigate={setView} /> : null}
          {view === "boundary" ? (
            <div className="space-y-7">
              <DomainModelSection
                busy={busy}
                domainModel={domainModel}
                evidenceChunks={evidenceChunks}
                releaseReady={Boolean(releaseId)}
                onCreate={createDomainModel}
              />
              <TeachingProfileSection approved={approved} busy={busy} draft={draft} preview={profilePreview} onApprove={approveDisplayedPreview} onCreate={createProfile} onDismissPreview={() => setProfilePreview(null)} onPreview={preparePreview} />
              <PolicySection busy={busy} editing={editingPolicy} pendingAction={pendingPolicyAction} policy={policy} approvedProfile={Boolean(approved)} onCancelAction={() => setPendingPolicyAction(null)} onConfirmAction={() => void confirmPolicyState()} onEdit={() => setEditingPolicy(true)} onRequestAction={setPendingPolicyAction} onSave={savePolicy} />
              <RuntimeModeSection
                busy={busy}
                domainModel={domainModel}
                policy={policy}
                profile={runtimeProfile}
                onSelect={(mode) => void setRuntimeMode(mode)}
              />
            </div>
          ) : null}
          {view === "learners" ? (
            <LearnersSection
              busy={busy}
              goals={goals}
              learningGaps={learningGaps}
              learnerEvidence={learnerEvidence}
              pendingCancel={pendingGoalCancel}
              policy={policy}
              recipients={recipients}
              onCancelRequest={setPendingGoalCancel}
              onCancelGoal={(goal) => void run(`cancel-goal-${goal.goal_id}`, async () => {
                await cancelProfessorAutonomousGoal(course.course_id, goal.goal_id)
                setPendingGoalCancel(null)
                await refresh()
              }, "The learner goal and all pending work derived from it were cancelled.")}
              onCreateGoal={createGoal}
            />
          ) : null}
          {view === "outreach" ? (
            <OutreachSection
              approved={Boolean(approved)}
              busy={busy}
              evidenceChunks={evidenceChunks}
              pendingCancel={pendingTriggerCancel}
              policy={policy}
              recipients={recipients}
              triggers={triggers}
              onCancelRequest={setPendingTriggerCancel}
              onCancelTrigger={(trigger) => void run(`cancel-${trigger.id}`, async () => {
                await cancelProfessorProactiveTrigger(course.course_id, trigger.id)
                setPendingTriggerCancel(null)
                await refresh()
              }, "The pending check-in was cancelled.")}
              onSchedule={schedule}
            />
          ) : null}
          {view === "activity" ? <ActivitySection actions={actions} outcomes={outcomes} traces={traces} /> : null}
        </div>
      </CardContent>
    </Card>
  )
}

function Overview({ actions, blockers, policy, pendingTriggers, onNavigate }: { actions: AutonomousActionV1[]; blockers: string[]; policy: PedagogicalPolicyV2 | null; pendingTriggers: number; onNavigate: (view: GovernanceView) => void }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="space-y-6">
        <section aria-labelledby="operating-boundary-heading">
          <div className="flex items-start justify-between gap-4">
            <div><h3 id="operating-boundary-heading" className="text-sm font-semibold">Current operating boundary</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">Deterministic checks retain authority over identity, consent, course scope, evidence, citations, frequency, and delivery.</p></div>
            <Button size="sm" variant="outline" onClick={() => onNavigate("boundary")}><Settings2 aria-hidden="true" /> Review boundary</Button>
          </div>
          <ul className="mt-4 divide-y rounded-lg border">
            <BoundaryRow done={Boolean(policy)} label="Professor-approved course objectives and action permissions" />
            <BoundaryRow done={Boolean(policy?.autonomy_enabled && !policy.paused && !policy.kill_switch)} label="Autonomy is active inside the approved policy" />
            <BoundaryRow done label="Student consent and valid source lineage are checked before delivery" />
            <BoundaryRow done label="A0 scheduled outreach is available; A2 remains a development candidate" />
          </ul>
        </section>
        <section aria-labelledby="recent-autonomy-heading">
          <div className="flex items-center justify-between gap-3"><h3 id="recent-autonomy-heading" className="text-sm font-semibold">Recent autonomous activity</h3><Button size="sm" variant="ghost" onClick={() => onNavigate("activity")}>Open audit</Button></div>
          {actions.length ? (
            <ul className="mt-3 divide-y rounded-lg border">{actions.slice(0, 4).map((action) => <li key={action.action_id} className="flex items-start justify-between gap-4 px-3 py-3"><div className="min-w-0"><p className="text-sm font-medium">{format(action.kind)}</p><p className="mt-1 truncate text-xs text-muted-foreground">{action.structured_reason}</p></div><Badge variant="outline">{format(action.status)}</Badge></li>)}</ul>
          ) : <EmptyState icon={Activity} title="No autonomous decisions yet" description="Decisions will appear here after the bounded worker evaluates an eligible event." />}
        </section>
      </div>
      <aside className="rounded-xl border bg-[var(--shell)] p-4" aria-labelledby="readiness-heading">
        <h3 id="readiness-heading" className="text-sm font-semibold">Readiness</h3>
        {blockers.length ? <><p className="mt-1 text-xs leading-5 text-muted-foreground">Complete these before the candidate can contact students autonomously.</p><ol className="mt-4 space-y-3">{blockers.map((blocker, index) => <li key={blocker} className="flex gap-2.5 text-sm"><span className="flex size-5 shrink-0 items-center justify-center rounded-full border bg-white text-xs font-semibold">{index + 1}</span><span>{blocker}</span></li>)}</ol></> : <p className="mt-2 text-sm leading-6 text-[var(--success)]">All configuration prerequisites are present. Evaluation status still controls promotion.</p>}
        <div className="mt-5 border-t pt-4"><p className="text-xs font-semibold text-muted-foreground">Scheduled check-ins</p><p className="mt-1 text-2xl font-semibold tracking-tight">{pendingTriggers}</p></div>
      </aside>
    </div>
  )
}

function DomainModelSection({ busy, domainModel, evidenceChunks, releaseReady, onCreate }: { busy: string | null; domainModel: CourseDomainModelV1 | null; evidenceChunks: ProfessorEvidenceChunkOption[]; releaseReady: boolean; onCreate: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  return (
    <section aria-labelledby="course-domain-heading">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 id="course-domain-heading" className="flex items-center gap-2 text-sm font-semibold"><BrainCircuit className="size-4" /> Course domain model</h3>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">Bind approved objectives and concepts to exact ranges in this release. The tutor may observe evidence, but it cannot invent the course model.</p>
        </div>
        <Badge variant={domainModel ? "default" : "outline"}>{domainModel ? `Approved v${domainModel.version}` : "Required for T1-v2"}</Badge>
      </div>
      {domainModel ? (
        <div className="mt-4 divide-y rounded-xl border">
          <div className="grid gap-4 px-4 py-3 sm:grid-cols-2">
            <div><p className="text-xs font-semibold text-muted-foreground">Objectives</p><ul className="mt-2 space-y-1.5 text-sm">{domainModel.objectives.map((item) => <li key={item.objective_id}>{item.statement}</li>)}</ul></div>
            <div><p className="text-xs font-semibold text-muted-foreground">Concepts and source ranges</p><ul className="mt-2 space-y-1.5 text-sm">{domainModel.concepts.map((item) => <li key={item.concept_id}>{item.label} <span className="text-xs text-muted-foreground">· {item.canonical_ranges.length} approved range{item.canonical_ranges.length === 1 ? "" : "s"}</span></li>)}</ul></div>
          </div>
          <p className="px-4 py-3 text-xs leading-5 text-muted-foreground">Pinned to release {domainModel.release_id}. Changes require a new release and a new approved model.</p>
        </div>
      ) : (
        <form className="mt-4 grid gap-4 rounded-xl border p-4 sm:grid-cols-2" onSubmit={onCreate}>
          <p className="sm:col-span-2 text-xs leading-5 text-muted-foreground">Create the first approved objective and concept. More complete course models should be prepared before publishing the next release.</p>
          <Input label="Course objective" name="objective_statement" placeholder="Explain how cache coherence preserves a shared view" />
          <Input label="Concept name" name="concept_label" placeholder="Cache coherence" />
          <TextArea label="Concept description" name="concept_description" placeholder="What the concept means inside this course" />
          <LabeledSelect label="Canonical evidence range" name="evidence_id" options={evidenceChunks.map((item) => ({ value: item.id, label: item.label }))} />
          <TextArea label="Known misconception (optional)" name="misconception" placeholder="An invalidation always removes the data immediately" required={false} />
          <TextArea label="Diagnostic cues (optional)" name="diagnostic_cues" placeholder="always removes, every cache updates at once" required={false} />
          <Button className="sm:col-span-2 sm:justify-self-end" disabled={busy !== null || !releaseReady || !evidenceChunks.length} type="submit"><ShieldCheck /> {busy === "domain-model" ? "Approving…" : "Approve release-bound model"}</Button>
        </form>
      )}
    </section>
  )
}

function RuntimeModeSection({ busy, domainModel, policy, profile, onSelect }: { busy: string | null; domainModel: CourseDomainModelV1 | null; policy: PedagogicalPolicyV2 | null; profile: CourseTutoringRuntimeProfileV1 | null; onSelect: (mode: CourseTutoringMode) => void }) {
  const current = profile?.mode ?? "server default"
  return (
    <section className="border-t pt-6" aria-labelledby="runtime-mode-heading">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><h3 id="runtime-mode-heading" className="flex items-center gap-2 text-sm font-semibold"><RotateCcw className="size-4" /> Tutor runtime and rollback</h3><p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">One course-level setting selects the active flow. T0 rollback cancels pending autonomous work and preserves the audit history.</p></div><Badge variant="outline">{format(current)}</Badge></div>
      <div className="mt-4 divide-y rounded-xl border">
        {RUNTIME_MODES.map((item) => {
          const selected = profile?.mode === item.mode
          const unavailable = item.mode === "governed-autonomous-tutoring-graph-v2.1" && (!domainModel || !policy)
          return <div key={item.mode} className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-medium">{item.label}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.description}</p></div><Button size="sm" variant={item.mode === "grounded-assistant" ? "destructive" : selected ? "default" : "outline"} disabled={busy !== null || selected || unavailable} onClick={() => onSelect(item.mode)}>{selected ? "Active" : item.mode === "grounded-assistant" ? "Roll back to T0" : "Select"}</Button></div>
        })}
      </div>
    </section>
  )
}

function TeachingProfileSection({ approved, busy, draft, preview, onApprove, onCreate, onDismissPreview, onPreview }: { approved?: ProfessorTeachingProfile; busy: string | null; draft?: ProfessorTeachingProfile; preview: ProfessorTeachingProfilePreview | null; onApprove: (profile: ProfessorTeachingProfile) => Promise<void>; onCreate: (event: FormEvent<HTMLFormElement>) => Promise<void>; onDismissPreview: () => void; onPreview: (profile: ProfessorTeachingProfile) => Promise<void> }) {
  return (
    <section aria-labelledby="teaching-profile-heading">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><h3 id="teaching-profile-heading" className="flex items-center gap-2 text-sm font-semibold"><BookOpenText className="size-4" /> Professor teaching profile</h3><p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">The professor approves explicit teaching behavior. Approval is bound to the ten cases displayed below, never to an unseen preview.</p></div><Badge variant={approved ? "default" : "outline"}>{approved ? `Approved v${approved.version}` : "Approval required"}</Badge></div>
      {draft ? (
        <div className="mt-4 rounded-xl border bg-[var(--shell)] p-4">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-semibold">Draft v{draft.version}</p><p className="mt-1 text-xs text-muted-foreground">{draft.tone} · {format(draft.depth)} depth</p></div>{!preview ? <Button disabled={busy !== null} onClick={() => void onPreview(draft)}><Eye aria-hidden="true" /> {busy === `preview-${draft.profile_id}` ? "Loading preview…" : "Review 10 cases"}</Button> : null}</div>
          {preview?.profile_id === draft.profile_id ? (
            <div className="mt-4 border-t pt-4">
              <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-semibold">Approval preview</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Review every expected behavior. Approval binds this exact content and preview hash.</p></div><Button size="sm" variant="ghost" onClick={onDismissPreview}>Close preview</Button></div>
              <ol className="mt-4 grid gap-2 lg:grid-cols-2">{preview.cases.map((item, index) => <li key={item.case_id} className="rounded-lg border bg-white p-3"><p className="text-xs font-semibold text-muted-foreground">{index + 1}. {format(item.student_situation)}</p><p className="mt-1.5 text-sm leading-5">{item.expected_behavior}</p></li>)}</ol>
              <p className="mt-3 break-all rounded-lg bg-white px-3 py-2 font-mono text-xs text-muted-foreground">Preview SHA-256: {preview.preview_sha256}</p>
              <div className="mt-4 flex flex-wrap justify-end gap-2"><Button variant="outline" onClick={onDismissPreview}>Not ready</Button><Button disabled={busy !== null} onClick={() => void onApprove(draft)}><ShieldCheck aria-hidden="true" /> {busy === `approve-${draft.profile_id}` ? "Approving…" : "Approve displayed preview"}</Button></div>
            </div>
          ) : null}
        </div>
      ) : <ProfileForm approved={approved} busy={busy} onSubmit={onCreate} />}
    </section>
  )
}

function ProfileForm({ approved, busy, onSubmit }: { approved?: ProfessorTeachingProfile; busy: string | null; onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  return (
    <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={onSubmit}>
      <p className="sm:col-span-2 text-xs leading-5 text-muted-foreground">{approved ? "Create a reviewable successor. The published release remains bound to the current approved profile." : "Define the behavior the professor expects before creating a reviewable draft."}</p>
      <Input label="Tone" name="tone" defaultValue={approved?.tone ?? "Encouraging, precise, and concise"} />
      <Select label="Depth" name="depth" options={["concise", "balanced", "detailed"]} defaultValue={approved?.depth ?? "balanced"} />
      <TextArea label="Explanation structure" name="explanation_structure" defaultValue={approved?.explanation_structure.join(", ") ?? "Concept, Example, Check understanding"} />
      <TextArea label="Example preferences" name="example_preferences" defaultValue={approved?.example_preferences.join(", ") ?? "Small worked example, Course terminology"} />
      <TextArea label="Misconception handling" name="misconception_handling" defaultValue={approved?.misconception_handling ?? "Name the misconception, contrast it with evidence, then check understanding."} />
      <TextArea label="Integrity limits" name="integrity_limits" defaultValue={approved?.integrity_limits ?? "Use attempt-first hints for assessed work; never provide a submission."} />
      <TextArea label="Help ladder" name="help_ladder" defaultValue={approved?.help_ladder.join(", ") ?? "Focused hint, Analogous example, Full explanation"} />
      <TextArea label="Outreach policy" name="outreach_policy" defaultValue={approved?.outreach_policy ?? "Only send cited in-app prompts to opted-in students within the approved limits."} />
      <Button className="sm:col-span-2 sm:justify-self-end" disabled={busy !== null} type="submit">{busy === "profile" ? <LoaderCircle className="animate-spin" /> : <ShieldCheck />} {approved ? "Create updated draft" : "Create reviewable profile"}</Button>
    </form>
  )
}

function PolicySection({ approvedProfile, busy, editing, pendingAction, policy, onCancelAction, onConfirmAction, onEdit, onRequestAction, onSave }: { approvedProfile: boolean; busy: string | null; editing: boolean; pendingAction: PolicyStateAction | null; policy: PedagogicalPolicyV2 | null; onCancelAction: () => void; onConfirmAction: () => void; onEdit: () => void; onRequestAction: (action: PolicyStateAction) => void; onSave: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  const showForm = !policy || editing
  return (
    <section className="border-t pt-6" aria-labelledby="autonomy-policy-heading">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><h3 id="autonomy-policy-heading" className="flex items-center gap-2 text-sm font-semibold"><Power className="size-4" /> Autonomy boundary</h3><p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">Choose the objectives and action types the candidate may propose. Deterministic checks still decide whether any action can execute.</p></div>{policy ? <Badge variant={policy.kill_switch ? "destructive" : policy.autonomy_enabled && !policy.paused ? "default" : "outline"}>{policy.kill_switch ? "Stopped" : policy.paused ? "Paused" : policy.autonomy_enabled ? "Active" : "Off"}</Badge> : null}</div>
      {policy && !showForm ? (
        <div className="mt-4 rounded-xl border p-4">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-semibold">Policy v{policy.version}</p><p className="mt-1 text-xs text-muted-foreground">{policy.approved_course_objectives.length} objectives · {policy.allowed_actions.filter((action) => action !== "no-action").length} permitted actions</p></div><Button size="sm" variant="outline" onClick={onEdit}><Settings2 aria-hidden="true" /> Edit boundary</Button></div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2"><div><p className="text-xs font-semibold text-muted-foreground">Approved objectives</p><ul className="mt-2 space-y-1.5 text-sm">{policy.approved_course_objectives.map((objective) => <li key={objective} className="flex gap-2"><Check className="mt-0.5 size-4 shrink-0 text-[var(--success)]" />{objective}</li>)}</ul></div><div><p className="text-xs font-semibold text-muted-foreground">Permitted actions</p><ul className="mt-2 space-y-1.5 text-sm">{policy.allowed_actions.filter((action) => action !== "no-action").map((action) => <li key={action}>{format(action)}</li>)}</ul></div></div>
          <div className="mt-5 flex flex-wrap gap-2 border-t pt-4">{policy.paused || policy.kill_switch || !policy.autonomy_enabled ? <Button size="sm" variant="outline" disabled={busy !== null} onClick={() => onRequestAction("activate")}><Power /> Review activation</Button> : null}{policy.autonomy_enabled && !policy.paused && !policy.kill_switch ? <Button size="sm" variant="outline" disabled={busy !== null} onClick={() => onRequestAction("pause")}><Pause /> Review pause</Button> : null}{!policy.kill_switch ? <Button size="sm" variant="destructive" disabled={busy !== null} onClick={() => onRequestAction("kill")}><ShieldAlert /> Review kill switch</Button> : null}</div>
        </div>
      ) : <PolicyForm approvedProfile={approvedProfile} busy={busy} policy={policy} onSubmit={onSave} />}
      {pendingAction ? (
        <Alert className={cn("mt-4", pendingAction === "kill" && "border-[var(--destructive-border)] bg-[var(--destructive-soft)]")}><ShieldAlert aria-hidden="true" /><AlertTitle>{policyActionTitle(pendingAction)}</AlertTitle><AlertDescription>{policyActionDescription(pendingAction)}</AlertDescription><div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={onCancelAction}>Cancel</Button><Button size="sm" variant={pendingAction === "kill" ? "destructive" : "default"} disabled={busy !== null} onClick={onConfirmAction}>{busy === "policy-state" ? "Applying…" : policyActionConfirmLabel(pendingAction)}</Button></div></Alert>
      ) : null}
    </section>
  )
}

function PolicyForm({ approvedProfile, busy, policy, onSubmit }: { approvedProfile: boolean; busy: string | null; policy: PedagogicalPolicyV2 | null; onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  const selected = new Set(policy?.allowed_actions ?? DEFAULT_POLICY_ACTIONS)
  return (
    <form className="mt-4 space-y-5 rounded-xl border p-4" onSubmit={onSubmit}>
      <TextArea label="Approved course objectives" name="approved_course_objectives" defaultValue={policy?.approved_course_objectives.join(", ") ?? ""} placeholder="Explain cache coherence, Apply consistency models" />
      <fieldset><legend className="text-xs font-semibold">Permitted autonomous actions</legend><p className="mt-1 text-xs leading-5 text-muted-foreground">Select only actions the professor is comfortable allowing inside the deterministic safety boundary.</p><div className="mt-3 grid gap-2 sm:grid-cols-2">{CONFIGURABLE_ACTIONS.map((action) => <label key={action} className="flex items-start gap-2.5 rounded-lg border px-3 py-2.5 text-sm"><input className="mt-1" type="checkbox" name="allowed_actions" value={action} defaultChecked={selected.has(action)} /><span>{format(action)}</span></label>)}</div></fieldset>
      {!policy ? <label className="flex items-start gap-2.5 rounded-lg bg-[var(--shell)] p-3 text-sm"><input type="checkbox" name="autonomy_enabled" className="mt-1" /><span><span className="font-medium">Activate after saving</span><span className="mt-1 block text-xs leading-5 text-muted-foreground">Activation still cannot bypass student consent, current release scope, citations, frequency limits, or quiet hours.</span></span></label> : null}
      <div className="flex justify-end"><Button type="submit" disabled={busy !== null || !approvedProfile}><ShieldCheck /> {busy === "policy" ? "Saving…" : policy ? "Save new policy version" : "Save autonomy boundary"}</Button></div>
    </form>
  )
}

function LearnersSection({ busy, goals, learnerEvidence, learningGaps, pendingCancel, policy, recipients, onCancelGoal, onCancelRequest, onCreateGoal }: { busy: string | null; goals: AutonomousGoalV1[]; learnerEvidence: ProfessorLearnerBeliefEvidence[]; learningGaps: ProfessorLearningGapResult | null; pendingCancel: string | null; policy: PedagogicalPolicyV2 | null; recipients: AutonomousRecipientEligibilityV1[]; onCancelGoal: (goal: AutonomousGoalV1) => void; onCancelRequest: (goalId: string | null) => void; onCreateGoal: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  const eligible = recipients.filter((recipient) => recipient.goal_eligible)
  return (
    <div className="space-y-7">
      <section aria-labelledby="learner-goal-heading">
        <div className="flex items-start justify-between gap-3"><div><h3 id="learner-goal-heading" className="flex items-center gap-2 text-sm font-semibold"><Target className="size-4" /> Bounded learner goals</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">Goals must derive from an approved course objective and expire after a finite number of attempts.</p></div><span className="text-xs text-muted-foreground">Maximum 3 active per learner</span></div>
        <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={onCreateGoal}><RecipientSelect label="Student" name="student_account_id" recipients={recipients} eligibility="goal" /><Select label="Approved objective" name="approved_course_objective" options={policy?.approved_course_objectives ?? []} /><TextArea label="Learner subgoal" name="learner_subgoal" placeholder="Correctly explain the invalidation step" /><TextArea label="Success condition" name="success_condition" placeholder="Answers one retrieval prompt with cited reasoning" /><Input label="Expires at" name="expires_at" type="datetime-local" /><Button className="self-end" type="submit" disabled={busy !== null || !eligible.length}><Target /> {busy === "goal" ? "Creating…" : "Create bounded goal"}</Button></form>
        {!eligible.length ? <EligibilityNote recipients={recipients} kind="goal" /> : null}
        {goals.length ? (
          <ul className="mt-5 grid gap-2 sm:grid-cols-2">
            {goals.slice(0, 8).map((goal) => (
              <li key={goal.goal_id} className="min-w-0 rounded-lg border p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="min-w-0 [overflow-wrap:anywhere] text-sm font-medium">
                    {goal.learner_subgoal}
                  </p>
                  <Badge variant="outline">{format(goal.status)}</Badge>
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {goal.student_id} · {goal.attempt_count}/{goal.attempt_limit} attempts
                </p>
                {goal.status === "active" && pendingCancel !== goal.goal_id ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mt-2"
                    disabled={busy !== null}
                    onClick={() => onCancelRequest(goal.goal_id)}
                  >
                    Stop goal
                  </Button>
                ) : null}
                {pendingCancel === goal.goal_id ? (
                  <div className="mt-3 rounded-lg bg-[var(--warning-soft)] p-3">
                    <p className="text-xs leading-5 text-[var(--warning)]">
                      Stop this goal and cancel its pending opportunities and follow-ups?
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button type="button" size="sm" variant="outline" onClick={() => onCancelRequest(null)}>
                        Keep active
                      </Button>
                      <Button type="button" size="sm" variant="destructive" disabled={busy !== null} onClick={() => onCancelGoal(goal)}>
                        {busy === `cancel-goal-${goal.goal_id}` ? "Stopping…" : "Stop goal"}
                      </Button>
                    </div>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon={Target} title="No learner goals" description="Create a finite goal after the professor profile and autonomy boundary are active." />
        )}
      </section>
      <section className="border-t pt-6" aria-labelledby="learner-evidence-heading">
        <div><h3 id="learner-evidence-heading" className="flex items-center gap-2 text-sm font-semibold"><BrainCircuit className="size-4" /> Observed learning evidence</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">Evidence counts and uncertainty are shown without converting them into a model-owned mastery score.</p></div>
        {learnerEvidence.some((item) => item.belief_states.length) ? (
          <ul className="mt-4 divide-y rounded-lg border">
            {learnerEvidence.flatMap((item) => item.belief_states.slice(0, 1).map((belief) => (
              <li key={`${item.student_id}-${belief.release_id}`} className="px-3 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2"><p className="text-sm font-medium">{item.student_id}</p><span className="text-xs text-muted-foreground">Revision {belief.revision} · {new Date(belief.updated_at).toLocaleString()}</span></div>
                {belief.concepts.length ? <ul className="mt-2 grid gap-2 sm:grid-cols-2">{belief.concepts.slice(0, 6).map((concept) => <li key={concept.concept_id} className="rounded-lg bg-[var(--shell)] px-3 py-2"><p className="text-xs font-semibold">{format(concept.concept_id)}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{concept.observation_count} observed · {concept.assessed_evidence_count} assessed · {Math.round(concept.uncertainty * 100)}% uncertainty</p></li>)}</ul> : <p className="mt-2 text-xs text-muted-foreground">No concept evidence recorded yet.</p>}
              </li>
            )))}
          </ul>
        ) : <EmptyState icon={BrainCircuit} title="No learner evidence yet" description="V2 observations will appear after a governed tutoring turn is committed." />}
      </section>
      <section className="border-t pt-6" aria-labelledby="learning-gap-heading">
        <div className="flex items-center justify-between gap-3"><div><h3 id="learning-gap-heading" className="flex items-center gap-2 text-sm font-semibold"><UsersRound className="size-4" /> Learning-gap insights</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">Only privacy-safe aggregate signals are visible.</p></div><span className="text-xs text-muted-foreground">Minimum 5 learners</span></div>
        {learningGaps?.aggregation.visible_aggregates.length ? (
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {learningGaps.aggregation.visible_aggregates.map((gap) => (
              <li key={gap.aggregate_id} className="rounded-lg border px-3 py-3">
                <p className="text-sm font-medium">{format(gap.signal_kind)}</p>
                <p className="mt-1 text-xs text-muted-foreground">{gap.distinct_learners} learners · {gap.signal_count} signals</p>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={UsersRound}
            title="No visible cohort insight"
            description={learningGaps?.aggregation.suppressed_group_count
              ? "Small cohorts remain suppressed until the privacy threshold is met."
              : "No privacy-safe aggregate is available yet."}
          />
        )}
      </section>
    </div>
  )
}

function OutreachSection({ approved, busy, evidenceChunks, pendingCancel, policy, recipients, triggers, onCancelRequest, onCancelTrigger, onSchedule }: { approved: boolean; busy: string | null; evidenceChunks: ProfessorEvidenceChunkOption[]; pendingCancel: string | null; policy: PedagogicalPolicyV2 | null; recipients: AutonomousRecipientEligibilityV1[]; triggers: ProfessorProactiveTrigger[]; onCancelRequest: (triggerId: string | null) => void; onCancelTrigger: (trigger: ProfessorProactiveTrigger) => void; onSchedule: (event: FormEvent<HTMLFormElement>) => Promise<void> }) {
  const eligible = recipients.filter((recipient) => recipient.outreach_eligible)
  return (
    <section aria-labelledby="outreach-heading">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><h3 id="outreach-heading" className="flex items-center gap-2 text-sm font-semibold"><BellRing className="size-4" /> Private in-app outreach</h3><p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">A0 professor-scheduled prompts are available now. A2 automatic interventions remain a development candidate until the product-freeze evaluation is selected.</p></div><Badge variant="outline">A0 available · A2 candidate</Badge></div>
      <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={onSchedule}><RecipientSelect label="Eligible student" name="student_account_id" recipients={recipients} eligibility="outreach" /><LabeledSelect label="Evidence" name="source_chunk_id" options={evidenceChunks.map((item) => ({ value: item.id, label: item.label }))} /><Input label="Send at" name="scheduled_for" type="datetime-local" /><Input label="Expires at" name="expires_at" type="datetime-local" /><Input label="Topic" name="topic" placeholder="Review cache coherence" /><TextArea label="Prompt" name="prompt" placeholder="Explain the key invariant in your own words." /><Button className="sm:col-span-2 sm:justify-self-end" disabled={busy !== null || !approved || !policy?.autonomy_enabled || policy.paused || policy.kill_switch || !eligible.length || !evidenceChunks.length} type="submit"><BellRing /> {busy === "schedule" ? "Scheduling…" : "Schedule cited prompt"}</Button></form>
      {!eligible.length ? <EligibilityNote recipients={recipients} kind="outreach" /> : null}
      {triggers.length ? <ul className="mt-5 divide-y rounded-lg border">{triggers.map((trigger) => <li key={trigger.id} className="px-3 py-3"><div className="flex items-start gap-3"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-muted-foreground" /><div className="min-w-0 flex-1"><p className="text-sm font-medium">{trigger.topic}</p><p className="mt-0.5 text-xs text-muted-foreground">{format(trigger.status)} · {new Date(trigger.scheduled_for).toLocaleString()}</p></div>{trigger.status === "pending" && pendingCancel !== trigger.id ? <Button size="sm" variant="ghost" disabled={busy !== null} onClick={() => onCancelRequest(trigger.id)}>Cancel</Button> : null}</div>{pendingCancel === trigger.id ? <div className="mt-3 rounded-lg border border-[var(--warning-border)] bg-[var(--warning-soft)] p-3"><p className="text-xs leading-5">Cancel this pending check-in? It will not be delivered and cannot be resumed.</p><div className="mt-2 flex gap-2"><Button size="sm" variant="outline" onClick={() => onCancelRequest(null)}>Keep scheduled</Button><Button size="sm" variant="destructive" disabled={busy !== null} onClick={() => onCancelTrigger(trigger)}>{busy === `cancel-${trigger.id}` ? "Cancelling…" : "Cancel check-in"}</Button></div></div> : null}</li>)}</ul> : <EmptyState icon={BellRing} title="No scheduled check-ins" description="Only consented recipients with current evidence can receive a private prompt." />}
    </section>
  )
}

function ActivitySection({ actions, outcomes, traces }: { actions: AutonomousActionV1[]; outcomes: AutonomousOutcomeV1[]; traces: AgentTraceV2[] }) {
  const outcomeByAction = new Map(outcomes.map((outcome) => [outcome.action_id, outcome]))
  return (
    <section aria-labelledby="autonomy-audit-heading">
      <div>
        <h3 id="autonomy-audit-heading" className="flex items-center gap-2 text-sm font-semibold">
          <Activity className="size-4" /> Autonomous activity audit
        </h3>
        <p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">
          Inspect structured decision reasons, deterministic validation, delivery, and learner outcomes. Hidden chain-of-thought is never stored.
        </p>
      </div>
      {actions.length ? (
        <ul className="mt-4 divide-y rounded-lg border">
          {actions.slice(0, 40).map((action) => {
            const outcome = outcomeByAction.get(action.action_id)
            const checks = Object.entries(action.validation_results)
            const passed = checks.filter(([, value]) => value).length
            return (
              <li key={action.action_id} className="min-w-0 px-3 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{format(action.kind)}</p>
                    <p className="mt-1 [overflow-wrap:anywhere] text-xs leading-5 text-muted-foreground">
                      {action.student_id} · {action.structured_reason}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {passed}/{checks.length} deterministic checks passed
                      {outcome ? ` · Outcome: ${format(outcome.kind)}` : " · Awaiting outcome"}
                      {outcome?.next_wake_at ? ` · Next check ${new Date(outcome.next_wake_at).toLocaleString()}` : ""}
                    </p>
                  </div>
                  <Badge variant="outline">{format(action.status)}</Badge>
                </div>
              </li>
            )
          })}
        </ul>
      ) : (
        <EmptyState icon={Activity} title="No activity recorded" description="The audit remains empty until an eligible event reaches the bounded worker." />
      )}
      <div className="mt-7 border-t pt-6">
        <h3 className="text-sm font-semibold">Reactive turn traces</h3>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">Sanitized state revisions, provider accounting, checkpoints, and restart lineage. Raw prompts and chain-of-thought are not retained.</p>
        {traces.length ? <ul className="mt-4 divide-y rounded-lg border">{traces.slice(0, 30).map((trace) => {
          const passed = Object.values(trace.validation_results).filter(Boolean).length
          const total = Object.keys(trace.validation_results).length
          return <li key={trace.trace_id} className="px-3 py-3"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-medium">State {trace.input_state_revision} → {trace.output_state_revision}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{trace.fast_path ? "Deterministic fast path" : "Semantic plan path"} · {passed}/{total} checks · {trace.restart_count} restarts · {trace.checkpoint_ids.length} checkpoints</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Requested {trace.generator_requested_model ?? "deterministic"} · returned {trace.generator_model ?? "not called"} · {trace.generation_calls + trace.repair_calls} calls · {trace.provider_input_tokens + trace.provider_output_tokens} tokens · ${trace.provider_cost_usd.toFixed(4)}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{trace.decision_reason}</p></div><Badge variant="outline">{trace.graph_version}</Badge></div></li>
        })}</ul> : <EmptyState icon={Activity} title="No reactive V2 traces" description="The first governed T1-v2 tutoring turn will create a sanitized node and restart trace." />}
      </div>
    </section>
  )
}

function SummaryItem({ label, value, ready }: { label: string; value: string; ready: boolean }) {
  return <div className="border-b px-3 py-3 even:border-l sm:border-b-0 sm:border-l sm:first:border-l-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1.5 flex items-center gap-2 text-sm font-semibold"><span className={cn("size-2 rounded-full", ready ? "bg-[var(--success)]" : "bg-muted-foreground")} />{value}</dd></div>
}

function BoundaryRow({ done, label }: { done: boolean; label: string }) {
  return <li className="flex items-start gap-3 px-3 py-3 text-sm">{done ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[var(--success)]" /> : <span className="mt-1.5 size-2 shrink-0 rounded-full bg-[var(--warning)]" />}<span>{label}</span></li>
}

function EmptyState({ icon: Icon, title, description }: { icon: typeof Activity; title: string; description: string }) {
  return <div className="mt-4 rounded-xl border border-dashed px-5 py-8 text-center"><Icon className="mx-auto size-5 text-muted-foreground" aria-hidden="true" /><p className="mt-2 text-sm font-semibold">{title}</p><p className="mx-auto mt-1 max-w-md text-xs leading-5 text-muted-foreground">{description}</p></div>
}

function RecipientSelect({ label, name, recipients, eligibility }: { label: string; name: string; recipients: AutonomousRecipientEligibilityV1[]; eligibility: "goal" | "outreach" }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span><select className="h-10 w-full rounded-lg border bg-white px-3 text-sm" name={name} required defaultValue=""><option value="" disabled>Select an eligible student…</option>{recipients.map((recipient) => { const eligible = eligibility === "goal" ? recipient.goal_eligible : recipient.outreach_eligible; const reason = recipient.ineligibility_reasons.join("; "); return <option key={recipient.student_account_id} value={recipient.student_account_id} disabled={!eligible}>{recipient.student_account_id}{eligible ? "" : ` — ${reason || "Not eligible"}`}</option> })}</select></label>
}

function EligibilityNote({ recipients, kind }: { recipients: AutonomousRecipientEligibilityV1[]; kind: "goal" | "outreach" }) {
  const reasons = [...new Set(recipients.flatMap((recipient) => recipient.ineligibility_reasons))]
  return <p className="mt-3 rounded-lg bg-[var(--warning-soft)] px-3 py-2 text-xs leading-5 text-[var(--warning)]">No student is currently eligible for {kind === "goal" ? "a new goal" : "outreach"}. {reasons.slice(0, 3).join("; ") || "Activate the approved policy and verify the student scope."}</p>
}

function Input({ label, ...props }: { label: string } & React.ComponentProps<"input">) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span><input className="h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]" required {...props} /></label>
}

function TextArea({ label, ...props }: { label: string } & React.ComponentProps<"textarea">) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span><textarea className="min-h-24 w-full resize-y rounded-lg border bg-white px-3 py-2 text-sm leading-5 outline-none focus:border-[var(--accent-strong)] focus:ring-3 focus:ring-[var(--accent-soft)]" required {...props} /></label>
}

function Select({ label, name, options, defaultValue = "" }: { label: string; name: string; options: string[]; defaultValue?: string }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span><select className="h-10 w-full rounded-lg border bg-white px-3 text-sm" name={name} required defaultValue={defaultValue}><option value="" disabled>Select…</option>{options.map((option) => <option key={option} value={option}>{format(option)}</option>)}</select></label>
}

function LabeledSelect({ label, name, options }: { label: string; name: string; options: Array<{ value: string; label: string }> }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span><select className="h-10 w-full rounded-lg border bg-white px-3 text-sm" name={name} required defaultValue=""><option value="" disabled>Select current evidence…</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
}

function text(data: FormData, name: string): string { return String(data.get(name) ?? "").trim() }
function list(data: FormData, name: string): string[] { return text(data, name).split(",").map((item) => item.trim()).filter(Boolean) }
function format(value: string): string { const label = value.replaceAll("_", " ").replaceAll("-", " "); return `${label.charAt(0).toUpperCase()}${label.slice(1)}` }
function stableId(value: string): string { return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || "item" }
function message(reason: unknown): string { return reason instanceof Error ? reason.message : "The request failed. Please try again." }

function policyActionTitle(action: PolicyStateAction): string { return action === "activate" ? "Activate governed autonomy?" : action === "pause" ? "Pause autonomous processing?" : "Use the global kill switch?" }
function policyActionDescription(action: PolicyStateAction): string { if (action === "activate") return "Eligible jobs may run inside this exact policy. Student consent, evidence, quiet hours, frequency, and delivery checks still apply."; if (action === "pause") return "New jobs will wait. Active goals and scheduled wake-ups are preserved so processing can resume without recreating them."; return "All active goals, pending opportunities, and scheduled wake-ups for this course will be cancelled. This cannot be undone by reactivation." }
function policyActionConfirmLabel(action: PolicyStateAction): string { return action === "activate" ? "Activate policy" : action === "pause" ? "Pause processing" : "Cancel all autonomous work" }
function policyActionSuccess(action: PolicyStateAction): string { return action === "activate" ? "Governed autonomy is active." : action === "pause" ? "Autonomous processing is paused; goals and wake-ups are preserved." : "The kill switch cancelled active goals and pending autonomous work." }

const GOVERNANCE_VIEWS: Array<{ id: GovernanceView; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "boundary", label: "Profile & policy" },
  { id: "learners", label: "Learners" },
  { id: "outreach", label: "Outreach" },
  { id: "activity", label: "Activity" },
]

const CONFIGURABLE_ACTIONS: AutonomousActionKind[] = [
  "ask-diagnostic-question",
  "provide-hint-or-example",
  "recommend-approved-source",
  "issue-retrieval-practice",
  "schedule-follow-up",
  "send-in-app-check-in",
  "summarize-progress",
  "create-professor-insight-draft",
]

const DEFAULT_POLICY_ACTIONS: AutonomousActionKind[] = [
  "ask-diagnostic-question",
  "provide-hint-or-example",
  "recommend-approved-source",
  "issue-retrieval-practice",
  "schedule-follow-up",
  "create-professor-insight-draft",
]

const RUNTIME_MODES: Array<{ mode: CourseTutoringMode; label: string; description: string }> = [
  { mode: "governed-autonomous-tutoring-graph-v2.1", label: "T1-v2 governed autonomy", description: "Uses release-bound concepts, observed evidence, node checkpoints, and deterministic safety gates." },
  { mode: "bounded-tutoring-graph", label: "T1-v1 historical control", description: "Keeps the earlier reactive bounded graph available for regression and rollback comparison." },
  { mode: "grounded-assistant", label: "T0 safety rollback", description: "Stops autonomous work and returns the course to grounded, non-autonomous tutoring." },
]
