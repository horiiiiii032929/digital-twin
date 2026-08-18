import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { OnboardingSession } from "@/lib/api/types"

export function RevisionProposalPanel({
  session,
  isResolvingRevision,
  onConfirm,
  onDiscard,
}: {
  session: OnboardingSession
  isResolvingRevision: boolean
  onConfirm: () => Promise<void>
  onDiscard: () => Promise<void>
}) {
  if (!session.revision_proposal) {
    return null
  }

  return (
    <section className="rounded-xl border border-[var(--warning-border)] bg-[var(--warning-soft)] p-4 text-[var(--warning)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--ink)]">
            Pending policy revision
          </h3>
          <p className="mt-1 text-xs leading-5 text-[var(--warning)]">
            Confirm to update the policy, or discard to keep the current draft.
          </p>
        </div>
        <Badge variant="outline" className="status-badge status-badge-warning">
          review needed
        </Badge>
      </div>
      <p className="mt-4 rounded-lg bg-white p-3 text-sm leading-6 text-[var(--ink)]">
        {session.revision_proposal.proposed_value}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {session.revision_proposal.affected_policy_fields.map((field) => (
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
          disabled={isResolvingRevision}
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
    </section>
  )
}
