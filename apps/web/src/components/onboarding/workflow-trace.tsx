import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleDashed,
  CircleStop,
} from "lucide-react"

import type { TraceStatus, WorkflowTraceItem } from "@/lib/api/types"
import { cn } from "@/lib/utils"

type WorkflowTraceProps = {
  trace: WorkflowTraceItem[]
}

export function WorkflowTrace({ trace }: WorkflowTraceProps) {
  return (
    <section aria-labelledby="workflow-trace-title">
      <div className="flex items-center justify-between gap-3">
        <h3 id="workflow-trace-title" className="text-sm font-semibold">
          Setup history
        </h3>
        <span className="text-xs font-medium tabular-nums text-muted-foreground">
          {trace.length} event{trace.length === 1 ? "" : "s"}
        </span>
      </div>

      {trace.length === 0 ? (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-[var(--shell)] p-3 text-sm leading-5 text-muted-foreground">
          <CircleDashed className="mt-0.5 size-4 shrink-0" />
          Trace events appear after the session starts.
        </div>
      ) : (
        <ol className="mt-3 overflow-hidden rounded-xl border">
          {trace.map((item, index) => (
            <li key={item.id} className="border-b last:border-b-0">
              <details open={index === trace.length - 1} className="group">
                <summary className="grid min-h-12 cursor-pointer list-none grid-cols-[20px_minmax(0,1fr)_16px] items-start gap-2 px-4 py-3 text-sm outline-none hover:bg-[var(--shell)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/30 [&::-webkit-details-marker]:hidden">
                  <StatusIcon status={item.status} />
                  <span className="min-w-0">
                    <span className="block font-semibold leading-5">{item.title}</span>
                    <TraceLabel status={item.status} />
                  </span>
                  <ChevronDown className="mt-0.5 size-4 text-muted-foreground transition-transform group-open:rotate-180" />
                </summary>
                <p className="px-4 pb-3 pl-12 text-xs leading-5 text-muted-foreground">
                  {item.detail}
                </p>
              </details>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function TraceLabel({ status }: { status: TraceStatus }) {
  const label =
    status === "complete"
      ? "Complete"
      : status === "warning"
        ? "Review needed"
        : "Blocked"

  return (
    <span
      className={cn(
        "mt-1 block text-xs font-semibold",
        status === "complete" && "text-[var(--success)]",
        status === "warning" && "text-[var(--warning)]",
        status === "blocked" && "text-[var(--destructive-ink)]",
      )}
    >
      {label}
    </span>
  )
}

function StatusIcon({ status }: { status: TraceStatus }) {
  if (status === "complete") {
    return <CheckCircle2 className="mt-0.5 size-4 text-[var(--success)]" />
  }

  if (status === "warning") {
    return <AlertTriangle className="mt-0.5 size-4 text-[var(--warning)]" />
  }

  return <CircleStop className="mt-0.5 size-4 text-[var(--destructive-ink)]" />
}
