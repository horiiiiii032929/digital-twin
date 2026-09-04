/**
 * THESIS: Conversation is the professor's stable setup home; structured stages
 * open as accountable context instead of becoming a horizontal admin wizard.
 * OWN-WORLD: A 216px cool-neutral rail, true-white chat canvas, charcoal
 * actions, restrained iris focus, compact controls, and one elevated composer.
 * STORY: Continue the interview, open a setup stage, resolve blockers, inspect
 * evidence, preview behavior, and retain explicit release authority.
 * FIRST VIEWPORT: Setup rail, wide conversation, compact course/status header,
 * and an optional 400px inspector that never replaces the transcript.
 * FORM: User-delegated familiar-LLM canon, accepted composition C in
 * reports/generated/ui-redesign-product-wide/composition-c-accepted.png.
 */

import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react"
import {
  Activity,
  AlertCircle,
  BookOpen,
  FlaskConical,
  Menu,
  PackageCheck,
  PanelRightClose,
  PanelRightOpen,
  X,
} from "lucide-react"
import { Dialog as DialogPrimitive } from "radix-ui"

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
import { WorkspaceBrand } from "@/components/workspace/workspace-brand"
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
  interview: "Interview",
  policy: "Tutor policy",
  preview: "Preview",
  approval: "Approval",
}

type InspectorMode = ReviewStageId | "activity"
const STUDENT_TUTOR_LINK_AVAILABLE =
  import.meta.env.VITE_AUTH_MODE !== "session"

