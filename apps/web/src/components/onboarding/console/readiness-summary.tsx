import { Check, Circle, CircleAlert } from "lucide-react"

import type { ReviewStageId, StepState } from "@/lib/onboarding/readiness"
import { cn } from "@/lib/utils"

const STEP_STATE_LABELS: Record<StepState["state"], string> = {
  active: "In progress",
  blocked: "Blocked",
  complete: "Complete",
  waiting: "Not started",
}

const STEP_HELP: Record<ReviewStageId, string> = {
  sources: "Add and verify materials",
  interview: "Shape the tutor with AI",
  policy: "Define behavior and rules",
  preview: "Test tutor responses",
  approval: "Review and release",
}

export function ReleaseRoute({
  steps,
  selectedStage,
  collapsed,
  onSelectStage,
}: {
  steps: StepState[]
  selectedStage?: ReviewStageId
  collapsed: boolean
  onSelectStage: (stage: ReviewStageId) => void
}) {
  return (
    <nav aria-label="Tutor setup stages" className="min-w-0 px-2 py-4">
      {collapsed ? null : (
        <h2 className="px-2 pb-2.5 text-xs font-semibold text-muted-foreground">
          Release workflow
        </h2>
      )}

      <ol className="flex flex-col gap-1">
        {steps.map((step, index) => (
          <li key={step.id}>
            <button
              type="button"
              onClick={() => onSelectStage(step.id)}
              aria-current={selectedStage === step.id ? "step" : undefined}
              aria-label={`${step.label}, ${STEP_HELP[step.id]}, ${STEP_STATE_LABELS[step.state]}`}
              className={cn(
                "group flex min-h-12 w-full items-start gap-2.5 rounded-xl px-2.5 py-2 text-left text-sm outline-none transition-colors hover:bg-white/80 focus-visible:ring-2 focus-visible:ring-ring/30",
                selectedStage === step.id &&
                  "bg-white shadow-[0_1px_2px_rgba(25,25,29,0.06),0_5px_14px_rgba(25,25,29,0.04)]",
                collapsed && "justify-center px-0",
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                  selectedStage === step.id
                    ? "border-[var(--accent-strong)] bg-[var(--accent-strong)] text-white"
                    : "border-[var(--border-strong)] bg-white text-muted-foreground",
                )}
              >
                {index + 1}
              </span>

              {collapsed ? null : (
                <span className="min-w-0 flex-1">
                  <span
                    className={cn(
                      "block truncate font-semibold",
                      selectedStage === step.id && "text-[var(--accent-strong)]",
                    )}
                  >
                    {step.label}
                  </span>
                  <span className="mt-0.5 block truncate text-xs leading-4 text-muted-foreground">
                    {STEP_HELP[step.id]}
                  </span>
                </span>
              )}

              {collapsed ? null : (
                <span className="mt-0.5">
                  <StepStateIcon state={step.state} />
                </span>
              )}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}

function StepStateIcon({ state }: { state: StepState["state"] }) {
  if (state === "complete") {
    return <Check className="size-4 shrink-0 text-[var(--success)]" aria-hidden="true" />
  }
  if (state === "blocked") {
    return <CircleAlert className="size-4 shrink-0 text-[var(--warning)]" aria-hidden="true" />
  }
  return (
    <Circle
      className={cn(
        "size-3.5 shrink-0",
        state === "active" ? "fill-[var(--accent-strong)] text-[var(--accent-strong)]" : "text-[var(--border-strong)]",
      )}
      aria-hidden="true"
    />
  )
}
