import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { OnboardingSession } from "@/lib/api/types"

function formatRevisionValue(value: string | string[] | Record<string, unknown>) {
  if (typeof value === "string") return value
  if (Array.isArray(value)) return value.join(", ")
  return Object.entries(value)
    .map(([key, entry]) => `${key.replaceAll("_", " ")}: ${String(entry)}`)
    .join(" · ")
}

export function RevisionProposalPanel({
  session,
  isResolvingRevision,
  onConfirm,
  onDiscard,
  onSelect,
}: {
  session: OnboardingSession
  isResolvingRevision: boolean
  onConfirm: () => Promise<void>
  onDiscard: () => Promise<void>
  onSelect: (alternativeId: string) => Promise<void>
}) {
  const proposal = session.revision_proposal
  const history = session.revision_history ?? []
  if (!proposal && history.length === 0) {
    return null
  }

  return (
    <section className="space-y-4" aria-labelledby="revision-review-heading">
      {proposal ? (
        <div className="rounded-xl border border-[var(--warning-border)] bg-[var(--warning-soft)] p-4 text-[var(--warning)]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 id="revision-review-heading" className="text-sm font-semibold text-[var(--ink)]">
                Pending policy revision
              </h3>
              <p className="mt-1 text-xs leading-5 text-[var(--warning)]">
                {proposal.alternatives.length > 1 && !proposal.selected_alternative_id
                  ? "This feedback matches multiple policy areas. Choose one before confirming."
                  : "Confirm to update the policy, or discard to keep the current draft."}
              </p>
            </div>
            <Badge variant="outline" className="status-badge status-badge-warning">
              review needed
            </Badge>
          </div>
          {proposal.alternatives.length > 1 ? (
            <div className="mt-4 grid gap-2" role="group" aria-label="Policy revision options">
              {proposal.alternatives.map((alternative) => {
                const selected = proposal.selected_alternative_id === alternative.id
                return (
                  <Button
                    key={alternative.id}
                    type="button"
                    variant={selected ? "default" : "outline"}
                    className="h-auto justify-start whitespace-normal px-3 py-2 text-left"
                    onClick={() => void onSelect(alternative.id)}
                    disabled={isResolvingRevision}
                    aria-pressed={selected}
                  >
                    <span className="min-w-0 [overflow-wrap:anywhere]">
                      <strong>{alternative.category.replaceAll("_", " ")}</strong>
                      <br />
                      <span className="font-normal">
                        {formatRevisionValue(alternative.proposed_value)}
                      </span>
                    </span>
                  </Button>
                )
              })}
            </div>
          ) : (
            <p className="mt-4 rounded-lg bg-white p-3 text-sm leading-6 text-[var(--ink)]">
              {formatRevisionValue(proposal.proposed_value)}
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            {proposal.affected_policy_fields.map((field) => (
              <Badge key={field} variant="outline">
                {field.replaceAll("_", " ")}
              </Badge>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => void onConfirm()}
              disabled={isResolvingRevision || (proposal.alternatives.length > 1 && !proposal.selected_alternative_id)}
            >
              Confirm
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void onDiscard()}
              disabled={isResolvingRevision}
            >
              Discard
            </Button>
          </div>
        </div>
      ) : null}
      {history.length > 0 ? (
        <div className="rounded-xl border bg-card p-4">
          <h3 className="text-sm font-semibold">Revision history</h3>
          <ol className="mt-3 space-y-2">
            {[...history].reverse().map((record) => (
              <li key={`${record.proposal_id}-${record.resolved_at}`} className="rounded-lg bg-muted/50 px-3 py-2 text-xs leading-5">
                <div className="flex items-center justify-between gap-3"><span className="font-medium">Policy v{record.base_policy_version} → v{record.target_policy_version}</span><Badge variant="outline">{record.status}</Badge></div>
                <p className="mt-1 [overflow-wrap:anywhere] text-muted-foreground">
                  {record.proposed_value
                    ? formatRevisionValue(record.proposed_value)
                    : record.feedback}
                </p>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  )
}