export function ProfessorReviewConsole({
  controller,
  supervisorDemo = false,
  onOpenDelivery,
}: {
  controller: OnboardingController
  supervisorDemo?: boolean
  onOpenDelivery?: () => void
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
    selectRevisionOption,
  } = controller
  const [activeStage, setActiveStage] = useState<ReviewStageId>(
    supervisorDemo ? "policy" : "interview",
  )
  const [inspectorMode, setInspectorMode] = useState<InspectorMode>(
    supervisorDemo ? "policy" : "interview",
  )
  const [desktopInspectorOpen, setDesktopInspectorOpen] = useState(true)
  const [mobileInspectorOpen, setMobileInspectorOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const mobileMenuTriggerRef = useRef<HTMLButtonElement | null>(null)
  const mobileInspectorTriggerRef = useRef<HTMLButtonElement | null>(null)
  const inspectorOpeningFromMenuRef = useRef(false)
  const releaseReadiness = getReleaseReadiness(session)
  const stepStates = getStepStates(session)
  const nextAction = getNextAction(session, releaseReadiness.blockers)

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 1024px)")
    const closeMobileSurfacesOnDesktop = (event: MediaQueryListEvent) => {
      if (!event.matches) return
      inspectorOpeningFromMenuRef.current = false
      setMobileMenuOpen(false)
      setMobileInspectorOpen(false)
    }
    desktop.addEventListener("change", closeMobileSurfacesOnDesktop)
    return () => desktop.removeEventListener("change", closeMobileSurfacesOnDesktop)
  }, [])

  const openStage = (stage: ReviewStageId) => {
    setActiveStage(stage)
    setInspectorMode(stage)
    openInspectorForViewport()
  }

  const openActivity = () => {
    setInspectorMode("activity")
    openInspectorForViewport()
  }

  const openInspectorForViewport = () => {
    if (window.matchMedia("(min-width: 1024px)").matches) {
      setDesktopInspectorOpen(true)
    } else {
      if (mobileMenuOpen) inspectorOpeningFromMenuRef.current = true
      setMobileInspectorOpen(true)
    }
    setMobileMenuOpen(false)
  }

  const toggleInspector = () => {
    if (window.matchMedia("(min-width: 1024px)").matches) {
      setDesktopInspectorOpen((open) => !open)
    } else {
      setMobileInspectorOpen(true)
    }
  }

  const renderInspectorContent = () =>
    inspectorMode === "activity" ? (
      <ReviewContext session={session} readiness={releaseReadiness} />
    ) : (
      <StageTool
        stage={inspectorMode}
        controller={controller}
        onAddSource={addSource}
        onUpdateSource={editSource}
        onUpdateField={editPolicyField}
        onUpdateApproval={updateApprovalItem}
        onPreviewDecision={decidePreview}
        onAddCustomPreview={addCustomPreview}
        onConfirmRevision={confirmRevision}
        onDiscardRevision={discardRevision}
        onSelectRevisionOption={selectRevisionOption}
        isAddingSource={isAddingSource}
        updatingSourceId={updatingSourceId}
        updatingFieldId={updatingFieldId}
        updatingApprovalItemId={updatingApprovalItemId}
        updatingPreviewId={updatingPreviewId}
        isAddingCustomPreview={isAddingCustomPreview}
        isResolvingRevision={isResolvingRevision}
      />
    )

  return (
    <main className="h-dvh min-w-0 overflow-hidden bg-white text-foreground">
      <div
        className={cn(
          "grid h-full min-h-0 min-w-0 lg:overflow-hidden",
          desktopInspectorOpen
            ? "lg:grid-cols-[216px_minmax(0,1fr)_400px]"
            : "lg:grid-cols-[216px_minmax(0,1fr)]",
        )}
      >
        <aside className="hidden min-h-0 flex-col border-r bg-[var(--shell)] lg:flex">
          <WorkspaceBrand />
          <div className="px-3 pt-3">
            <Button
              type="button"
              className="w-full"
              onClick={() => openStage(nextAction.stage)}
            >
              Continue setup
            </Button>
          </div>
          <ReleaseRoute
            steps={stepStates}
            selectedStage={inspectorMode === "activity" ? undefined : activeStage}
            collapsed={false}
            onSelectStage={openStage}
          />

          <div className="mt-auto space-y-1 border-t p-3">
            {onOpenDelivery ? (
              <Button
                type="button"
                variant="ghost"
                className="w-full justify-start"
                onClick={onOpenDelivery}
              >
                <PackageCheck data-icon="inline-start" />
                Course delivery
              </Button>
            ) : null}
            <Button
              type="button"
              variant="ghost"
              className={cn(
                "w-full justify-start",
                releaseReadiness.blockers.length > 0
                  ? "text-[var(--warning)] hover:bg-[var(--warning-soft)] hover:text-[var(--warning)]"
                  : "text-[var(--success)] hover:bg-[var(--success-soft)] hover:text-[var(--success)]",
              )}
              onClick={openActivity}
            >
              <AlertCircle data-icon="inline-start" />
              {releaseReadiness.blockers.length} blocker
              {releaseReadiness.blockers.length === 1 ? "" : "s"}
            </Button>
            {STUDENT_TUTOR_LINK_AVAILABLE ? (
              <Button asChild variant="ghost" className="w-full justify-start">
                <a href="/student">
                  <BookOpen data-icon="inline-start" />
                  Student tutor
                </a>
              </Button>
            ) : null}
          </div>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-col bg-white">
          <ProfessorHeader
            status={formatReleaseStatus(releaseReadiness.status)}
            blockerCount={releaseReadiness.blockers.length}
            inspectorOpen={desktopInspectorOpen}
            menuTriggerRef={mobileMenuTriggerRef}
            inspectorTriggerRef={mobileInspectorTriggerRef}
            onOpenMenu={() => setMobileMenuOpen(true)}
            onToggleInspector={toggleInspector}
          />

          {supervisorDemo ? (
            <div className="border-b bg-[var(--accent-soft)] px-4 py-2.5 text-[var(--accent-foreground)] sm:px-5">
              <div className="mx-auto flex max-w-3xl items-start gap-2.5 text-xs leading-5">
                <FlaskConical className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                <p className="min-w-0 flex-1">
                  <strong className="font-semibold">Synthetic supervisor demo.</strong>{" "}
                  The completed interview and source entry contain no private course
                  files or student records.
                </p>
                <a
                  href="/"
                  className="shrink-0 font-semibold underline underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
                >
                  Start empty
                </a>
              </div>
            </div>
          ) : null}

          {error ? (
            <div className="px-4 pt-4 sm:px-6">
              <Alert variant="destructive">
                <AlertCircle />
                <AlertTitle>Setup request failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            </div>
          ) : null}

          <section aria-label="Setup conversation" className="min-h-0 min-w-0 flex-1 bg-white">
            <OnboardingChat
              messages={session?.messages ?? []}
              currentStep={session?.current_step ?? "starting"}
              isLoading={isStarting}
              isSubmitting={isSubmitting}
              onSendMessage={sendMessage}
              onRestart={restart}
            />
          </section>
        </section>

        {desktopInspectorOpen ? (
          <ProfessorInspector
            key={inspectorMode}
            title={inspectorMode === "activity" ? "Activity" : TOOL_TITLES[inspectorMode]}
            className="hidden border-l lg:flex"
            onClose={() => setDesktopInspectorOpen(false)}
          >
            {renderInspectorContent()}
          </ProfessorInspector>
        ) : null}
      </div>

      <ProfessorMobileMenu
        open={mobileMenuOpen}
        steps={stepStates}
        selectedStage={inspectorMode === "activity" ? undefined : activeStage}
        blockerCount={releaseReadiness.blockers.length}
        onOpenChange={setMobileMenuOpen}
        triggerRef={mobileMenuTriggerRef}
        inspectorOpeningRef={inspectorOpeningFromMenuRef}
        onSelectStage={openStage}
        onOpenActivity={openActivity}
        onOpenDelivery={onOpenDelivery}
      />

      <DialogPrimitive.Root
        open={mobileInspectorOpen}
        onOpenChange={setMobileInspectorOpen}
      >
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-20 bg-black/15 lg:hidden" />
          <DialogPrimitive.Content
            onCloseAutoFocus={(event) => {
              event.preventDefault()
              mobileInspectorTriggerRef.current?.focus()
            }}
            className="fixed inset-x-0 bottom-0 z-30 flex max-h-[84dvh] min-h-[52dvh] flex-col overflow-hidden rounded-t-2xl border-t bg-white shadow-[0_-12px_40px_rgba(32,33,35,0.14)] outline-none lg:hidden"
          >
            <DialogPrimitive.Title className="sr-only">
              {inspectorMode === "activity" ? "Activity" : TOOL_TITLES[inspectorMode]}
            </DialogPrimitive.Title>
            <div
              aria-hidden="true"
              className="absolute top-2 left-1/2 z-10 h-1 w-9 -translate-x-1/2 rounded-full bg-[var(--rule-strong)]"
            />
            <ProfessorInspector
              key={inspectorMode}
              title={inspectorMode === "activity" ? "Activity" : TOOL_TITLES[inspectorMode]}
              className="flex min-h-0 flex-1"
              onClose={() => setMobileInspectorOpen(false)}
            >
              {renderInspectorContent()}
            </ProfessorInspector>
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
    </main>
  )
}

