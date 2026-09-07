import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { LearningGapReview } from './learning-gap-review'
import type { ProfessorLearningGapResult } from '@/lib/api/types'

const result: ProfessorLearningGapResult = {
  aggregation: { minimum_distinct_learners: 5, suppressed_group_count: 0,
    computed_at: '2026-09-06T00:00:00Z', reporting_window_start: '2026-08-07T00:00:00Z', active_learner_count: 6,
    visible_aggregates: [{ aggregate_id: 'a', topic_key: 'source-a', source_title: 'Approved cache notes', signal_kind: 'confusion', distinct_learners: 5, signal_count: 5, limitations: [] }] },
  proposals: [{ proposal_id: 'p', topic_key: 'source-a', signal_kind: 'confusion', observed_pattern: '5 signals', suggested_follow_up: 'Review the explanation.', distinct_learners: 5, signal_count: 5 }],
}

describe('professor gap review', () => {
  it('renders source and exact active learner definition with review choices', () => {
    const html = renderToStaticMarkup(<LearningGapReview result={result} busy={false} onReview={vi.fn()} />)
    expect(html).toContain('Source: Approved cache notes')
    expect(html).toContain('Active learners: 6')
    expect(html).toContain('not course enrollment')
    expect(html).toContain('Consider for next release')
    expect(html).toContain('Dismiss')
  })
  it('shows recorded audit outcome without claiming a course change', () => {
    const reviewed = { ...result, proposals: result.proposals.map(p => ({ ...p, review_decision: 'dismissed' })) }
    const html = renderToStaticMarkup(<LearningGapReview result={reviewed} busy={false} onReview={vi.fn()} />)
    expect(html).toContain('Recorded review: Dismissed')
    expect(html).toContain('Course material has not been changed')
    expect(html).not.toContain('<button')
  })
  it('shows no proposal controls or titles for suppressed cells', () => {
    const hidden = { ...result, aggregation: { ...result.aggregation, active_learner_count: null, visible_aggregates: [] }, proposals: [] }
    const html = renderToStaticMarkup(<LearningGapReview result={hidden} busy={false} onReview={vi.fn()} />)
    expect(html).not.toContain('Approved cache notes')
    expect(html).not.toContain('<button')
    expect(html).toContain('suppressed')
  })
})
