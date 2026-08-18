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
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="dossier-label">System evidence</div>
          <h2 id="workflow-trace-title" className="mt-1 text-[15px] font-semibold">
            Workflow trace
          </h2>
        </div>
        <span className="text-xs font-semibold tabular-nums text-muted-foreground">
          {trace.length} events
        </span>
      </div>

      {trace.length === 0 ? (
        <div className="mt-3 flex items-start gap-2 border-t pt-3 text-sm leading-5 text-muted-foreground">
          <CircleDashed className="mt-0.5 size-4 shrink-0" />
          Trace events appear after the session starts.
        </div>
      ) : (
        <ol className="mt-3 border-t">
          {trace.map((item, index) => (
            <li key={item.id} className="border-b">
              <details open={index === trace.length - 1} className="group">
                <summary className="grid min-h-12 cursor-pointer list-none grid-cols-[24px_20px_minmax(0,1fr)_16px] items-start gap-2 py-3 text-sm focus-visible:outline-2 focus-visible:outline-[var(--cobalt)] [&::-webkit-details-marker]:hidden">
                  <span className="dossier-label mt-0.5 text-[var(--cobalt)]">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <StatusIcon status={item.status} />
                  <span className="min-w-0">
                    <span className="block font-semibold leading-5">{item.title}</span>
                    <TraceLabel status={item.status} />
                  </span>
                  <ChevronDown className="mt-0.5 size-4 text-muted-foreground transition-transform group-open:rotate-180" />
                </summary>
                <p className="pb-3 pl-[52px] text-xs leading-5 text-muted-foreground">
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
        "mt-1 block text-[11px] font-semibold",
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
