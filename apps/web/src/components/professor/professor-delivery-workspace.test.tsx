import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import { EvidenceCard, ReleaseCard } from './professor-delivery-workspace'
import type { ProfessorReleaseSummary } from '@/lib/api/types'

const callbacks = { onCreateDraft: vi.fn(), onPreflight: vi.fn(), onPublish: vi.fn(), onOpenSetup: vi.fn() }
const published = { id: 'published', course_id: 'course-a', status: 'published', evaluation_status: 'passed', policy_version: 1, chunk_count: 3 } as ProfessorReleaseSummary

describe('delivery readiness and recovery', () => {
  it('does not claim an empty history when the request is loading or failed and offers recovery', () => {
    const base = { busy: null, jobs: [], onRefresh: vi.fn(), onSubmit: vi.fn(), onRetry: vi.fn(), onCancel: vi.fn() }
    const loading = renderToStaticMarkup(<EvidenceCard {...base} loading={true} loadError={null} />)
    expect(loading).toContain('Loading upload history')
    expect(loading).not.toContain('No background upload jobs')
    const failed = renderToStaticMarkup(<EvidenceCard {...base} loading={false} loadError="Synthetic timeout" />)
    expect(failed).toContain('Synthetic timeout')
    expect(failed).toContain('Retry upload history')
    expect(failed).not.toContain('No background upload jobs')
    const empty = renderToStaticMarkup(<EvidenceCard {...base} loading={false} loadError={null} />)
    expect(empty).toContain('No background upload jobs')
  })
  it('explains the live version separately from an unpublished successor', () => {
    const html = renderToStaticMarkup(<ReleaseCard {...callbacks} busy={null} onboardingReady={false} setupContext="The open tutor setup belongs to another course." publishedRelease={published} profileReady={false} preflight={null} sourceCount={0} release={{ ...published, id: 'next', status: 'draft', evaluation_status: 'pending', policy_version: 2 } as ProfessorReleaseSummary} />)
    expect(html).toContain('Students still use published policy v1')
    expect(html).toContain('belongs to another course')
    expect(html).not.toContain('Publish to students')
    expect(html).toContain('Review Digital Twin setup')
  })
  it('does not label withdrawn releases as drafts or offer publication without checks', () => {
    const html = renderToStaticMarkup(<ReleaseCard {...callbacks} busy={null} onboardingReady={false} setupContext={null} publishedRelease={null} profileReady={false} preflight={null} sourceCount={0} release={{ ...published, status: 'withdrawn' }} />)
    expect(html).toContain('Withdrawn release')
    expect(html).not.toContain('Draft release')
    expect(html).not.toContain('Publish to students')
  })
})
