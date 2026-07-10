import {
  CheckCircle2,
  Circle,
  ClipboardCheck,
  FileSearch,
  FileText,
  MessageSquareText,
  ShieldCheck,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type {
  ReleaseReadiness,
  StepState,
} from "@/lib/onboarding/readiness"
import { formatReleaseStatus } from "@/lib/onboarding/readiness"
import { cn } from "@/lib/utils"

const STEP_ICONS = {
  sources: FileText,
  interview: MessageSquareText,
  policy: ShieldCheck,
  preview: FileSearch,
  approval: ClipboardCheck,
}

export function ReadinessSummary({
  readiness,
}: {
  readiness: ReleaseReadiness
}) {
  return (
    <section className="rounded-xl border bg-background p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">Gate summary</h2>
        <Badge
          variant={readiness.status === "approved" ? "default" : "outline"}
        >
          {formatReleaseStatus(readiness.status)}
        </Badge>
      </div>
      <div className="grid gap-2 text-sm">
        <SummaryLine label="Approved sources" value={readiness.approvedSources} />
        <SummaryLine label="Policy blockers" value={readiness.policyBlockers} />
        <SummaryLine label="Pending previews" value={readiness.pendingPreviews} />
        <SummaryLine
          label="Checklist blockers"
          value={readiness.checklistBlockers}
        />
      </div>
    </section>
  )
}

export function ReadinessMetric({
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

export function StepStatusCard({ step }: { step: StepState }) {
  const Icon = STEP_ICONS[step.id]

  return (
    <div
      className={cn(
        "grid grid-cols-[auto_minmax(0,1fr)] gap-3 rounded-lg border p-3 text-sm",
        step.state === "active" && "border-sky-200 bg-sky-50 text-sky-950",
        step.state === "complete" &&
          "border-emerald-200 bg-emerald-50 text-emerald-950",
        step.state === "blocked" &&
          "border-amber-200 bg-amber-50 text-amber-950",
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

export function WorkbenchHeader({
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

function SummaryLine({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-muted/50 px-3 py-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  )
}
