import { AlertTriangle, BookOpenCheck, FileCheck2 } from "lucide-react"

import { WorkflowTrace } from "@/components/onboarding/workflow-trace"
import type { OnboardingSession } from "@/lib/api/types"
import type { ReleaseReadiness } from "@/lib/onboarding/readiness"

export function ReviewContext({
  session,
  readiness,
}: {
  session: OnboardingSession | null
  readiness: ReleaseReadiness
}) {
  const evidence = session?.evidence_snapshots.slice(-3).reverse() ?? []
  const visibleBlockers = readiness.blockers.slice(0, 5)
  const remainingBlockers = readiness.blockers.slice(5)

  return (
    <aside aria-label="Review activity" className="min-h-full bg-white p-5 sm:p-6">
      <header className="border-b pb-5 pr-11">
        <h2 className="text-lg font-semibold tracking-[-0.02em]">Activity</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Release conditions, evidence, and setup history.
        </p>
      </header>

      <div className="flex flex-col gap-7 pt-6">
        <section aria-labelledby="release-blockers-title">
          <div className="flex items-center justify-between gap-3">
            <h3 id="release-blockers-title" className="text-sm font-semibold">
              Blockers
            </h3>
            <span className="text-xs font-medium tabular-nums text-muted-foreground">
              {readiness.blockers.length}
            </span>
          </div>

          {readiness.blockers.length === 0 ? (
            <p className="mt-3 flex gap-2 rounded-lg bg-[var(--success-soft)] p-3 text-sm leading-5 text-[var(--success)]">
              <FileCheck2 className="mt-0.5 size-4 shrink-0" />
              No release blockers remain.
            </p>
          ) : (
            <div className="mt-3 overflow-hidden rounded-xl border">
              <ul>
                {visibleBlockers.map((blocker) => (
                  <li key={blocker} className="border-b px-4 py-3 text-sm leading-5 last:border-b-0">
                    {formatBlocker(blocker)}
                  </li>
                ))}
              </ul>
              {remainingBlockers.length > 0 ? (
                <details className="border-t">
                  <summary className="min-h-10 cursor-pointer list-none px-4 py-3 text-xs font-semibold text-[var(--accent-strong)] outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/30 [&::-webkit-details-marker]:hidden">
                    Show {remainingBlockers.length} more blocker
                    {remainingBlockers.length === 1 ? "" : "s"}
                  </summary>
                  <ul className="border-t bg-[var(--shell)]">
                    {remainingBlockers.map((blocker) => (
                      <li key={blocker} className="border-b px-4 py-3 text-sm leading-5 last:border-b-0">
                        {formatBlocker(blocker)}
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </div>
          )}
        </section>

        <section aria-labelledby="evidence-title">
          <div className="flex items-center justify-between gap-3">
            <h3 id="evidence-title" className="text-sm font-semibold">Recent evidence</h3>
            <span className="text-xs font-medium tabular-nums text-muted-foreground">
              {session?.evidence_snapshots.length ?? 0}
            </span>
          </div>

          {evidence.length === 0 ? (
            <p className="mt-3 flex gap-2 rounded-lg bg-[var(--shell)] p-3 text-sm leading-5 text-muted-foreground">
              <BookOpenCheck className="mt-0.5 size-4 shrink-0" />
              Preview evidence will appear here after review.
            </p>
          ) : (
            <ol className="mt-3 overflow-hidden rounded-xl border">
              {evidence.map((snapshot) => (
                <li key={snapshot.id} className="border-b p-4 last:border-b-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-[var(--accent-strong)]">
                      {formatBlocker(snapshot.decision)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Policy v{snapshot.policy_version}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm leading-5">{snapshot.prompt}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {snapshot.source_labels.length} source
                    {snapshot.source_labels.length === 1 ? "" : "s"}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </section>

        {session?.trace.some((item) => item.status !== "complete") ? (
          <p className="flex gap-2 rounded-lg bg-[var(--warning-soft)] p-3 text-xs leading-5 text-[var(--warning)]">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
            The activity history includes an item that needs attention.
          </p>
        ) : null}

        <WorkflowTrace trace={session?.trace ?? []} />
      </div>
    </aside>
  )
}

function formatBlocker(value: string): string {
  const formatted = value.replaceAll("_", " ")
  return formatted.charAt(0).toUpperCase() + formatted.slice(1)
}
