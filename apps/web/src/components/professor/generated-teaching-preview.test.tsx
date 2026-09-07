import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { GeneratedPreviewArtifact, GeneratedTeachingPreview } from './generated-teaching-preview'
import { canReviewGeneratedPreview, mergeSavedPreviews, parsePreviewCases } from './generated-preview-review'
import type { ProfessorGeneratedPreview } from '@/lib/api/types'
const artifact: ProfessorGeneratedPreview = {
  artifact_id: 'saved-a', profile_id: 'profile-a', status: 'complete', artifact_sha256: 'immutable-hash', created_at: '2026-09-06', review_status: 'unreviewed',
  bindings: { profile_sha256: 'profile-hash', source_sha256: 'source-hash', configuration_sha256: 'config-hash', composition: { candidate: 'v13-luna-sol' }, scope: 'isolated-single-concept-preview' },
  cases: [{ case_id: 'case-1', student_messages: ['Why?', 'Explain my mistake.'], turns: [{ student: 'Why?', tutor: 'What condition matters?', action: 'ask', citations: [] }, { student: 'Explain my mistake.', tutor: 'The source requires both signatures.', action: 'answer', citations: [{ title: 'Approved notes', source_checksum: 'abc' }] }], error_code: null }],
  usage: { max_calls: 60, max_cost_usd: 9.6, actual_calls: 4, known_cost_usd: 0.02, unknown_cost_calls: 0 }, error_code: null,
}
describe('generated teaching approval', () => {
  it('retains newly created evidence and completed reviews when an older list arrives', () => {
    const created = { ...artifact, artifact_id: 'newly-created' }
    const accepted: ProfessorGeneratedPreview = { ...artifact, review_status: 'accepted' }
    const historical = { ...artifact, artifact_id: 'older-saved' }
    expect(mergeSavedPreviews([created, accepted], [artifact, historical])).toEqual([created, accepted, historical])
    expect(mergeSavedPreviews([], [artifact])).toEqual([artifact])
  })
  it('retains explicit histories without invented tutor turns and bounds case input', () => {
    expect(parsePreviewCases('First question\nFollow-up\n\nOther case')).toEqual([{ case_id: 'case-1', student_messages: ['First question', 'Follow-up'] }, { case_id: 'case-2', student_messages: ['Other case'] }])
    expect(() => parsePreviewCases('')).toThrow()
    expect(() => parsePreviewCases('a\nb\nc\nd')).toThrow()
    expect(() => parsePreviewCases('a\n\nb\n\nc\n\nd\n\ne')).toThrow()
  })
  it('requires explicit decisions, complete turns and known usage before review', () => {
    expect(canReviewGeneratedPreview(artifact, {})).toBe(false)
    expect(canReviewGeneratedPreview(artifact, { 'case-1': 'accept' })).toBe(true)
    expect(canReviewGeneratedPreview({ ...artifact, status: 'failed' }, { 'case-1': 'accept' })).toBe(false)
    expect(canReviewGeneratedPreview({ ...artifact, usage: { ...artifact.usage, unknown_cost_calls: 1 } }, { 'case-1': 'accept' })).toBe(false)
    expect(canReviewGeneratedPreview({ ...artifact, cases: [{ ...artifact.cases[0], turns: [] }] }, { 'case-1': 'accept' })).toBe(false)
  })
  it('displays actual dialogue, evidence, model configuration and immutable hash', () => {
    const html = renderToStaticMarkup(<GeneratedPreviewArtifact artifact={artifact} busy={false} onReview={vi.fn()} />)
    for (const text of ['What condition matters?', 'Explain my mistake.', 'both signatures', 'Approved notes', 'v13-luna-sol', 'immutable-hash', 'do not prove factual correctness']) expect(html).toContain(text)
    expect(html).toContain('disabled')
  })
  it('keeps approved profiles read-only while a new draft is required for generation', () => {
    const html = renderToStaticMarkup(<GeneratedTeachingPreview courseId="course-a" profileId="approved-a" sessionId="session-a" ingestionJobIds={["job-a"]} canGenerate={false} onApproved={vi.fn()} />)
    expect(html).toContain('Create a new draft')
    expect(html).not.toContain('<form')
    expect(html).not.toContain('Generate and save preview')
  })
  it('retains failed artifact and saved review outcome without new approval controls', () => {
    const html = renderToStaticMarkup(<GeneratedPreviewArtifact artifact={{ ...artifact, review_status: 'needs_revision', status: 'failed', error_code: 'provider_unavailable' }} busy={false} onReview={vi.fn()} />)
    expect(html).toContain('needs revision')
    expect(html).toContain('provider_unavailable')
    expect(html).not.toContain('<button')
  })
})
