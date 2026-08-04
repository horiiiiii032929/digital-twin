# Component inventory

Status: active readable inventory

The machine-validated
[`student-tutor-v1`](../research/05_evaluation/profiles/student-tutor-v1.json)
is the active experimental profile. It selects the page-bounded chunker and
M2 hybrid retrieval from the cross-course held-out result while retaining BM25
as the explicit rollback. The earlier
[`student-tutor-v0`](../research/05_evaluation/profiles/student-tutor-v0.json)
remains immutable historical evidence.

## Product components

| Component | Current evidence/control | State for final product | Next decision |
| --- | --- | --- | --- |
| Account/session | Synthetic `X-Account-ID` session plus active/revoked account checks | Implemented R3 test boundary / Refine | Replace with invite-only credential/session design before release candidate |
| Course membership | Durable course membership with fail-closed student authorization | Implemented R3 foundation / Refine | Add professor/admin lifecycle and migration evidence |
| Source governance | Metadata workflow plus approval/version domain | Selected foundation / Refine | Persist course-scoped source lifecycle and rollback |
| Parser | PyMuPDF/TXT/Markdown local parser v1 | Selected foundation / Refine | Evaluate local OCR and layout-aware visual regions in #60 without changing the sealed text corpus |
| Chunker | Page-bounded heading/paragraph chunker v1 | Selected / Keep | Retrieval sensitivity and visual-content follow-up |
| Visual representation | Full vault inventoried; seven text-recoverable cases have accepted visual replacements; the 40-case benchmark is researcher-verified and sealed into a 16-case development split plus an unopened 24-case held-out split | V0-V2 and conditional V3 development runs completed; V2 improved region nDCG but failed the relative gate, while V3 regressed failed-slice quality and kept a vision tower online; no profile selected | Apply the stop rule: retain V0 text rollback, keep unsupported visual claims abstaining, and define a new prospective method only with new evidence rather than tuning these development cases |
| Embedding | Local Qwen3 binding qualified on development data; Jina retired before hosted execution | Selected for the M2 experimental profile | Runtime activation and provider-failure fallback pass the synthetic R3 slice; qualify end-to-end provider capacity |
| Retriever | M2 hybrid BM25 plus Qwen3 dense RRF selected on the 60-case held-out result; BM25 v1 retained as rollback | Selected / Keep experimentally | Synthetic product activation, citation checks, and fallback pass; retain for R2/R3 evaluation |
| Reranker | Local Qwen3 M3 leads development quality but failed the latency gate at depth 40 and 20; Jina is not required | Research candidate / deployment-ineligible | Retain M3 in the sealed comparison; carry M2 as the operational candidate |
| Evidence action | Any-hit rollback is not a safe selected verifier | Pending end-to-end | Measure evidence completeness/no-evidence directly in #24 and #25 |
| Generator | Deterministic control and unselected local/API adapters | Pending | Fixed provider/prompt qualification after retrieval selection |
| Professor profile/policy | Structured professor policy v1 and approved onboarding direction | Selected foundation / Refine | Multi-professor persistence and fidelity evaluation |
| Policy enforcement | Deterministic preflight only | Pending | Generic vs professor-policy comparison in #24 |
| Citation validation | Deterministic validator plus persisted release/source/version/locator checks pass the synthetic student slice | Implemented foundation / Refine | Adversarial live-output qualification in #24 |
| Conversation state | SQLite-backed course/release-scoped turns, idempotent request IDs, and restart reload pass synthetic acceptance | Implemented R3 foundation / Refine | Migration, backup/restore, concurrency, and capacity evidence |
| Evaluation-before-publication | Preview/release domain foundation | Pending product integration | Immutable draft/evaluation/release/rollback lifecycle |
| Audit/operations | Durable redacted lifecycle, denial, fallback, and recovery events pass content-exclusion checks | Implemented foundation / Refine | Health, backup/restore, bounded capacity, and operator visibility |
| Learning-gap analytics | Design scaffold only | Deferred | Reconsider after core Digital Twin evidence freeze |
| Proactive intervention | Design scaffold only | Deferred | Reconsider after core Digital Twin evidence freeze |

## Evidence already retained

- Local ingestion and provenance passed its recorded synthetic evaluation.
- BM25 v1 is the inspectable retrieval rollback.
- Retrieval v2 selected no replacement.
- Evidence-sufficiency v1 selected no safe gate.
- Local Gemma generation was exploratory and selected no generator/prompt.
- The IT5002 development pilot showed a large descriptive reranking advantage,
  but its negatives were calibration cases.
- The separate one-time rapid run is invalid, retired, and never rerun.
- Jina has no result and was retired before hosted execution; its adapters remain
  historical, unselected implementation evidence.
- Cross-course ingestion selected page-bounded chunks: 0/1,322 crossed pages,
  compared with 591/598 for the document-wide control.

These outcomes are indexed in
[`result-registry.md`](../research/05_evaluation/result-registry.md). Unfavourable
and invalid results are part of the evidence, not cleanup candidates.

## Selection sequence

1. #49 froze the permitted course portfolio and verified benchmark.
2. The local deployability study froze one quality-preserving Qwen3
   embedding/reranking configuration on development data only.
3. #60 completed separately with no selected multimodal profile; the text-only
   rollback remains authoritative.
4. #7 compared M0-M3 once on the sealed cross-course set and selected M2 with
   BM25 rollback.
5. #24 qualifies professor fidelity, tutoring policy, generation, and citation
   behaviour with generator/evidence controlled.
6. #8 integrates multi-course professor/student journeys and
   evaluation-before-publication.
7. #10 and #25 run calibrated pedagogical, simulated, and end-to-end
   evaluation.
8. #9 validates isolation, failure, recovery, capacity, and packaging.
9. #12 freezes the final profile and technical evidence on 2026-08-16.

## Profile rule

A profile may change only when:

- the decision question, control, candidates, data, metrics, and hard gates were
  prospective;
- the run and all failures are registered;
- privacy, permission, integrity, isolation, and sealed-data gates pass;
- a Keep / Refine / Go Deeper / Drop decision names the rollback; and
- component plus end-to-end regression checks pass.

Provider reputation, a paper result, a leaderboard, or faster hardware does not
select a component.
