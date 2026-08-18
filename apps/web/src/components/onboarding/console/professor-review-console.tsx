import { useState } from "react"
import {
  AlertCircle,
  ArrowRight,
  BookOpenCheck,
  FlaskConical,
} from "lucide-react"

import { ApprovalChecklist } from "@/components/onboarding/approval-checklist"
import {
  ReleaseRoute,
  ReleaseStateIcon,
  WorkbenchHeader,
} from "@/components/onboarding/console/readiness-summary"
import { ReviewContext } from "@/components/onboarding/console/review-context"
import { RevisionProposalPanel } from "@/components/onboarding/console/revision-proposal-panel"
import { OnboardingChat } from "@/components/onboarding/onboarding-chat"
import { PolicyReview } from "@/components/onboarding/policy-review"
import { PreviewComparison } from "@/components/onboarding/preview-comparison"
import { SourceInventory } from "@/components/onboarding/source-inventory"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { OnboardingController } from "@/hooks/use-onboarding-session"
import type { ReviewStageId } from "@/lib/onboarding/readiness"
import {
  formatReleaseStatus,
  getNextAction,
  getReleaseReadiness,
  getStepStates,
} from "@/lib/onboarding/readiness"
import { cn } from "@/lib/utils"

const STAGE_COPY: Record<
  ReviewStageId,
  { index: string; title: string; detail: string }
> = {
  sources: {
    index: "01",
    title: "Source governance",
    detail:
      "Register course-material metadata, classify provenance, and make an explicit permission decision for each source.",
  },
  interview: {
    index: "02",
    title: "Instructor interview",
    detail:
      "Record source rules, teaching approach, integrity boundaries, misconception handling, and approval criteria.",
  },
  policy: {
    index: "03",
    title: "Tutor policy",
    detail:
      "Inspect the generated policy field by field and mark every decision as resolved, review needed, or release blocking.",
  },
  preview: {
    index: "04",
    title: "Preview evidence",
    detail:
      "Compare configured behavior with the generic control, inspect source provenance, and record a professor decision.",
  },
  approval: {
    index: "05",
    title: "Professor approval",
    detail:
      "Confirm the final checklist only after source, policy, preview, and revision gates are clear.",
  },
}

