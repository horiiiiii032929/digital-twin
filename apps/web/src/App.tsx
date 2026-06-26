import { AlertCircle, Bot, GitBranch, ShieldCheck } from "lucide-react"

import { ApprovalChecklist } from "@/components/onboarding/approval-checklist"
import { OnboardingChat } from "@/components/onboarding/onboarding-chat"
import { PolicyReview } from "@/components/onboarding/policy-review"
import { PreviewComparison } from "@/components/onboarding/preview-comparison"
import { WorkflowTrace } from "@/components/onboarding/workflow-trace"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useOnboardingSession } from "@/hooks/use-onboarding-session"

function App() {
  const {
    session,
    error,
    isStarting,
    isSubmitting,
    updatingFieldId,
    restart,
    sendMessage,
    editPolicyField,
  } = useOnboardingSession()

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-foreground">
      <div className="mx-auto flex min-h-screen max-w-[1480px] flex-col gap-4 px-4 py-4 lg:px-6">
        <header className="flex flex-col gap-3 rounded-lg border bg-background px-4 py-3 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <Badge variant="secondary" className="gap-1.5">
                <Bot className="size-3.5" />
                Digital Twin
              </Badge>
              <Badge variant="outline" className="gap-1.5">
                <GitBranch className="size-3.5" />
                Sprint 1
              </Badge>
            </div>
            <h1 className="text-xl font-semibold tracking-normal">
              Minimal Chat-Led Onboarding Prototype
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Interview the instructor, generate a draft tutor policy, and review
              release blockers before student exposure.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-lg border bg-sky-50 px-3 py-2 text-sm text-sky-900">
            <ShieldCheck className="size-4 shrink-0" />
            Draft-only until professor approval
          </div>
        </header>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertTitle>Onboarding request failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_460px]">
          <section className="flex min-h-[680px] flex-col overflow-hidden rounded-lg border bg-background">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3">
              <div>
                <h2 className="text-sm font-semibold">Instructor Interview</h2>
                <p className="text-xs text-muted-foreground">
                  Current step:{" "}
                  <span className="font-medium">
                    {formatStep(session?.current_step ?? "starting")}
                  </span>
                </p>
              </div>
              <Badge variant={session?.policy ? "default" : "outline"}>
                {session?.policy ? "policy generated" : "collecting answers"}
              </Badge>
            </div>
            <OnboardingChat
              messages={session?.messages ?? []}
              currentStep={session?.current_step ?? "starting"}
              isLoading={isStarting}
              isSubmitting={isSubmitting}
              onSendMessage={sendMessage}
              onRestart={restart}
            />
          </section>

          <aside className="grid gap-4 lg:max-h-[calc(100vh-7.5rem)] lg:overflow-auto lg:pr-1">
            <WorkflowTrace trace={session?.trace ?? []} />
            <PolicyReview
              policy={session?.policy ?? null}
              updatingFieldId={updatingFieldId}
              onUpdateField={editPolicyField}
            />
            <Separator />
            <PreviewComparison previewCases={session?.preview_cases ?? []} />
            <ApprovalChecklist items={session?.approval_checklist ?? []} />
          </aside>
        </div>
      </div>
    </main>
  )
}

function formatStep(step: string): string {
  return step.replaceAll("_", " ")
}

export default App
