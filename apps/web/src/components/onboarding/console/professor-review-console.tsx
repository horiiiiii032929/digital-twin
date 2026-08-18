import { useState } from "react"
import {
  Activity,
  AlertCircle,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
} from "lucide-react"

import { ApprovalChecklist } from "@/components/onboarding/approval-checklist"
import { ReleaseRoute } from "@/components/onboarding/console/readiness-summary"
import { ReviewContext } from "@/components/onboarding/console/review-context"
import { RevisionProposalPanel } from "@/components/onboarding/console/revision-proposal-panel"
import { OnboardingChat } from "@/components/onboarding/onboarding-chat"
import { PolicyReview } from "@/components/onboarding/policy-review"
import { PreviewComparison } from "@/components/onboarding/preview-comparison"
import { SourceInventory } from "@/components/onboarding/source-inventory"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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

const TOOL_TITLES: Record<ReviewStageId, string> = {
  sources: "Sources",
  interview: "Tutor policy",
  policy: "Tutor policy",
  preview: "Preview",
  approval: "Approval",
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
  const [activityOpen, setActivityOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const releaseReadiness = getReleaseReadiness(session)
  const stepStates = getStepStates(session)
  const nextAction = getNextAction(session, releaseReadiness.blockers)

  const openStage = (stage: ReviewStageId) => {
    setActiveStage(stage)
    setActivityOpen(false)
  }

  return (
    <main className="flex h-dvh flex-col overflow-hidden bg-white text-foreground">
      <AppBar
        collapsed={sidebarCollapsed}
        status={formatReleaseStatus(releaseReadiness.status)}
        blockerCount={releaseReadiness.blockers.length}
        activityOpen={activityOpen}
        onToggleActivity={() => setActivityOpen((open) => !open)}
      />

      <div
        className={cn(
          "grid min-h-0 flex-1 lg:h-[calc(100dvh-57px)] lg:overflow-hidden",
          sidebarCollapsed
            ? "lg:grid-cols-[72px_minmax(0,1fr)]"
            : "lg:grid-cols-[240px_minmax(0,1fr)]",
        )}
      >
        <aside className="hidden min-h-0 flex-col border-r bg-[var(--shell)] lg:flex">
          <ReleaseRoute
            steps={stepStates}
            selectedStage={activeStage}
            collapsed={sidebarCollapsed}
            onSelectStage={openStage}
          />
          <div className="mt-auto border-t p-2">
            <Button
              type="button"
              variant="ghost"
              size={sidebarCollapsed ? "icon" : "sm"}
              className={cn("text-muted-foreground", !sidebarCollapsed && "w-full justify-start")}
              aria-label={sidebarCollapsed ? "Expand setup navigation" : "Collapse setup navigation"}
              onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
            >
              {sidebarCollapsed ? (
                <PanelLeftOpen data-icon="inline-start" />
              ) : (
                <PanelLeftClose data-icon="inline-start" />
              )}
              {sidebarCollapsed ? null : "Collapse"}
            </Button>
          </div>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-col bg-white">
          <div className="border-b bg-[var(--shell)] lg:hidden">
            <ReleaseRoute
              steps={stepStates}
              selectedStage={activeStage}
              collapsed={false}
              onSelectStage={openStage}
            />
          </div>

          {error ? (
            <div className="px-4 pt-4 sm:px-6">
              <Alert variant="destructive">
                <AlertCircle />
                <AlertTitle>Setup request failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            </div>
          ) : null}

          <div className="grid min-h-0 flex-1 xl:grid-cols-[minmax(480px,1.03fr)_minmax(420px,0.97fr)]">
            <section
              aria-label="Setup conversation"
              className={cn(
                "min-h-0 min-w-0 bg-white xl:block xl:border-r",
                activeStage !== "interview" || activityOpen ? "hidden" : "block",
              )}
            >
              <OnboardingChat
                messages={session?.messages ?? []}
                currentStep={session?.current_step ?? "starting"}
                isLoading={isStarting}
                isSubmitting={isSubmitting}
                onSendMessage={sendMessage}
                onRestart={restart}
              />
            </section>

            <section
              aria-label={activityOpen ? "Review activity" : TOOL_TITLES[activeStage]}
              className={cn(
                "min-h-0 min-w-0 overflow-y-auto bg-white xl:block",
                activeStage === "interview" && !activityOpen ? "hidden" : "block",
              )}
            >
              {activityOpen ? (
                <ReviewContext session={session} readiness={releaseReadiness} />
              ) : (
                <StageTool
                  stage={activeStage}
                  controller={controller}
                  onAddSource={addSource}
                  onUpdateSource={editSource}
                  onUpdateField={editPolicyField}
                  onUpdateApproval={updateApprovalItem}
                  onPreviewDecision={decidePreview}
                  onAddCustomPreview={addCustomPreview}
                  onConfirmRevision={confirmRevision}
                  onDiscardRevision={discardRevision}
                  isAddingSource={isAddingSource}
                  updatingSourceId={updatingSourceId}
                  updatingFieldId={updatingFieldId}
                  updatingApprovalItemId={updatingApprovalItemId}
                  updatingPreviewId={updatingPreviewId}
                  isAddingCustomPreview={isAddingCustomPreview}
                  isResolvingRevision={isResolvingRevision}
                />
              )}
            </section>
          </div>

          <ReleaseBar
            blockers={releaseReadiness.blockers}
            nextActionTitle={nextAction.title}
            onOpenNext={() => openStage(nextAction.stage)}
          />
        </section>
      </div>
    </main>
  )
}

function AppBar({
  collapsed,
  status,
  blockerCount,
  activityOpen,
  onToggleActivity,
}: {
  collapsed: boolean
  status: string
  blockerCount: number
  activityOpen: boolean
  onToggleActivity: () => void
}) {
  const statusLabel =
    blockerCount > 0
      ? `${capitalize(status)} · ${blockerCount} blocker${blockerCount === 1 ? "" : "s"}`
      : capitalize(status)

  return (
    <header className="flex min-h-14 items-stretch border-b bg-white">
      <div
        className={cn(
          "hidden shrink-0 items-center gap-2.5 border-r px-4 lg:flex",
          collapsed ? "w-[72px] justify-center px-0" : "w-[240px]",
        )}
      >
        <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-strong)] text-white">
          <Sparkles className="size-4" aria-hidden="true" />
        </span>
        {collapsed ? null : (
          <span className="truncate text-sm font-semibold tracking-[-0.01em]">
            Course Digital Twin
          </span>
        )}
      </div>

      <div className="flex min-w-0 flex-1 items-center justify-between gap-3 px-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-strong)] text-white lg:hidden">
            <Sparkles className="size-4" aria-hidden="true" />
          </span>
          <h1 className="truncate text-base font-semibold tracking-[-0.02em]">
            Tutor setup
          </h1>
          <span
            className={cn(
              "hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium sm:inline-flex",
              blockerCount > 0
                ? "bg-[var(--warning-soft)] text-[var(--warning)]"
                : "bg-[var(--success-soft)] text-[var(--success)]",
            )}
          >
            <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
            {statusLabel}
          </span>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-label="Activity"
          aria-pressed={activityOpen}
          onClick={onToggleActivity}
        >
          <Activity data-icon="inline-start" />
          <span className="hidden sm:inline">Activity</span>
          <ChevronDown
            data-icon="inline-end"
            className={cn("transition-transform", activityOpen && "rotate-180")}
          />
        </Button>
      </div>
    </header>
  )
}

