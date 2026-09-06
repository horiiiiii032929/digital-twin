import { Button } from '@/components/ui/button'
import type { ProfessorLearningGapResult } from '@/lib/api/types'

export type GapReviewDecision = 'consider-for-next-release' | 'dismissed'

export function LearningGapReview({ result, busy, onReview }: {
  result: ProfessorLearningGapResult | null
  busy: boolean
  onReview: (proposalId: string, decision: GapReviewDecision) => void
}) {
  if (!result) return null
  const { aggregation, proposals } = result
  return <div className="mt-4 space-y-3">
    <p className="text-xs text-muted-foreground">
      Reporting window: {aggregation.reporting_window_start ? new Date(aggregation.reporting_window_start).toLocaleDateString() : 'Not available'}–{new Date(aggregation.computed_at).toLocaleDateString()}.
      {' '}Active learners: {aggregation.active_learner_count ?? 'suppressed (fewer than 5)'}. Counts distinct learners with a saved student message in this release and window; not course enrollment.
    </p>
    {proposals.map(proposal => <div key={proposal.proposal_id} className="rounded-lg border p-3">
      <p className="text-sm">{proposal.suggested_follow_up}</p>
      <p className="mt-1 text-xs text-muted-foreground">Source: {aggregation.visible_aggregates.find(gap => gap.topic_key === proposal.topic_key)?.source_title ?? 'No uniquely identified source'}</p>
      {proposal.review_decision ? <p className="mt-2 text-xs" role="status">Recorded review: {proposal.review_decision === 'dismissed' ? 'Dismissed' : 'Consider for next release'}. Course material has not been changed.</p> : <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" disabled={busy} onClick={() => onReview(proposal.proposal_id, 'consider-for-next-release')}>Consider for next release</Button>
        <Button size="sm" variant="outline" disabled={busy} onClick={() => onReview(proposal.proposal_id, 'dismissed')}>Dismiss</Button>
      </div>}
    </div>)}
  </div>
}
