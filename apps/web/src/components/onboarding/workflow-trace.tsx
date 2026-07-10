import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  CircleStop,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
} from "@/components/ui/chain-of-thought"
import type { TraceStatus, WorkflowTraceItem } from "@/lib/api/types"
import { cn } from "@/lib/utils"

type WorkflowTraceProps = {
  trace: WorkflowTraceItem[]
}

export function WorkflowTrace({ trace }: WorkflowTraceProps) {
  return (
    <section className="rounded-lg border bg-card p-4 text-card-foreground">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Workflow Trace</h2>
          <p className="text-xs text-muted-foreground">
            LangGraph step events and guardrail outcomes.
          </p>
        </div>
        <Badge variant="outline">{trace.length} events</Badge>
      </div>

      {trace.length === 0 ? (
        <EmptyState label="Trace events appear after the session starts." />
      ) : (
        <ChainOfThought>
          {trace.map((item, index) => (
            <ChainOfThoughtStep
              key={item.id}
              defaultOpen={index === trace.length - 1}
            >
              <ChainOfThoughtTrigger leftIcon={<StatusIcon status={item.status} />}>
                <span className="flex flex-wrap items-center gap-2">
                  {item.title}
                  <TraceBadge status={item.status} />
                </span>
              </ChainOfThoughtTrigger>
              <ChainOfThoughtContent>
                <ChainOfThoughtItem>{item.detail}</ChainOfThoughtItem>
              </ChainOfThoughtContent>
            </ChainOfThoughtStep>
          ))}
        </ChainOfThought>
      )}
    </section>
  )
}

function TraceBadge({ status }: { status: TraceStatus }) {
  const label =
    status === "complete"
      ? "complete"
      : status === "warning"
        ? "review"
        : "blocked"

  return (
    <span
      className={cn(
        "rounded-md border px-1.5 py-0.5 text-[11px] font-medium",
        status === "complete" &&
          "border-emerald-200 bg-emerald-50 text-emerald-700",
        status === "warning" &&
          "border-amber-200 bg-amber-50 text-amber-700",
        status === "blocked" && "border-red-200 bg-red-50 text-red-700",
      )}
    >
      {label}
    </span>
  )
}

function StatusIcon({ status }: { status: TraceStatus }) {
  if (status === "complete") {
    return <CheckCircle2 className="size-4 text-emerald-600" />
  }

  if (status === "warning") {
    return <AlertTriangle className="size-4 text-amber-600" />
  }

  return <CircleStop className="size-4 text-red-600" />
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
      <CircleDashed className="size-4" />
      {label}
    </div>
  )
}
