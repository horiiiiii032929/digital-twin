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
    <aside aria-label="Review context" className="min-w-0 bg-[var(--workspace)]">
      <div className="grid content-start gap-6 p-5">
        <section aria-labelledby="release-blockers-title">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="dossier-label">Blocking record</div>
              <h2
                id="release-blockers-title"
                className="mt-1 text-[15px] font-semibold"
              >
                Release conditions
              </h2>
            </div>
            <span className="text-xs font-semibold tabular-nums text-muted-foreground">
              {readiness.blockers.length}
            </span>
          </div>

          {readiness.blockers.length === 0 ? (
            <p className="mt-3 flex gap-2 border-t pt-3 text-sm leading-5 text-[var(--success)]">
              <FileCheck2 className="mt-0.5 size-4 shrink-0" />
              No release blockers remain.
            </p>
          ) : (
            <div className="mt-3 border-t">
              <ol>
                {visibleBlockers.map((blocker, index) => (
                  <li
                    key={blocker}
                    className="grid grid-cols-[24px_1fr] gap-2 border-b py-3 text-sm leading-5"
                  >
                    <span className="dossier-label mt-0.5 text-[var(--warning)]">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="text-[var(--ink)]">
                      {formatBlocker(blocker)}
                    </span>
                  </li>
                ))}
              </ol>
              {remainingBlockers.length > 0 && (
                <details className="group border-b">
                  <summary className="min-h-10 cursor-pointer list-none py-3 text-xs font-semibold text-[var(--cobalt)] focus-visible:outline-2 focus-visible:outline-[var(--cobalt)] [&::-webkit-details-marker]:hidden">
                    Show {remainingBlockers.length} more blocker
                    {remainingBlockers.length === 1 ? "" : "s"}
                  </summary>
                  <ol start={6}>
                    {remainingBlockers.map((blocker, index) => (
                      <li
                        key={blocker}
                        className="grid grid-cols-[24px_1fr] gap-2 border-t py-3 text-sm leading-5"
                      >
                        <span className="dossier-label mt-0.5 text-[var(--warning)]">
                          {String(index + 6).padStart(2, "0")}
                        </span>
                        <span className="text-[var(--ink)]">
                          {formatBlocker(blocker)}
                        </span>
                      </li>
                    ))}
                  </ol>
                </details>
              )}
            </div>
          )}
        </section>

        <section aria-labelledby="evidence-ledger-title">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="dossier-label">Decision evidence</div>
              <h2
                id="evidence-ledger-title"
                className="mt-1 text-[15px] font-semibold"
              >
                Evidence ledger
              </h2>
            </div>
            <span className="text-xs font-semibold tabular-nums text-muted-foreground">
              {session?.evidence_snapshots.length ?? 0}
            </span>
          </div>

          {evidence.length === 0 ? (
            <p className="mt-3 flex gap-2 border-t pt-3 text-sm leading-5 text-muted-foreground">
              <BookOpenCheck className="mt-0.5 size-4 shrink-0" />
              Preview evidence snapshots will be recorded here.
            </p>
          ) : (
            <ol className="mt-3 border-t">
              {evidence.map((snapshot, index) => (
                <li key={snapshot.id} className="border-b py-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="dossier-label text-[var(--cobalt)]">
                      EV-{String(evidence.length - index).padStart(2, "0")}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      policy v{snapshot.policy_version}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm leading-5">
                    {snapshot.prompt}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatBlocker(snapshot.decision)} ·{" "}
                    {snapshot.source_labels.length} source
                    {snapshot.source_labels.length === 1 ? "" : "s"}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </section>

        {session?.trace.some((item) => item.status !== "complete") && (
          <p className="flex gap-2 border border-[var(--warning-border)] bg-[var(--warning-soft)] p-3 text-xs leading-5 text-[var(--warning)]">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
            The trace includes an event that still needs attention.
          </p>
        )}

        <WorkflowTrace trace={session?.trace ?? []} />
      </div>
    </aside>
  )
}

function formatBlocker(value: string): string {
  const formatted = value.replaceAll("_", " ")
  return formatted.charAt(0).toUpperCase() + formatted.slice(1)
}
