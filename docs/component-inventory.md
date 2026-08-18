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
| Parser | Selected text parser plus prospective PyMuPDF region path for columns, tables/cells, figures, diagrams, equations, OCR, and page crops | Product foundation / Refine | Qualify a production OCR/layout provider on representative PDFs; keep selected text parser as fallback |
| Chunker | Page-bounded heading/paragraph chunker v1 | Selected / Keep | Retrieval sensitivity and visual-content follow-up |
| Visual representation | Original page/region crops and non-authoritative description boundary implemented; historical 24-case held-out unopened | New public-synthetic attempt 003: 13/13 complete@3, 100% recall@5, 0.9764 nDCG, 0.9316 top-1 IoU, and 13/13 lineage; relative p95 gate failed, so no profile selected | Stop tuning the 21-case set; qualify real OCR/layout and representative end-to-end latency with text rollback |
| Embedding | Local Qwen3 binding qualified on development data; Jina retired before hosted execution | Selected for the M2 experimental profile | Runtime activation and provider-failure fallback pass the synthetic R3 slice; qualify end-to-end provider capacity |
| Retriever | M2 hybrid BM25 plus Qwen3 dense RRF selected on the 60-case held-out result; BM25 v1 retained as rollback | Selected / Keep experimentally | Synthetic product activation, citation checks, and fallback pass; retain for R2/R3 evaluation |
| Reranker | Local Qwen3 M3 leads development quality but failed the latency gate at depth 40 and 20; Jina is not required | Research candidate / deployment-ineligible | Retain M3 in the sealed comparison; carry M2 as the operational candidate |
| Evidence action | Historical C3 had 19/30 source/page evidence coverage but 0/30 exact selected-passage matches because its chunker/corpus drifted; corrected anchor C3 citation-source correctness is 4/8 applicable cases | Invalid for selection / Refine (Paused) | Preserve the failure; redesign and authorize a new prospective evaluation before any new run |
| Generator | DeepSeek V4 Flash non-thinking with strict-evidence P2; P0/P1 failed development citation correctness; P2 passed development, 36/36 stability, 104/104 one-time held-out, and 20/20 second-review sample checks; deterministic rollback retained | Selected / Keep experimentally | Retain the qualified generator binding; separately evaluate the hash-frozen professor-fidelity integration prompt on reviewed data |
| Professor profile/policy | The historical C2/C3 prompts leaked case expected actions; anchor-only V4 Pro/P3 completed 48/48, but judge repeat agreement was 33/48 labels across two cases and both sensitivity attempts stopped invalid | Requirements foundation / Refine (Paused) | Keep the deferred human packets unclaimed; resume only as a separately authorized evaluator redesign |
| Policy enforcement | Historical development action accuracy is diagnostic only; the tracked execution policy now denies development and held-out work before private split access | Refine / machine-paused | Require an explicit policy change and new run identity before prospective development; require a registered all-gates Keep result before held-out |
| Citation validation | Deterministic validation now carries source/version/checksum/page/region/bbox and access-checked original crop; historical semantic limitations remain | Implemented structural and region-lineage boundary / Refine | Validate semantic completeness on representative release evidence and production storage authorization |
| Conversation state | SQLite-backed course/release-scoped turns, idempotent request IDs, and restart reload pass synthetic acceptance | Implemented R3 foundation / Refine | Migration, backup/restore, concurrency, and capacity evidence |
| Evaluation-before-publication | Durable draft, evaluation gate, atomic publication replacement, withdrawal, rollback, and stale-conversation denial pass the 19-check synthetic v2 slice | Implemented R3 foundation / Refine | Connect frozen R2 evaluation evidence and complete migration, recovery, and concurrency qualification |
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
5. #8 now provides the bounded synthetic student journey and
   evaluation-before-publication lifecycle; credentialed identity, complete
   professor/source administration, and operational qualification remain.
6. #24 produced a reliable provider trace but no selectable professor-fidelity
   result. Its corrected anchor decision is `Refine / Paused`; development,
   held-out, and the deferred human packets require separate authorization.
7. #12 froze the supported experimental profile and technical evidence on
   2026-08-18, including explicit unsupported pedagogy, capacity, recovery, and
   deployment claims.
8. #10 and #25 remain future work for calibrated pedagogical, simulated, and
   end-to-end evaluation; they are not implied by the freeze.
9. #9 remains future operational qualification for backup/restore,
   concurrency, bounded capacity, and deployment packaging.

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
