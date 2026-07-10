import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  FileSearch,
  FileText,
  GitBranch,
  MessageSquareText,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react"

import { ApprovalChecklist } from "@/components/onboarding/approval-checklist"
import { OnboardingChat } from "@/components/onboarding/onboarding-chat"
import { PolicyReview } from "@/components/onboarding/policy-review"
import { PreviewComparison } from "@/components/onboarding/preview-comparison"
import { SourceInventory } from "@/components/onboarding/source-inventory"
import { WorkflowTrace } from "@/components/onboarding/workflow-trace"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useOnboardingSession } from "@/hooks/use-onboarding-session"
import type { OnboardingSession, ReleaseStatus } from "@/lib/api"
import { cn } from "@/lib/utils"

function App() {
  const {
    session,
    error,
    isStarting,
    isSubmitting,
    isAddingSource,
    updatingSourceId,
    updatingFieldId,
    updatingApprovalItemId,
    updatingPreviewId,
    isAddingCustomPreview,
    isResolvingRevision,
    restart,
    sendMessage,
    addSource,
    editSource,
    editPolicyField,
    updateApprovalItem,
    decidePreview,
    addCustomPreview,
    confirmRevision,
    discardRevision,
  } = useOnboardingSession()
  const releaseReadiness = getReleaseReadiness(session)
  const stepStates = getStepStates(session)
  const nextAction = getNextAction(session, releaseReadiness.blockers)

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-foreground">
      <div className="mx-auto flex min-h-screen max-w-[1540px] flex-col gap-4 px-4 py-4 lg:px-6">
        <header className="rounded-xl border bg-background">
          <div className="flex flex-col gap-4 px-4 py-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge variant="secondary" className="gap-1.5">
                  <Bot className="size-3.5" />
                  Course Digital Twin
                </Badge>
                <Badge variant="outline" className="gap-1.5">
                  <GitBranch className="size-3.5" />
                  Sprint 1 prototype
                </Badge>
                <Badge
                  variant={
                    releaseReadiness.status === "approved" ? "default" : "outline"
                  }
                  className={cn(
                    "gap-1.5",
                    releaseReadiness.status === "blocked" &&
                      "border-red-200 text-red-700",
                  )}
                >
                  <ShieldCheck className="size-3.5" />
                  {formatReleaseStatus(releaseReadiness.status)}
                </Badge>
              </div>
              <h1 className="text-xl font-semibold tracking-normal text-balance">
                Professor Review Console
              </h1>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
                Set up a draft tutor by collecting instructor guidance, approving
                source metadata, reviewing evidence, and clearing the release gate.
              </p>
            </div>

            <div className="grid gap-2 sm:grid-cols-2 lg:w-[520px]">
              <ReadinessMetric
                label="Release blockers"
                value={releaseReadiness.blockers.length}
                tone={releaseReadiness.blockers.length === 0 ? "clear" : "blocked"}
              />
              <ReadinessMetric
                label="Accepted previews"
                value={`${releaseReadiness.acceptedPreviews}/${releaseReadiness.previewCount}`}
                tone={
                  releaseReadiness.previewCount > 0 &&
                  releaseReadiness.acceptedPreviews === releaseReadiness.previewCount
                    ? "clear"
                    : "waiting"
                }
              />
            </div>
          </div>

          <div className="border-t px-4 py-3">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex min-w-0 items-start gap-3">
                <div
                  className={cn(
                    "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg",
                    releaseReadiness.blockers.length === 0
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-amber-50 text-amber-700",
                  )}
                >
                  {releaseReadiness.blockers.length === 0 ? (
                    <CheckCircle2 className="size-4" />
                  ) : (
                    <ShieldAlert className="size-4" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold">{nextAction.title}</div>
                  <p className="mt-0.5 text-sm leading-6 text-muted-foreground">
                    {nextAction.detail}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {releaseReadiness.blockers.slice(0, 3).map((blocker) => (
                  <Badge
                    key={blocker}
                    variant="outline"
                    className="max-w-full border-amber-200 bg-amber-50 text-amber-800"
                  >
                    <span className="truncate">{blocker}</span>
                  </Badge>
                ))}
                {releaseReadiness.blockers.length > 3 && (
                  <Badge variant="outline">
                    +{releaseReadiness.blockers.length - 3} more
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </header>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertTitle>Onboarding request failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="grid content-start gap-4">
            <section className="rounded-xl border bg-background p-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold">Setup map</h2>
                <Badge variant="outline">{formatStep(session?.current_step ?? "starting")}</Badge>
              </div>
              <div className="grid gap-2">
                {stepStates.map((step) => (
                  <StepStatusCard key={step.id} step={step} />
                ))}
              </div>
            </section>

            <section className="rounded-xl border bg-background p-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold">Gate summary</h2>
                <Badge
                  variant={
                    releaseReadiness.status === "approved" ? "default" : "outline"
                  }
                >
                  {formatReleaseStatus(releaseReadiness.status)}
                </Badge>
              </div>
              <div className="grid gap-2 text-sm">
                <SummaryLine
                  label="Approved sources"
                  value={releaseReadiness.approvedSources}
                />
                <SummaryLine
                  label="Policy blockers"
                  value={releaseReadiness.policyBlockers}
                />
                <SummaryLine
                  label="Pending previews"
                  value={releaseReadiness.pendingPreviews}
                />
                <SummaryLine
                  label="Checklist blockers"
                  value={releaseReadiness.checklistBlockers}
                />
              </div>
            </section>
          </aside>

          <section className="min-w-0 rounded-xl border bg-background">
            <Tabs defaultValue="interview" className="min-h-0">
              <div className="border-b px-3 py-3">
                <TabsList className="w-full justify-start overflow-x-auto">
                  <TabsTrigger value="interview" className="min-w-fit">
                    <MessageSquareText data-icon="inline-start" />
                    Interview
                  </TabsTrigger>
                  <TabsTrigger value="sources" className="min-w-fit">
                    <FileText data-icon="inline-start" />
                    Sources
                  </TabsTrigger>
                  <TabsTrigger value="policy" className="min-w-fit">
                    <ShieldCheck data-icon="inline-start" />
                    Policy
                  </TabsTrigger>
                  <TabsTrigger value="preview" className="min-w-fit">
                    <FileSearch data-icon="inline-start" />
                    Preview
                  </TabsTrigger>
                  <TabsTrigger value="approval" className="min-w-fit">
                    <ClipboardCheck data-icon="inline-start" />
                    Approval
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="interview" className="m-0">
                <div className="grid min-h-[520px] gap-0 lg:min-h-[680px] lg:grid-cols-[minmax(0,1fr)_380px]">
                  <section className="flex min-h-[520px] flex-col overflow-hidden border-b lg:min-h-[680px] lg:border-b-0 lg:border-r">
                    <WorkbenchHeader
                      title="Instructor interview"
                      detail="Collect source rules, teaching style, integrity boundaries, misconception handling, and approval criteria."
                      badge={session?.policy ? "policy generated" : "collecting answers"}
                    />
                    <OnboardingChat
                      messages={session?.messages ?? []}
                      currentStep={session?.current_step ?? "starting"}
                      isLoading={isStarting}
                      isSubmitting={isSubmitting}
                      onSendMessage={sendMessage}
                      onRestart={restart}
                    />
                  </section>
                  <aside className="grid content-start gap-4 p-4">
                    <WorkflowTrace trace={session?.trace ?? []} />
                  </aside>
                </div>
              </TabsContent>

              <TabsContent value="sources" className="m-0 p-4">
                <SourceInventory
                  items={session?.source_inventory ?? []}
                  blockers={session?.release_blockers.source_inventory ?? []}
                  isAdding={isAddingSource}
                  updatingSourceId={updatingSourceId}
                  onAddSource={addSource}
                  onUpdateSource={editSource}
                />
              </TabsContent>

              <TabsContent value="policy" className="m-0 p-4">
                <PolicyReview
                  policy={session?.policy ?? null}
                  updatingFieldId={updatingFieldId}
                  onUpdateField={editPolicyField}
                />
              </TabsContent>

              <TabsContent value="preview" className="m-0 p-4">
                <div className="grid gap-4">
                  <PreviewComparison
                    previewCases={session?.preview_cases ?? []}
                    updatingPreviewId={updatingPreviewId}
                    isAddingCustomPreview={isAddingCustomPreview}
                    onPreviewDecision={decidePreview}
                    onAddCustomPreview={addCustomPreview}
                  />
                  {session?.revision_proposal && (
                    <RevisionProposalPanel
                      session={session}
                      isResolvingRevision={isResolvingRevision}
                      onConfirm={confirmRevision}
                      onDiscard={discardRevision}
                    />
                  )}
                </div>
              </TabsContent>

              <TabsContent value="approval" className="m-0 p-4">
                <ApprovalChecklist
                  items={session?.approval_checklist ?? []}
                  releaseStatus={session?.policy?.release_status ?? "draft"}
                  updatingItemId={updatingApprovalItemId}
                  onUpdateItem={updateApprovalItem}
                />
              </TabsContent>
            </Tabs>
          </section>
        </div>
      </div>
    </main>
  )
}

function WorkbenchHeader({
  title,
  detail,
  badge,
}: {
  title: string
  detail: string
  badge: string
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3">
      <div>
        <h2 className="text-sm font-semibold">{title}</h2>
        <p className="mt-0.5 max-w-2xl text-xs leading-5 text-muted-foreground">
          {detail}
        </p>
      </div>
      <Badge variant="outline">{badge}</Badge>
    </div>
  )
}

function ReadinessMetric({
  label,
  value,
  tone,
}: {
  label: string
  value: string | number
  tone: "clear" | "waiting" | "blocked"
}) {
  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2",
        tone === "clear" && "border-emerald-200 bg-emerald-50 text-emerald-900",
        tone === "waiting" && "border-sky-200 bg-sky-50 text-sky-900",
        tone === "blocked" && "border-amber-200 bg-amber-50 text-amber-900",
      )}
    >
      <div className="text-xs font-medium opacity-80">{label}</div>
      <div className="mt-1 text-lg font-semibold leading-none">{value}</div>
    </div>
  )
}