function ProfessorHeader({
  status,
  blockerCount,
  inspectorOpen,
  menuTriggerRef,
  inspectorTriggerRef,
  onOpenMenu,
  onToggleInspector,
}: {
  status: string
  blockerCount: number
  inspectorOpen: boolean
  menuTriggerRef: RefObject<HTMLButtonElement | null>
  inspectorTriggerRef: RefObject<HTMLButtonElement | null>
  onOpenMenu: () => void
  onToggleInspector: () => void
}) {
  return (
    <header className="flex min-h-14 items-center justify-between gap-3 border-b bg-white px-3 sm:px-5">
      <div className="flex min-w-0 items-center gap-2.5">
        <Button
          ref={menuTriggerRef}
          type="button"
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label="Open setup navigation"
          onClick={onOpenMenu}
        >
          <Menu aria-hidden="true" />
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold tracking-[-0.015em] sm:text-base">
            Tutor setup
          </h1>
          <span
            className={cn(
              "block truncate text-xs font-medium sm:hidden",
              blockerCount > 0 ? "text-[var(--warning)]" : "text-[var(--success)]",
            )}
          >
            {capitalize(status)}
            {blockerCount > 0
              ? ` · ${blockerCount} blocker${blockerCount === 1 ? "" : "s"}`
              : ""}
          </span>
        </div>
        <span
          className={cn(
            "hidden items-center gap-1.5 text-xs font-medium sm:inline-flex",
            blockerCount > 0 ? "text-[var(--warning)]" : "text-[var(--success)]",
          )}
        >
          <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
          {capitalize(status)}
          {blockerCount > 0
            ? ` · ${blockerCount} blocker${blockerCount === 1 ? "" : "s"}`
            : ""}
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        {STUDENT_TUTOR_LINK_AVAILABLE ? (
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <a href="/student" aria-label="Open student tutor">
              <BookOpen data-icon="inline-start" />
              Student tutor
            </a>
          </Button>
        ) : null}
        <Button
          ref={inspectorTriggerRef}
          type="button"
          variant="outline"
          size="sm"
          className="lg:hidden"
          aria-label="Open setup inspector"
          onClick={onToggleInspector}
        >
          <PanelRightOpen data-icon="inline-start" />
          Setup
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="hidden lg:inline-flex"
          aria-label={inspectorOpen ? "Close setup inspector" : "Open setup inspector"}
          aria-pressed={inspectorOpen}
          onClick={onToggleInspector}
        >
          {inspectorOpen ? (
            <PanelRightClose data-icon="inline-start" />
          ) : (
            <PanelRightOpen data-icon="inline-start" />
          )}
          Setup
        </Button>
      </div>
    </header>
  )
}

function ProfessorInspector({
  title,
  className,
  onClose,
  children,
}: {
  title: string
  className?: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <aside
      aria-label={`${title} inspector`}
      className={cn("relative min-h-0 min-w-0 flex-col overflow-y-auto bg-white", className)}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute top-2.5 right-2.5 z-10 size-9 bg-white/95"
        aria-label={`Close ${title.toLowerCase()} inspector`}
        onClick={onClose}
      >
        <X aria-hidden="true" />
      </Button>
      {children}
    </aside>
  )
}

