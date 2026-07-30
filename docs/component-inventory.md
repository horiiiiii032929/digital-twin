# Component inventory

Status: active readable inventory

The machine-validated
[`student-tutor-v1`](../research/05_evaluation/profiles/student-tutor-v1.json)
is the active experimental profile. It selects the page-bounded chunker from
the cross-course ingestion result while retaining BM25 as the retrieval
rollback. The earlier
[`student-tutor-v0`](../research/05_evaluation/profiles/student-tutor-v0.json)
remains immutable historical evidence.

## Product components

| Component | Current evidence/control | State for final product | Next decision |
| --- | --- | --- | --- |
| Account/session | None; prototype is unauthenticated | Pending | Invite-only admin/professor/student session design |
| Course membership | No multi-user boundary | Pending | Role and course authorization with isolation tests |
| Source governance | Metadata workflow plus approval/version domain | Selected foundation / Refine | Persist course-scoped source lifecycle and rollback |
| Parser | PyMuPDF/TXT/Markdown local parser v1 | Selected foundation / Refine | Cross-course extraction QA; add alternatives only for observed failures |
| Chunker | Page-bounded heading/paragraph chunker v1 | Selected / Keep | Retrieval sensitivity and visual-content follow-up |
| Embedding | Local Qwen control and hosted Jina text candidate behind shared development runner; no final selection | Pending | Complete development-only provider qualification in #50 |
| Retriever | BM25 v1 rollback; prior dense/RRF studies selected no replacement | Pending final profile | M0-M3 cross-course comparison in #7 |
| Reranker | Local Qwen3 and hosted Jina adapters behind shared usage, cost, and failure contracts; no final selection | Pending | Qualify provider in #50, then include fixed M3 in #7 |
| Evidence action | Any-hit rollback is not a safe selected verifier | Pending end-to-end | Measure evidence completeness/no-evidence directly in #7, #24, and #25 |
| Generator | Deterministic control and unselected local/API adapters | Pending | Fixed provider/prompt qualification after retrieval selection |
| Professor profile/policy | Structured professor policy v1 and approved onboarding direction | Selected foundation / Refine | Multi-professor persistence and fidelity evaluation |
| Policy enforcement | Deterministic preflight only | Pending | Generic vs professor-policy comparison in #24 |
| Citation validation | Deterministic validator implemented | Pending release evidence | Adversarial and live-output qualification |
| Conversation state | No durable student implementation | Pending | Persistent course-isolated turns and recovery |
| Evaluation-before-publication | Preview/release domain foundation | Pending product integration | Immutable draft/evaluation/release/rollback lifecycle |
| Audit/operations | Test traces only | Pending | Redacted logging, health, failure, restore, and capacity evidence |
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
- Jina has no result and remains an unselected implementation spike.
- Cross-course ingestion selected page-bounded chunks: 0/1,322 crossed pages,
  compared with 591/598 for the document-wide control.

These outcomes are indexed in
[`result-registry.md`](../research/05_evaluation/result-registry.md). Unfavourable
and invalid results are part of the evidence, not cleanup candidates.

## Selection sequence

1. #49 freezes the permitted course portfolio and verified benchmark.
2. #50 qualifies one embedding/reranking provider configuration on development
   data only.
3. #7 compares M0-M3 once on the sealed cross-course set and selects a profile
   or rollback.
4. #24 qualifies professor fidelity, tutoring policy, generation, and citation
   behaviour with generator/evidence controlled.
5. #8 integrates multi-course professor/student journeys and
   evaluation-before-publication.
6. #10 and #25 run calibrated pedagogical, simulated, and end-to-end
   evaluation.
7. #9 validates isolation, failure, recovery, capacity, and packaging.
8. #12 freezes the final profile and technical evidence on 2026-08-16.

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
