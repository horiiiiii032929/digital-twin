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
    <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Pending policy revision</div>
          <p className="mt-1 text-xs leading-5">
            Confirm to update the policy, or discard to keep the current draft.
          </p>
        </div>
        <Badge variant="outline" className="border-amber-300 text-amber-900">
          review needed
        </Badge>
      </div>
      <p className="mt-3 text-sm leading-6">
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