function ProfessorMobileMenu({
  open,
  steps,
  selectedStage,
  blockerCount,
  onOpenChange,
  triggerRef,
  inspectorOpeningRef,
  onSelectStage,
  onOpenActivity,
  onOpenDelivery,
}: {
  open: boolean
  steps: ReturnType<typeof getStepStates>
  selectedStage?: ReviewStageId
  blockerCount: number
  onOpenChange: (open: boolean) => void
  triggerRef: RefObject<HTMLButtonElement | null>
  inspectorOpeningRef: RefObject<boolean>
  onSelectStage: (stage: ReviewStageId) => void
  onOpenActivity: () => void
  onOpenDelivery?: () => void
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-20 bg-black/15 lg:hidden" />
        <DialogPrimitive.Content
          onCloseAutoFocus={(event) => {
            event.preventDefault()
            if (inspectorOpeningRef.current) {
              inspectorOpeningRef.current = false
              return
            }
            triggerRef.current?.focus()
          }}
          className="fixed inset-y-0 left-0 z-30 flex w-[min(88vw,320px)] flex-col border-r bg-[var(--shell)] shadow-[12px_0_40px_rgba(32,33,35,0.12)] outline-none lg:hidden"
        >
          <DialogPrimitive.Title className="sr-only">
            Tutor setup navigation
          </DialogPrimitive.Title>
          <WorkspaceBrand className="pr-14" />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute top-2.5 right-2.5"
            aria-label="Close setup navigation"
            onClick={() => onOpenChange(false)}
          >
            <X aria-hidden="true" />
          </Button>
          <ReleaseRoute
            steps={steps}
            selectedStage={selectedStage}
            collapsed={false}
            onSelectStage={onSelectStage}
          />
          <div className="mt-auto space-y-1 border-t p-3">
            {onOpenDelivery ? (
              <Button
                type="button"
                variant="ghost"
                className="w-full justify-start"
                onClick={() => {
                  onOpenChange(false)
                  onOpenDelivery()
                }}
              >
                <PackageCheck data-icon="inline-start" />
                Course delivery
              </Button>
            ) : null}
            <Button
              type="button"
              variant="ghost"
              className={cn(
                "w-full justify-start",
                blockerCount > 0 ? "text-[var(--warning)]" : "text-[var(--success)]",
              )}
              onClick={onOpenActivity}
            >
              <Activity data-icon="inline-start" />
              {blockerCount} blocker{blockerCount === 1 ? "" : "s"}
            </Button>
            {STUDENT_TUTOR_LINK_AVAILABLE ? (
              <Button asChild variant="ghost" className="w-full justify-start">
                <a href="/student">
                  <BookOpen data-icon="inline-start" />
                  Student tutor
                </a>
              </Button>
            ) : null}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
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
  onSelectRevisionOption,
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
  onSelectRevisionOption: OnboardingController["selectRevisionOption"]
  isAddingSource: boolean
  updatingSourceId: string | null
  updatingFieldId: string | null
  updatingApprovalItemId: string | null
  updatingPreviewId: string | null
  isAddingCustomPreview: boolean
  isResolvingRevision: boolean
}) {
  const { session } = controller

  if (stage === "interview") {
    return (
      <section className="p-5 sm:p-6">
        <header className="border-b pb-5 pr-10">
          <h2 className="text-lg font-semibold tracking-[-0.02em]">Interview</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Shape the tutor through the setup conversation.
          </p>
        </header>
        <div className="space-y-6 pt-6">
          <section>
            <h3 className="text-sm font-semibold">About this stage</h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Your answers define the course scope, teaching approach, academic
              integrity boundaries, misconception handling, and approval criteria.
            </p>
          </section>
          <section>
            <h3 className="text-sm font-semibold">Current interview section</h3>
            <p className="mt-2 rounded-lg bg-[var(--accent-soft)] px-3 py-2.5 text-sm font-medium text-[var(--accent-strong)]">
              {formatInterviewStep(session?.current_step ?? "starting")}
            </p>
          </section>
          <p className="border-t pt-5 text-xs leading-5 text-muted-foreground">
            Continue in the conversation. The draft policy remains reviewable
            before any release decision.
          </p>
        </div>
      </section>
    )
  }

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
            onSelect={onSelectRevisionOption}
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

function capitalize(value: string): string {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`
}

function formatInterviewStep(step: string): string {
  if (step === "starting") return "Starting setup"
  const label = step.replaceAll("_", " ").replaceAll("-", " ")
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`
}
