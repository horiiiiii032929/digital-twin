import {
  AlertCircle,
  Bot,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  FileText,
  GitBranch,
  MessageSquareText,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react"

import { ApprovalChecklist } from "@/components/onboarding/approval-checklist"
import {
  ReadinessMetric,
  ReadinessSummary,
  StepStatusCard,
  WorkbenchHeader,
} from "@/components/onboarding/console/readiness-summary"
import { RevisionProposalPanel } from "@/components/onboarding/console/revision-proposal-panel"
import { OnboardingChat } from "@/components/onboarding/onboarding-chat"
import { PolicyReview } from "@/components/onboarding/policy-review"
import { PreviewComparison } from "@/components/onboarding/preview-comparison"
import { SourceInventory } from "@/components/onboarding/source-inventory"
import { WorkflowTrace } from "@/components/onboarding/workflow-trace"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { OnboardingController } from "@/hooks/use-onboarding-session"
import {
  formatReleaseStatus,
  formatStep,
  getNextAction,
  getReleaseReadiness,
  getStepStates,
} from "@/lib/onboarding/readiness"
import { cn } from "@/lib/utils"

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
                <Badge variant="outline">
                  {formatStep(session?.current_step ?? "starting")}
                </Badge>
              </div>
              <div className="grid gap-2">
                {stepStates.map((step) => (
                  <StepStatusCard key={step.id} step={step} />
                ))}
              </div>
            </section>

            <ReadinessSummary readiness={releaseReadiness} />
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
                      badge={
                        session?.policy ? "policy generated" : "collecting answers"
                      }
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
