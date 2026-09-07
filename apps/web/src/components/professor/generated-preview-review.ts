import type { ProfessorGeneratedPreview, ProfessorGeneratedPreviewRequest } from '@/lib/api/types'
export type Decision = 'accept' | 'revise'
export function mergeSavedPreviews(current: ProfessorGeneratedPreview[], fetched: ProfessorGeneratedPreview[]): ProfessorGeneratedPreview[] {
  const currentIds = new Set(current.map(artifact => artifact.artifact_id))
  return [...current, ...fetched.filter(artifact => !currentIds.has(artifact.artifact_id))]
}
export function parsePreviewCases(value: string): ProfessorGeneratedPreviewRequest['cases'] {
  const cases = value.trim().split(/\n\s*\n/).map((block, i) => ({ case_id: `case-${i + 1}`, student_messages: block.split('\n').map(s => s.trim()).filter(Boolean) }))
  if (cases.length > 4 || cases.some(c => !c.student_messages.length || c.student_messages.length > 3)) throw new Error('Enter one to four cases, with one to three student messages per case.')
  return cases
}
export function canReviewGeneratedPreview(artifact: ProfessorGeneratedPreview, decisions: Record<string, Decision>): boolean {
  return artifact.status === 'complete' && artifact.usage.unknown_cost_calls === 0 && artifact.usage.known_cost_usd !== null && artifact.cases.length > 0 && artifact.cases.every(c => !c.error_code && c.turns.length === c.student_messages.length && (decisions[c.case_id] === 'accept' || decisions[c.case_id] === 'revise'))
}
