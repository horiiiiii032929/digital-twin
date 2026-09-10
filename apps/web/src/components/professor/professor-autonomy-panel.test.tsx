import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ActivitySection, PolicySection } from './professor-autonomy-panel'
import type { AutonomousActionV1, AutonomousGoalV1, AutonomousOutcomeV1 } from '@/lib/api/types'

const scope = { student_id: 'student-a', course_id: 'course-a', release_id: 'release-a' }
const action: AutonomousActionV1 = { schema_version: '1.0.0', plan_id: 'plan-a', opportunity_id: 'opportunity-a', profile_sha256: 'a'.repeat(64), graph_version: 'v2.1', updated_at: '2026-09-08T00:00:00Z', ...scope, action_id: 'action-a', goal_id: 'goal-a', kind: 'issue-retrieval-practice', status: 'delivered', structured_reason: 'due-review', validation_results: { consent: true, source: true }, created_at: '2026-09-08T00:00:00Z', policy_version: 1, generator_model: 'deterministic' }
const goal = { ...scope, goal_id: 'goal-a', learner_subgoal: 'Explain the retry boundary', success_condition: 'Distinguish accounts' } as AutonomousGoalV1
const outcome = { ...scope, action_id: 'action-a', outcome_id: 'answered-a', recorded_at: '2026-09-08T01:00:00Z', kind: 'answered' } as AutonomousOutcomeV1

describe('support decision provenance', () => {
  it('connects matching goal, recorded decision and observed outcome without equating reply with learning', () => {
    const html = renderToStaticMarkup(<ActivitySection actions={[action]} goals={[goal]} outcomes={[outcome]} traces={[]} />)
    expect(html).toContain('Explain the retry boundary')
    expect(html).toContain('Distinguish accounts')
    expect(html).toContain('Recorded decision')
    expect(html).toContain('does not establish understanding')
    expect(html).toContain('View release and delivery checks')
  })
  it('does not attach foreign learner, course or release evidence even when IDs collide', () => {
    for (const field of ['student_id', 'course_id', 'release_id'] as const) {
      const html = renderToStaticMarkup(<ActivitySection actions={[action]} goals={[{...goal, [field]: 'foreign'}]} outcomes={[{...outcome, [field]: 'foreign'}]} traces={[]} />)
      expect(html).not.toContain('Explain the retry boundary')
      expect(html).not.toContain('Outcome: Answered')
      expect(html).toContain('No outcome has been recorded yet')
      expect(html).toContain('linked goal is not available')
    }
  })
  it('keeps the latest scoped outcome when the API lists newest records first', () => {
    const earlier = {...outcome, outcome_id: 'delivered-a', recorded_at: '2026-09-08T00:00:00Z', kind: 'delivered' as const}
    const foreign = {...outcome, outcome_id: 'foreign-a', recorded_at: '2026-09-08T02:00:00Z', student_id: 'foreign', kind: 'failed' as const}
    for (const values of [[outcome, earlier, foreign], [foreign, earlier, outcome]]) {
      const html = renderToStaticMarkup(<ActivitySection actions={[action]} outcomes={values} traces={[]} />)
      expect(html).toContain('Outcome: Answered')
      expect(html).not.toContain('Outcome: Delivered')
      expect(html).not.toContain('Outcome: Failed')
    }
  })

})


describe('autonomy boundary prerequisites', () => {
  it('blocks saving with an approved profile but no published release', () => {
    const callbacks = { onCancelAction: () => {}, onConfirmAction: () => {}, onEdit: () => {},
      onRequestAction: () => {}, onSave: async () => {} }
    for (const publishedRelease of [false, true]) {
      const html = renderToStaticMarkup(<PolicySection {...callbacks} publishedRelease={publishedRelease}
        approvedProfile={true} busy={null} editing={false} pendingAction={null} policy={null} />)
      expect(html.includes('Publish a release with an approved teaching profile before saving')).toBe(!publishedRelease)
      const submit = html.match(/<button[^>]*type="submit"[^>]*>/)?.[0] ?? ''
      expect(submit).not.toBe('')
      expect(/\sdisabled(?:=|\s|>)/.test(submit)).toBe(!publishedRelease)
    }
  })
})