export function ProfessorReviewConsole({
  controller,
}: {
  controller: OnboardingController
}) {
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
  } = controller
  const [activeStage, setActiveStage] = useState<ReviewStageId>("interview")
  const releaseReadiness = getReleaseReadiness(session)
  const stepStates = getStepStates(session)
  const nextAction = getNextAction(session, releaseReadiness.blockers)
  const activeCopy = STAGE_COPY[activeStage]

  return (
    <main className="min-h-screen bg-[var(--workspace)] text-foreground">
      <div className="mx-auto min-h-screen max-w-[1800px] px-0 py-0 2xl:px-5 2xl:py-5">
        <div className="min-h-screen border-x bg-white 2xl:min-h-[calc(100vh-2.5rem)] 2xl:border">
          <header className="bg-white">
            <div className="flex flex-col gap-4 px-4 py-4 sm:gap-5 sm:px-7 sm:py-6 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--ink)]">
                    <span className="flex size-7 items-center justify-center bg-[var(--ink)] text-white">
                      <BookOpenCheck className="size-4" aria-hidden="true" />
                    </span>
                    Course Digital Twin
                  </span>
                  <Badge variant="outline" className="status-badge">
                    <FlaskConical className="size-3" aria-hidden="true" />
                    Experimental prototype
                  </Badge>
                </div>
                <h1 className="mt-3 text-xl font-semibold tracking-[-0.025em] text-[var(--ink)] sm:mt-4 sm:text-2xl">
                  Professor Review Console
                </h1>
                <p className="mt-1.5 hidden max-w-[72ch] text-sm leading-6 text-muted-foreground sm:block">
                  Configure and verify a draft course tutor through explicit source,
                  policy, evidence, and approval decisions.
                </p>
              </div>

              <dl className="grid min-w-0 grid-cols-3 border-l border-t lg:w-[480px]">
                <LedgerMetric
                  label="Release state"
                  mobileLabel="Status"
                  value={formatReleaseStatus(releaseReadiness.status)}
                  tone={
                    releaseReadiness.status === "approved"
                      ? "success"
                      : releaseReadiness.status === "blocked"
                        ? "danger"
                        : "warning"
                  }
                />
                <LedgerMetric
                  label="Blockers"
                  mobileLabel="Blockers"
                  value={releaseReadiness.blockers.length}
                  tone={releaseReadiness.blockers.length === 0 ? "success" : "warning"}
                />
                <LedgerMetric
                  label="Previews"
                  mobileLabel="Previews"
                  value={`${releaseReadiness.acceptedPreviews}/${releaseReadiness.previewCount}`}
                  tone={
                    releaseReadiness.previewCount > 0 &&
                    releaseReadiness.acceptedPreviews === releaseReadiness.previewCount
                      ? "success"
                      : "neutral"
                  }
                />
              </dl>
            </div>

            <section
              aria-labelledby="next-decision-title"
              className={cn(
                "grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-t px-4 py-3 sm:gap-4 sm:px-7 sm:py-4 lg:items-center",
                releaseReadiness.blockers.length === 0
                  ? "bg-[var(--success-soft)]"
                  : "bg-[var(--warning-soft)]",
              )}
            >
              <div className="flex min-w-0 gap-3">
                <span
                  className={cn(
                    "mt-0.5 flex size-8 shrink-0 items-center justify-center border",
                    releaseReadiness.blockers.length === 0
                      ? "border-[var(--success-border)] text-[var(--success)]"
                      : "border-[var(--warning-border)] text-[var(--warning)]",
                  )}
                >
                  <ReleaseStateIcon clear={releaseReadiness.blockers.length === 0} />
                </span>
                <div>
                  <div className="dossier-label">Recommended decision</div>
                  <h2 id="next-decision-title" className="mt-1 text-sm font-semibold">
                    {nextAction.title}
                  </h2>
                  <p className="mt-0.5 hidden max-w-4xl text-sm leading-5 text-muted-foreground sm:block">
                    {nextAction.detail}
                  </p>
                </div>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="justify-self-end border-[var(--rule-strong)] bg-white sm:h-9 sm:px-3.5 lg:justify-self-end"
                onClick={() => setActiveStage(nextAction.stage)}
              >
                <span className="hidden sm:inline">
                  Open {STAGE_COPY[nextAction.stage].title.toLowerCase()}
                </span>
                <span className="sm:hidden">Open</span>
                <ArrowRight data-icon="inline-end" />
              </Button>
            </section>
          </header>

          {error && (
            <div className="border-t px-5 py-4 sm:px-7">
              <Alert
                variant="destructive"
                className="border-[var(--destructive-border)] bg-[var(--destructive-soft)]"
              >
                <AlertCircle className="size-4" />
                <AlertTitle>Onboarding request failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            </div>
          )}

          <div className="grid border-t xl:grid-cols-[244px_minmax(0,1fr)_332px]">
            <aside className="min-w-0 border-b bg-white xl:sticky xl:top-0 xl:max-h-screen xl:self-start xl:overflow-y-auto xl:border-b-0 xl:border-r">
              <ReleaseRoute
                steps={stepStates}
                currentStep={session?.current_step ?? "starting"}
                selectedStage={activeStage}
                onSelectStage={setActiveStage}
              />
            </aside>

            <section className="min-w-0 bg-white">
              <WorkbenchHeader
                index={activeCopy.index}
                title={activeCopy.title}
                detail={activeCopy.detail}
                badge={stageBadge(activeStage, session)}
              />
              <div className={cn(activeStage === "interview" ? "" : "p-5 sm:p-6")}>
                {activeStage === "interview" && (
                  <OnboardingChat
                    messages={session?.messages ?? []}
                    currentStep={session?.current_step ?? "starting"}
                    isLoading={isStarting}
                    isSubmitting={isSubmitting}
                    onSendMessage={sendMessage}
                    onRestart={restart}
                  />
                )}

                {activeStage === "sources" && (
                  <SourceInventory
                    items={session?.source_inventory ?? []}
                    blockers={session?.release_blockers.source_inventory ?? []}
                    isAdding={isAddingSource}
                    updatingSourceId={updatingSourceId}
                    onAddSource={addSource}
                    onUpdateSource={editSource}
                  />
                )}

                {activeStage === "policy" && (
                  <PolicyReview
                    policy={session?.policy ?? null}
                    updatingFieldId={updatingFieldId}
                    onUpdateField={editPolicyField}
                  />
                )}

                {activeStage === "preview" && (
                  <div className="grid gap-5">
                    {session?.revision_proposal && (
                      <RevisionProposalPanel
                        session={session}
                        isResolvingRevision={isResolvingRevision}
                        onConfirm={confirmRevision}
                        onDiscard={discardRevision}
                      />
                    )}
                    <PreviewComparison
                      previewCases={session?.preview_cases ?? []}
                      updatingPreviewId={updatingPreviewId}
                      isAddingCustomPreview={isAddingCustomPreview}
                      onPreviewDecision={decidePreview}
                      onAddCustomPreview={addCustomPreview}
                    />
                  </div>
                )}

                {activeStage === "approval" && (
                  <ApprovalChecklist
                    items={session?.approval_checklist ?? []}
                    releaseStatus={session?.policy?.release_status ?? "draft"}
                    updatingItemId={updatingApprovalItemId}
                    onUpdateItem={updateApprovalItem}
                  />
                )}
              </div>
            </section>

            <div className="min-w-0 border-t xl:sticky xl:top-0 xl:max-h-screen xl:self-start xl:overflow-y-auto xl:border-l xl:border-t-0">
              <ReviewContext session={session} readiness={releaseReadiness} />
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

function LedgerMetric({
  label,
  mobileLabel,
  value,
  tone,
}: {
  label: string
  mobileLabel: string
  value: string | number
  tone: "success" | "warning" | "danger" | "neutral"
}) {
  return (
    <div className="min-w-0 border-b border-r px-3 py-3 sm:px-4">
      <dt className="dossier-label min-h-4 leading-4 sm:min-h-0">
        <span className="sm:hidden">{mobileLabel}</span>
        <span className="hidden sm:inline">{label}</span>
      </dt>
      <dd
        className={cn(
          "mt-1 truncate text-sm font-semibold tabular-nums",
          tone === "success" && "text-[var(--success)]",
          tone === "warning" && "text-[var(--warning)]",
          tone === "danger" && "text-[var(--destructive)]",
          tone === "neutral" && "text-[var(--ink)]",
        )}
      >
        {value}
      </dd>
    </div>
  )
}

function stageBadge(
  stage: ReviewStageId,
  session: OnboardingController["session"],
): string {
  if (stage === "sources") {
    return `${session?.source_inventory.length ?? 0} registered`
  }
  if (stage === "interview") {
    return session?.policy ? "policy generated" : "collecting answers"
  }
  if (stage === "policy") {
    return `policy v${session?.policy_version ?? 0}`
  }
  if (stage === "preview") {
    return `${session?.preview_cases.length ?? 0} cases`
  }
  return session?.policy?.release_status === "approved"
    ? "approved"
    : "draft only"
}