function StageTool({
  stage,
  controller,
  onAddSource,
  onUpdateSource,
  onUpdateField,
  onUpdateApproval,
  onPreviewDecision,
  onAddCustomPreview,
  onConfirmRevision,
  onDiscardRevision,
  isAddingSource,
  updatingSourceId,
  updatingFieldId,
  updatingApprovalItemId,
  updatingPreviewId,
  isAddingCustomPreview,
  isResolvingRevision,
}: {
  stage: ReviewStageId
  controller: OnboardingController
  onAddSource: OnboardingController["addSource"]
  onUpdateSource: OnboardingController["editSource"]
  onUpdateField: OnboardingController["editPolicyField"]
  onUpdateApproval: OnboardingController["updateApprovalItem"]
  onPreviewDecision: OnboardingController["decidePreview"]
  onAddCustomPreview: OnboardingController["addCustomPreview"]
  onConfirmRevision: OnboardingController["confirmRevision"]
  onDiscardRevision: OnboardingController["discardRevision"]
  isAddingSource: boolean
  updatingSourceId: string | null
  updatingFieldId: string | null
  updatingApprovalItemId: string | null
  updatingPreviewId: string | null
  isAddingCustomPreview: boolean
  isResolvingRevision: boolean
}) {
  const { session } = controller

  if (stage === "sources") {
    return (
      <SourceInventory
        items={session?.source_inventory ?? []}
        blockers={session?.release_blockers.source_inventory ?? []}
        isAdding={isAddingSource}
        updatingSourceId={updatingSourceId}
        onAddSource={onAddSource}
        onUpdateSource={onUpdateSource}
      />
    )
  }

  if (stage === "preview") {
    return (
      <div className="flex flex-col gap-4 p-5 sm:p-6">
        {session?.revision_proposal ? (
          <RevisionProposalPanel
            session={session}
            isResolvingRevision={isResolvingRevision}
            onConfirm={onConfirmRevision}
            onDiscard={onDiscardRevision}
          />
        ) : null}
        <PreviewComparison
          previewCases={session?.preview_cases ?? []}
          updatingPreviewId={updatingPreviewId}
          isAddingCustomPreview={isAddingCustomPreview}
          onPreviewDecision={onPreviewDecision}
          onAddCustomPreview={onAddCustomPreview}
        />
      </div>
    )
  }

  if (stage === "approval") {
    return (
      <ApprovalChecklist
        items={session?.approval_checklist ?? []}
        releaseStatus={session?.policy?.release_status ?? "draft"}
        updatingItemId={updatingApprovalItemId}
        onUpdateItem={onUpdateApproval}
      />
    )
  }

  return (
    <PolicyReview
      policy={session?.policy ?? null}
      updatingFieldId={updatingFieldId}
      onUpdateField={onUpdateField}
    />
  )
}