function StepStatusCard({ step }: { step: StepState }) {
  const Icon = step.icon

  return (
    <div
      className={cn(
        "grid grid-cols-[auto_minmax(0,1fr)] gap-3 rounded-lg border p-3 text-sm",
        step.state === "active" && "border-sky-200 bg-sky-50 text-sky-950",
        step.state === "complete" &&
          "border-emerald-200 bg-emerald-50 text-emerald-950",
        step.state === "blocked" && "border-amber-200 bg-amber-50 text-amber-950",
        step.state === "waiting" && "bg-background",
      )}
    >
      <div className="mt-0.5">
        {step.state === "complete" ? (
          <CheckCircle2 className="size-4 text-emerald-700" />
        ) : step.state === "waiting" ? (
          <Circle className="size-4 text-muted-foreground" />
        ) : (
          <Icon className="size-4" />
        )}
      </div>
      <div className="min-w-0">
        <div className="font-medium">{step.label}</div>
        <p className="mt-0.5 text-xs leading-5 opacity-75">{step.detail}</p>
      </div>
    </div>
  )
}

function SummaryLine({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-muted/50 px-3 py-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  )
}

function RevisionProposalPanel({
  session,
  isResolvingRevision,
  onConfirm,
  onDiscard,
}: {
  session: OnboardingSession
  isResolvingRevision: boolean
  onConfirm: () => Promise<void>
  onDiscard: () => Promise<void>
}) {
  if (!session.revision_proposal) {
    return null
  }

  return (
    <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Pending policy revision</div>
          <p className="mt-1 text-xs leading-5">
            Confirm to update the policy, or discard to keep the current draft.
          </p>
        </div>
        <Badge variant="outline" className="border-amber-300 text-amber-900">
          review needed
        </Badge>
      </div>
      <p className="mt-3 text-sm leading-6">
        {session.revision_proposal.proposed_value}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {session.revision_proposal.affected_policy_fields.map((field) => (
          <Badge key={field} variant="outline">
            {field.replaceAll("_", " ")}
          </Badge>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <Button
          type="button"
          size="sm"
          onClick={() => void onConfirm()}
          disabled={isResolvingRevision}
        >
          Confirm
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => void onDiscard()}
          disabled={isResolvingRevision}
        >
          Discard
        </Button>
      </div>
    </section>
  )
}

type StepState = {
  id: string
  label: string
  detail: string
  state: "active" | "blocked" | "complete" | "waiting"
  icon: typeof MessageSquareText
}

function getReleaseReadiness(session: OnboardingSession | null) {
  const blockers = new Set(Object.values(session?.release_blockers ?? {}).flat())
  if (!session) {
    blockers.add("Start the onboarding session.")
  } else {
    if (session.source_inventory.length === 0) {
      blockers.add("Add at least one approved source metadata item.")
    }
    if (!session.policy) {
      blockers.add("Complete the instructor interview to generate policy.")
    }
    if (session.policy && session.preview_cases.length === 0) {
      blockers.add("Generate preview evidence for professor review.")
    }
    if (session.policy && session.approval_checklist.length === 0) {
      blockers.add("Generate the approval checklist.")
    }
  }
  const approvedSources =
    session?.source_inventory.filter(
      (source) => source.permission_status === "approved" && !source.excluded,
    ).length ?? 0
  const policyFields = session?.policy
    ? [
        ...session.policy.safety_compliance,
        ...session.policy.pedagogy,
        ...session.policy.professor_review,
      ]
    : []
  const policyBlockers = policyFields.filter(
    (field) => field.status === "blocks_release",
  ).length
  const previewCount = session?.preview_cases.length ?? 0
  const acceptedPreviews =
    session?.preview_cases.filter((preview) => preview.decision === "accepted")
      .length ?? 0
  const pendingPreviews =
    session?.preview_cases.filter((preview) => preview.decision !== "accepted")
      .length ?? 0
  const checklistBlockers =
    session?.approval_checklist.filter(
      (item) => item.blocks_release && !item.checked,
    ).length ?? 0

  return {
    status: session?.policy?.release_status ?? "draft",
    blockers: [...blockers],
    approvedSources,
    policyBlockers,
    previewCount,
    acceptedPreviews,
    pendingPreviews,
    checklistBlockers,
  }
}

function getStepStates(session: OnboardingSession | null): StepState[] {
  const currentStep = session?.current_step ?? "starting"
  const hasPolicy = Boolean(session?.policy)
  const hasSources = (session?.source_inventory.length ?? 0) > 0
  const sourceBlocked =
    (session?.release_blockers.source_inventory.length ?? 0) > 0
  const previewBlocked =
    (session?.release_blockers.preview_acceptance.length ?? 0) > 0
  const checklistBlocked =
    (session?.release_blockers.approval_checklist.length ?? 0) > 0

  return [
    {
      id: "sources",
      label: "Source inventory",
      detail: hasSources ? "Metadata added for review." : "Add approved source metadata.",
      state: sourceBlocked ? "blocked" : hasSources ? "complete" : "waiting",
      icon: FileText,
    },
    {
      id: "interview",
      label: "Instructor interview",
      detail: hasPolicy
        ? "Answers generated a draft policy."
        : `Current: ${formatStep(currentStep)}`,
      state: hasPolicy ? "complete" : "active",
      icon: MessageSquareText,
    },
    {
      id: "policy",
      label: "Tutor policy",
      detail: hasPolicy ? "Review editable policy fields." : "Generated after interview.",
      state: hasPolicy ? "active" : "waiting",
      icon: ShieldCheck,
    },
    {
      id: "preview",
      label: "Preview evidence",
      detail: previewBlocked
        ? "Accept or revise required cases."
        : "Compare configured and generic responses.",
      state: previewBlocked
        ? "blocked"
        : (session?.preview_cases.length ?? 0) > 0
          ? "complete"
          : "waiting",
      icon: FileSearch,
    },
    {
      id: "approval",
      label: "Professor approval",
      detail: checklistBlocked
        ? "Checklist still blocks release."
        : "Final release confirmation.",
      state: checklistBlocked
        ? "blocked"
        : session?.policy?.release_status === "approved"
          ? "complete"
          : "waiting",
      icon: ClipboardCheck,
    },
  ]
}

function getNextAction(
  session: OnboardingSession | null,
  blockers: string[],
): { title: string; detail: string } {
  if (!session) {
    return {
      title: "Starting onboarding session",
      detail: "The review console will populate once the API returns the draft session.",
    }
  }

  if (blockers.length === 0 && session.policy?.release_status === "approved") {
    return {
      title: "Release gate is clear",
      detail: "All professor review gates are complete for this draft.",
    }
  }

  if (session.source_inventory.length === 0) {
    return {
      title: "Add source metadata first",
      detail: "Start with syllabus, slide, assignment, or rubric metadata so preview grounding can be audited.",
    }
  }

  if (!session.policy) {
    return {
      title: "Continue the instructor interview",
      detail: `Answer the current prompt for ${formatStep(session.current_step)} to generate the first tutor policy draft.`,
    }
  }

  if (session.revision_proposal) {
    return {
      title: "Resolve the pending revision",
      detail: "A professor feedback item has produced a policy update proposal that needs confirmation or discard.",
    }
  }

  if (blockers.length > 0) {
    return {
      title: "Clear the next release blocker",
      detail: blockers[0],
    }
  }

  return {
    title: "Review final approval",
    detail: "The draft is ready for professor approval once the checklist confirms the release criteria.",
  }
}

function formatReleaseStatus(status: ReleaseStatus): string {
  if (status === "approved") {
    return "approved"
  }
  if (status === "blocked") {
    return "blocked"
  }
  return "draft only"
}

function formatStep(step: string): string {
  return step.replaceAll("_", " ")
}

export default App
