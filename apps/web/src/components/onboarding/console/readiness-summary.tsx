import {
  Check,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  FileSearch,
  FileText,
  MessageSquareText,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { ReviewStageId, StepState } from "@/lib/onboarding/readiness"
import { formatStep } from "@/lib/onboarding/readiness"
import { cn } from "@/lib/utils"

const STEP_ICONS = {
  sources: FileText,
  interview: MessageSquareText,
  policy: ShieldCheck,
  preview: FileSearch,
  approval: ClipboardCheck,
}

const STEP_STATE_LABELS: Record<StepState["state"], string> = {
  active: "In progress",
  blocked: "Blocked",
  complete: "Complete",
  waiting: "Waiting",
}

export function ReleaseRoute({
  steps,
  currentStep,
  selectedStage,
  onSelectStage,
}: {
  steps: StepState[]
  currentStep: string
  selectedStage: ReviewStageId
  onSelectStage: (stage: ReviewStageId) => void
}) {
  return (
    <nav aria-label="Professor review stages" className="min-w-0">
      <div className="mb-2 flex items-end justify-between gap-3 px-4 pt-3 sm:mb-4 sm:pt-4 xl:px-5 xl:pt-5">
        <div>
          <div className="dossier-label">Release route</div>
          <h2 className="mt-0.5 text-sm font-semibold tracking-[-0.01em] sm:mt-1 sm:text-[15px]">
            Five review gates
          </h2>
        </div>
        <span className="text-xs text-muted-foreground xl:hidden">
          {formatStep(currentStep)}
        </span>
      </div>

      <ol className="grid grid-flow-col auto-cols-[minmax(184px,1fr)] gap-2 overflow-x-auto px-4 pb-4 xl:grid-flow-row xl:auto-cols-auto xl:grid-cols-1 xl:gap-0 xl:overflow-visible xl:px-0 xl:pb-0">
        {steps.map((step, index) => (
          <li key={step.id} className="min-w-0">
            <StepStatusCard
              step={step}
              index={index + 1}
              selected={selectedStage === step.id}
              onSelect={() => onSelectStage(step.id)}
            />
          </li>
        ))}
      </ol>

      <div className="hidden border-t px-5 py-4 xl:block">
        <div className="dossier-label">Session position</div>
        <p className="mt-1 text-sm font-medium">{formatStep(currentStep)}</p>
      </div>
    </nav>
  )
}

export function StepStatusCard({
  step,
  index,
  selected,
  onSelect,
}: {
  step: StepState
  index: number
  selected: boolean
  onSelect: () => void
}) {
  const Icon = STEP_ICONS[step.id]

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected ? "step" : undefined}
      className={cn(
        "group grid min-h-16 w-full grid-cols-[28px_minmax(0,1fr)] gap-3 border px-3 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--cobalt)] sm:min-h-[88px] xl:min-h-0 xl:border-x-0 xl:border-b-0 xl:border-t xl:px-5 xl:py-4",
        selected
          ? "border-[#b9cdfb] bg-[var(--cobalt-soft)] text-[var(--ink)] xl:border-l-2 xl:border-l-[var(--cobalt)]"
          : "border-[var(--rule)] bg-white hover:bg-[var(--workspace)] xl:border-l-2 xl:border-l-transparent",
      )}
    >
      <span
        className={cn(
          "dossier-label mt-0.5",
          selected ? "text-[var(--cobalt)]" : "text-muted-foreground",
        )}
      >
        {String(index).padStart(2, "0")}
      </span>
      <span className="min-w-0">
        <span className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold">{step.label}</span>
          <StepIcon state={step.state} fallback={Icon} />
        </span>
        <span className="mt-1 hidden text-xs leading-5 text-muted-foreground xl:block">
          {step.detail}
        </span>
        <span
          className={cn(
            "mt-1 inline-flex items-center gap-1.5 text-[11px] font-semibold xl:mt-2",
            step.state === "complete" && "text-[var(--success)]",
            step.state === "blocked" && "text-[var(--destructive)]",
            step.state === "active" && "text-[var(--cobalt)]",
            step.state === "waiting" && "text-muted-foreground",
          )}
        >
          {STEP_STATE_LABELS[step.state]}
        </span>
      </span>
    </button>
  )
}

export function WorkbenchHeader({
  index,
  title,
  detail,
  badge,
}: {
  index: string
  title: string
  detail: string
  badge: string
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3 sm:gap-4 sm:px-6 sm:py-5">
      <div className="flex min-w-0 gap-3">
        <span className="dossier-label mt-1 text-[var(--cobalt)]">{index}</span>
        <div>
          <h2 className="text-base font-semibold tracking-[-0.02em] sm:text-lg">
            {title}
          </h2>
          <p className="mt-1 hidden max-w-2xl text-sm leading-6 text-muted-foreground sm:block">
            {detail}
          </p>
        </div>
      </div>
      <Badge variant="outline" className="status-badge">
        {badge}
      </Badge>
    </header>
  )
}

function StepIcon({
  state,
  fallback: Fallback,
}: {
  state: StepState["state"]
  fallback: typeof FileText
}) {
  if (state === "complete") {
    return <Check className="size-4 text-[var(--success)]" aria-hidden="true" />
  }
  if (state === "blocked") {
    return (
      <ShieldAlert
        className="size-4 text-[var(--destructive)]"
        aria-hidden="true"
      />
    )
  }
  if (state === "waiting") {
    return <Circle className="size-3.5 text-muted-foreground" aria-hidden="true" />
  }
  return <Fallback className="size-4 text-[var(--cobalt)]" aria-hidden="true" />
}

export function ReleaseStateIcon({ clear }: { clear: boolean }) {
  return clear ? (
    <CheckCircle2 className="size-4" aria-hidden="true" />
  ) : (
    <ShieldAlert className="size-4" aria-hidden="true" />
  )
}
