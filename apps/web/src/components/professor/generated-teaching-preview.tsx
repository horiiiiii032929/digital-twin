import { useEffect, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { createProfessorGeneratedPreview, listProfessorGeneratedPreviews, approveProfessorGeneratedPreview } from '@/lib/api/professor'
import type { ProfessorGeneratedPreview } from '@/lib/api/types'

import { canReviewGeneratedPreview, mergeSavedPreviews, parsePreviewCases, type Decision } from './generated-preview-review'
export function GeneratedPreviewArtifact({ artifact, busy, onReview }: { artifact: ProfessorGeneratedPreview; busy: boolean; onReview: (decisions: Array<{ case_id: string; decision: Decision }>) => void }) {
  const [decisions, setDecisions] = useState<Record<string, Decision>>({})
  return <article className="space-y-3 rounded-lg border p-4">
    <p className="text-sm font-semibold">Saved generated responses · {artifact.status} · {artifact.review_status.replaceAll('_', ' ')}</p>
    <p className="text-xs text-muted-foreground">{artifact.created_at} · {artifact.usage.actual_calls} provider calls · {artifact.usage.known_cost_usd === null ? 'Cost unknown' : `USD ${artifact.usage.known_cost_usd.toFixed(4)}`}</p>
    {artifact.error_code ? <p role="alert">Generation failed: {artifact.error_code}. This artifact cannot be approved.</p> : null}
    {artifact.cases.map(c => <section key={c.case_id} className="space-y-2 rounded border p-3"><h5 className="text-sm font-semibold">{c.case_id}</h5>
      {c.turns.map((t, i) => <div key={i} className="space-y-1 text-sm"><p className="whitespace-pre-wrap"><strong>Student:</strong> {t.student}</p><p className="whitespace-pre-wrap"><strong>Digital Twin:</strong> {t.tutor}</p><p className="text-xs text-muted-foreground">Action: {t.action}</p>{t.citations.length ? <details><summary>Source citations ({t.citations.length})</summary><pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(t.citations, null, 2)}</pre></details> : <p className="text-xs">No citations returned.</p>}</div>)}
      {c.error_code ? <p role="alert">Case failed: {c.error_code}</p> : null}
      {artifact.review_status === 'unreviewed' && artifact.status === 'complete' ? <label className="block text-sm">Decision for {c.case_id}<select className="ml-2 rounded border p-2" value={decisions[c.case_id] ?? ''} onChange={e => setDecisions(d => ({ ...d, [c.case_id]: e.target.value as Decision }))}><option value="">Review this case</option><option value="accept">Accept</option><option value="revise">Needs revision</option></select></label> : null}
    </section>)}
    <details><summary className="text-xs">Saved configuration and provenance</summary><pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(artifact.bindings, null, 2)}</pre><p className="break-all text-xs">Artifact SHA-256: {artifact.artifact_sha256}</p></details>
    <p className="text-xs text-muted-foreground">Citations identify the supplied sources; they do not prove factual correctness. Review relevance, accuracy, teaching style and answer disclosure.</p>
    {artifact.review_status === 'unreviewed' ? <Button disabled={busy || !canReviewGeneratedPreview(artifact, decisions)} onClick={() => onReview(artifact.cases.map(c => ({ case_id: c.case_id, decision: decisions[c.case_id] })))}>Save displayed case decisions</Button> : null}
  </article>
}
export function GeneratedTeachingPreview({ courseId, profileId, sessionId, ingestionJobIds, canGenerate, onApproved }: { courseId: string; profileId: string; sessionId?: string; ingestionJobIds: string[]; canGenerate: boolean; onApproved: () => void }) {
  const [artifacts, setArtifacts] = useState<ProfessorGeneratedPreview[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { let active = true; listProfessorGeneratedPreviews(courseId, profileId).then(rows => { if (active) setArtifacts(current => mergeSavedPreviews(current, rows)) }).catch(e => { if (active) setError(String(e)) }); return () => { active = false } }, [courseId, profileId])
  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!sessionId || !canGenerate) return
    const data = new FormData(event.currentTarget); setError(null); setBusy(true)
    try { const artifact = await createProfessorGeneratedPreview(courseId, profileId, { session_id: sessionId, ingestion_job_ids: ingestionJobIds, concept_label: String(data.get('concept')), concept_description: String(data.get('description')), objective: String(data.get('objective')), cases: parsePreviewCases(String(data.get('cases'))) }); setArtifacts(rows => [artifact, ...rows]) } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  async function review(artifact: ProfessorGeneratedPreview, decisions: Array<{ case_id: string; decision: Decision }>) {
    setError(null); setBusy(true)
    try { const updated = await approveProfessorGeneratedPreview(courseId, profileId, artifact.artifact_id, { artifact_sha256: artifact.artifact_sha256, decisions }); setArtifacts(rows => rows.map(row => row.artifact_id === updated.artifact_id ? updated : row)); if (updated.review_status === 'accepted') onApproved() } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  return <section className="mt-5 space-y-4 border-t pt-4"><h4 className="text-sm font-semibold">Review actual generated teaching</h4><p className="text-xs text-muted-foreground">Create fictional student questions using the completed, permitted sources in this course and the current draft profile. Responses use the configured tutoring system in an isolated preview; they are not sent to students. Generation uses external model calls (at most 60 calls / USD 9.60 per artifact). Reading or reviewing a saved artifact does not generate again.</p>
    {!sessionId || !ingestionJobIds.length ? <p className="text-sm">Select a reviewed onboarding session and complete source ingestion before generating a preview.</p> : null}
    {!canGenerate ? <p className="text-sm">This profile is approved. Create a new draft to generate further previews; saved responses remain available below.</p> : null}
    {canGenerate ? <form onSubmit={generate} className="grid gap-3"><label className="text-sm">Concept label<input required name="concept" className="mt-1 block w-full rounded border p-2" /></label><label className="text-sm">Concept description<textarea required name="description" className="mt-1 block w-full rounded border p-2" /></label><label className="text-sm">Learning objective<input required name="objective" className="mt-1 block w-full rounded border p-2" /></label><label className="text-sm">Fictional student messages<textarea required name="cases" rows={5} className="mt-1 block w-full rounded border p-2" /><span className="text-xs text-muted-foreground">One student turn per line; separate cases with a blank line. Up to four cases and three turns per case. Earlier Digital Twin responses will be generated by the system.</span></label><Button type="submit" disabled={busy || !sessionId || !ingestionJobIds.length}>{busy ? 'Working…' : 'Generate and save preview'}</Button></form> : null}
    {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
    {artifacts.map(a => <GeneratedPreviewArtifact key={a.artifact_id} artifact={a} busy={busy} onReview={decisions => void review(a, decisions)} />)}
  </section>
}