function ReleaseBar({
  blockers,
  nextActionTitle,
  onOpenNext,
}: {
  blockers: string[]
  nextActionTitle: string
  onOpenNext: () => void
}) {
  if (blockers.length === 0) {
    return (
      <div className="flex min-h-12 items-center gap-2 border-t bg-[var(--success-soft)] px-4 text-sm text-[var(--success)] sm:px-6">
        <span className="size-2 rounded-full bg-current" aria-hidden="true" />
        All release conditions are clear.
      </div>
    )
  }

  return (
    <div className="flex min-h-12 items-center gap-3 overflow-x-auto border-t bg-[var(--shell)] px-3 text-sm sm:px-5">
      <button
        type="button"
        onClick={onOpenNext}
        className="flex shrink-0 items-center gap-2 rounded-lg px-2 py-1.5 font-semibold text-[var(--warning)] outline-none hover:bg-[var(--warning-soft)] focus-visible:ring-2 focus-visible:ring-ring/30"
      >
        <AlertCircle className="size-4" aria-hidden="true" />
        {blockers.length} blocker{blockers.length === 1 ? "" : "s"}
      </button>
      <span className="hidden h-5 w-px shrink-0 bg-border sm:block" aria-hidden="true" />
      <div className="hidden min-w-[240px] flex-1 items-center gap-4 overflow-hidden text-xs text-muted-foreground sm:flex">
        {blockers.slice(0, 2).map((blocker) => (
          <span
            key={blocker}
            className="flex min-w-0 items-center gap-2"
          >
            <span
              className="size-1.5 shrink-0 rounded-full bg-[var(--destructive-ink)]"
              aria-hidden="true"
            />
            <span className="truncate">{formatBlockerLabel(blocker)}</span>
          </span>
        ))}
        {blockers.length > 2 ? (
          <span className="shrink-0">+{blockers.length - 2} more</span>
        ) : null}
      </div>
      <Button type="button" variant="link" size="sm" className="shrink-0" onClick={onOpenNext}>
        <span className="sm:hidden">Review</span>
        <span className="hidden sm:inline">{nextActionTitle}</span>
      </Button>
    </div>
  )
}

function formatBlockerLabel(blocker: string): string {
  if (!blocker.includes("_") && !blocker.includes("-")) {
    return blocker
  }

  const label = blocker.replaceAll("_", " ").replaceAll("-", " ")
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`
}

function capitalize(value: string): string {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`
}
