# Final report evidence map

Status: evidence-gathering checkpoint 0.1  
Inventory revision: `9474e64adbf2895329e807b9a787a1013ddc03a4`
Purpose: understand the complete evidence archive before drafting the report

## What this map does

This document is the human-readable entrance to the report evidence. It does
not replace the evaluation registry or individual records. It explains how the
evidence fits together, which artifacts are authoritative, why apparently
conflicting outcomes coexist, and what the final report can and cannot claim.

The exhaustive inventories are:

- [All report-relevant repository files](evidence-inventory/evidence-file-inventory.csv)
- [All 315 registered evaluation results](evidence-inventory/evaluation-result-inventory.csv)
- [Aggregate inventory of ignored local evidence](evidence-inventory/local-evidence-aggregates.csv)
- [Inventory validation summary](evidence-inventory/evidence-inventory-summary.json)

Ignored raw data and generated outputs are counted but not listed by filename
or copied into this directory. This preserves the repository's privacy and
artifact-boundary rules while still recording the scale and location of the
local evidence.

## How to decide which source wins

When two artifacts appear to disagree, use this order:

1. Immutable machine-readable run records and registered corrections for what
   happened in a particular evaluation.
2. The newest versioned component or release profile for what is currently
   selected.
3. The authoritative product scope and release plan for what the project is
   trying to deliver.
4. The evaluation result registry for the complete decision chronology.
5. The dated current-status document for navigation and operational context.
6. Experiment plans, design notes, reports, and issue summaries.
7. Implementation and tests for what the code does, without treating code
   existence as evaluation evidence.

This order follows the repository's own
[source-of-truth rule](../../../docs/current-status.md#source-of-truth-order).
Plans establish intent; records establish observations; profiles establish
selection. A successful test or build does not replace a failed quality result.

## Evidence inventory snapshot

### Individually inventoried repository artifacts

The generated manifest contains 2,041 report-relevant files. After this result
is committed, all 2,041 are tracked. Important evidence families
include:

| Evidence family | Files | Role in the report |
| --- | ---: | --- |
| Evaluation summaries, corrections, and rubrics | 398 | Human-readable interpretation of individual runs |
| Evaluation instruments | 258 | Frozen questions, gates, models, budgets, and execution rules |
| Machine-readable result records | 242 | Primary source for metrics, configurations, decisions, and limitations |
| Committed evaluation-dataset artifacts | 65 | Public or sanitized cases, schemas, and manifests |
| Experiment plans and learning logs | 79 | Predictions, alternatives, and prospective methods |
| Component and release profiles | 20 | Current and historical implementation selections |
| Literature notes | 9 | Starting point for academic related work; primary papers must still be cited |
| Architecture and operations documentation | 43 | System boundaries, deployment, security, and recovery design |
| Automated and manual verification files | 272 | Regression and acceptance evidence; not automatically research results |
| Reproduction and analysis tools | 295 | Commands and code used to construct or evaluate evidence |
| Backend and frontend implementation | 245 | Inspectable implementation of the claimed system boundaries |

The complete file-level path, category, size, Git state, and SHA-256 hash are in
the file inventory rather than repeated here.

### Ignored local evidence

There are 12,776 ignored local files occupying approximately 12.81 GiB across
the approved data and generated-output boundaries:

| Directory | Files | Approx. size | Handling rule |
| --- | ---: | ---: | --- |
| `data/raw/` | 24 | 23.47 MiB | Local only; do not copy raw contents into the report |
| `data/interim/` | 266 | 23.27 MiB | Local transformations; cite durable sanitized summaries |
| `data/processed/` | 794 | 13.14 MiB | Local evaluation products; use registered records for claims |
| `data/external/` | 2,829 | 4.79 GiB | External/public or approved local source copies; permissions still govern use |
| `experiments/runs/` | 34 | 4.49 MiB | Local run outputs; durable decisions belong in the registry |
| `reports/generated/` | 8,829 | 7.96 GiB | Bulky generated evidence; cite recorded hashes and durable summaries |

These directories cannot be treated as one dataset. They contain overlapping
source copies, intermediate transformations, databases, indexes, checkpoints,
and rendered artifacts. Their file count and total size describe storage, not
an evaluation sample.

## The project in one evidence-backed picture

The current project outcome is mixed but coherent.

1. Early work established permission-aware parsing, page-bounded chunking,
   text retrieval, professor-controlled publication, student isolation,
   persistence, citation lineage, and deterministic fallback.
2. Larger factual and whole-product evaluations repeatedly showed that good
   retrieval coverage or safe orchestration did not guarantee a fully grounded
   answer with correct academic-integrity action and exact claim-to-citation
   lineage. These runs produced valid `Refine` and `No Release` decisions.
3. The failures motivated fresh, source-disjoint successors rather than reruns
   on opened data. The latest grounding successor replaced free factual wording
   with an ambiguity-safe evidence method and deterministic evidence-set
   compiler.
4. The exact successor then passed an 820-case actual-product confirmation
   after a disclosed correction to 30 contradictory expected fallback actions.
   The original `Refine` result remains preserved.
5. Local qualification 006 then re-established HTTPS, restart, clean-restore,
   rollback, governed restoration, and responsive-browser operation for the
   exact post-correction V2.1 profile.
6. The selection remains experimental and local. It does not establish durable
   hosted production, real-professor fidelity, real-student usability, or
   improved learning outcomes.

The newest profile is therefore not evidence that the earlier no-release
results were wrong. It is evidence that a narrower architecture, new data, and
a different authority boundary passed later gates. This progression should be
the backbone of the academic report.

## Current decision chain

| Evidence line | Strongest decision-bearing result | Outcome | What it establishes | What it does not establish |
| --- | --- | --- | --- | --- |
| Local source ingestion and chunking | [`cross-course-ingestion-v1`](../../05_evaluation/cross-course-ingestion-v1-results.md) | Keep | Permission-aware TXT, Markdown, and selectable-text PDF ingestion with deterministic, page-bounded provenance on the audited corpus | OCR, complete visual understanding, or arbitrary private-course coverage |
| Historical text retrieval comparison | [`cross-course-retrieval-v1-heldout-001`](../../05_evaluation/cross-course-retrieval-v1-heldout-results.md) | Keep M2; retain BM25 rollback | On the one-time 60-case text-only comparison, hybrid M2 reached 85.0% complete evidence at three versus 80.0% for BM25 while passing its operational gates | End-to-end answer quality, multimodal grounding, or universal superiority |
| Large integrated factual evaluation | [`course-digital-twin-evaluation-program-011`](../../05_evaluation/course-digital-twin-evaluation-program-011-results.md) | Refine / no factual release | On 10,000 candidate and 1,000 control cases, the candidate reached 44.16% fully grounded success, 72.9% boundary action accuracy, and 478 severe unsupported releases; both conditions failed absolute gates | That every component or model was intrinsically poor; this was a system-level result |
| Cross-engine whole-product comparison | [`governed-full-autonomy-v2-1-cross-engine-evaluation-010`](../../05_evaluation/governed-full-autonomy-v2-1-cross-engine-evaluation-010-results.md) | Refine / No Release | No engine passed combined factual and autonomy eligibility; GPT-5.4 mini passed all autonomy gates, but every factual condition failed and a shared retrieval binding caused 100/500 failures per engine | A model-only ranking independent of the shared system defect |
| Fresh grounding successor | [`governed-full-autonomy-v2-1-grounding-successor-011`](../../05_evaluation/governed-full-autonomy-v2-1-grounding-successor-011-results.md) | Keep method | On 500 candidate plus 100 control cases, the successor reached 99.25% fully grounded success, a 98.0% source-family lower bound, 100% boundary safety, 99.25% claim/citation precision and recall, and zero severe releases | A hosted or human-validated product release |
| Actual-product confirmation | [`confirmation-013` correction](../../05_evaluation/governed-full-autonomy-v2-1-actual-product-confirmation-013-reference-validity-correction-001-results.md) | Keep exact governed V2.1 profile | All 820 immutable responses passed action, citation, fallback, restart, transition, termination, scope, and authority gates after correcting 30 expected provider-failure actions without another model call | That the correction can be hidden, or that real-user outcomes were measured |
| Local operational qualification | [`local-r1-governed-v2-1-release-qualification-006`](../../05_evaluation/local-r1-governed-v2-1-release-qualification-006-results.md) | Keep local release | After the multi-concept correction, the exact candidate-v3, dominance-gate, Luna H+E1 composition passed 25/25 live HTTPS, 6/6 restart, 6/6 clean restore, 3/3 T0 rollback, 3/3 governed restoration, and browser-critical checks | Durable public hosting, institutional production readiness, broad accessibility certification, or an absolute factual-quality pass |
| Multi-concept learner-state correction | [`governed-full-autonomy-v2-1-multi-concept-confirmation-025`](../../05_evaluation/governed-full-autonomy-v2-1-multi-concept-confirmation-025-results.md) | Keep correction | 72 fresh 30-day histories passed concept attribution, assessment scope, and attempt recognition at 100%, with zero policy violations or provider use | Real learning improvement; the simulated next-outcome AUROC remained weak and 32.9% of autonomous interventions were classified as wasted |
| Multimodal grounding | [`true-visual-supplement-003`](../../05_evaluation/true-visual-supplement-003-results.md) | Refine; no profile selected | On 30 public/synthetic visual assets, 27/30 answerable assets were retrieved at three, boundary safety and original-region lineage were 30/30, and all 30 provider calls completed | Representative multimodal quality; only 19/30 cases met visual-fact completeness, diagram recall was weak, and the lexical unsupported-segment proxy is not an independently verified hallucination count |
| Professor fidelity | [`professor-fidelity` corrected closeout](../../05_evaluation/professor-fidelity-v2-anchor-002-machine-review-summary-001-analysis-correction-001-results.md) | Refine / Paused | The automated evaluator and anchor work are ineligible for condition selection; negative and invalid evidence is preserved | Measurable professor fidelity, a calibrated human-equivalent judge, or professor approval |
| Human outcomes | [Claim boundary](../../../reports/claim-to-evidence-matrix.md) | Not established | The repository explicitly distinguishes technical and synthetic evidence from human claims | Usability, satisfaction, adoption, trust, engagement, or learning improvement |

## What the current selected profile actually contains

The newest profile is
[`student-tutor-r1-local-candidate-v3.json`](../../05_evaluation/profiles/student-tutor-r1-local-candidate-v3.json),
version `v2.1-floor-004-h-e1`, and is explicitly marked `experimental`.

It contains 15 component boundaries:

- 11 are selected;
- nine of the selected components have a `Keep` decision;
- two selected components, proactive triggers and learning-gap analytics, remain
  `Go Deeper`; and
- four components remain pending: reranking, figure description, policy
  enforcement, and citation validation.

The current factual generator is a deterministic evidence-set compiler. GPT-5.6
Luna under the selected H+E1 policy-value allocation is bounded to complex pedagogical planning and cannot own factual source
truth, identity, policy, state commit, publication, delivery, or rollback. T0,
the grounded deterministic assistant, remains the immediate rollback. The
phrasing “LLM-backed release” must therefore be qualified: the selected local
profile uses a constrained model planner, not unrestricted model-generated
factual answers.

## Why `Keep`, `Refine`, `Invalid`, and `No Release` all appear

The registry contains 315 named results:

| Report-oriented classification | Results | Interpretation |
| --- | ---: | --- |
| Keep | 94 | A method, control, dataset step, infrastructure boundary, or exact profile passed its own decision gate |
| Refine | 45 | A valid run produced usable evidence but did not justify selection |
| No Release | 27 | The evaluated integrated candidate did not meet release eligibility at that checkpoint |
| Invalid | 91 | The execution or instrument could not support its planned quality conclusion; the failure remains part of the audit trail |
| Go Deeper | 43 | The build, instrument, or development result justified a bounded next evaluation, not selection |
| Drop | 7 | The candidate or approach was rejected |
| Other | 8 | Results whose wording does not map cleanly to those report-level classes |

These counts must not be interpreted as a success rate. The rows have different
grains: a build check, dataset audit, provider canary, component comparison,
and release selection are all one registry row. The report should use them as a
decision chronology, not average them.

## Evidence chronology for understanding the project

### Phase 1: inspectable baselines, 14 July--7 August

The project first built and measured local ingestion, deterministic chunking,
BM25 retrieval, dense/hybrid alternatives, evidence sufficiency, grounded
generation, and synthetic publication/student workflows. The important lesson
was to keep simple controls and explicit rollback paths. M2 hybrid retrieval was
selected on a small, frozen text-only comparison, while multimodal and some
generation candidates remained unselected.

### Phase 2: professor fidelity and evaluator reliability, 10--18 August

Attempts to compare C0--C3 professor-policy conditions exposed invalid bindings,
unreliable judges, incomplete human packets, provider drift, and sensitivity
failures. The corrected closeout paused professor-fidelity selection rather than
turning diagnostic model labels into a claim. This phase is important negative
methodology evidence.

### Phase 3: deployable foundations and dataset scale, 19--29 August

The repository expanded identity, persistence, source storage, ingestion jobs,
publication, security, backup/restore, and local deployment controls. In
parallel, the factual-QA pipeline scaled to 10,000 synthetic rows through
successive pilots and corrections. The scale completion proves an engineering
pipeline, not 10,000 independent facts: the later correction records correlated
templates and shared claim grammars.

### Phase 4: integrated factual and whole-system evaluation, 30 August--2 September

Actual-product evaluations showed the central gap between retrieval and answer
validity. Some runs obtained high evidence recall while fully grounded success,
boundary decisions, or exact claim/citation binding remained poor. Program 011
and cross-engine evaluation 010 therefore issued valid no-release decisions.
Fresh architecture successors moved from question-level matching toward atomic,
source-side, ambiguity-safe evidence and deterministic claim compilation.

### Phase 5: narrow local selection, 2 September

Grounding successor 011 passed on fresh evidence. Confirmation 013 then tested
the exact governed product across reactive and autonomous conditions. Its
original output was `Refine` because 30 provider-failure expectations conflicted
with the approved fallback architecture; a disclosed zero-call reference
correction changed the expectations and preserved every response. The corrected
result and subsequent local operational qualification selected the exact V2.1
local profile with T0 rollback.

## Data and evidence quality assessment

| Finding | Evidence | Risk to the report | Severity |
| --- | --- | --- | --- |
| The registry is link-complete and its machine artifacts parse successfully | 315 unique result IDs, zero broken local links; 242/242 result records, 58/58 dataset JSON files, 253/253 instrument JSON files, and 20/20 profile JSON files are valid JSON | Low structural risk when paths are followed explicitly | Pass |
| The current claim matrix is stale by design | `reports/claim-to-evidence-matrix.md` is frozen to the 18 August `student-tutor-v1` baseline, before the 2 September grounding, autonomy, and local-release selections | It can incorrectly label newer supported claims as unsupported or preserve superseded model selections | High |
| `docs/current-status.md` contains older snapshots below newer opening sections | Its older “Evidence state” table says autonomous LLM-backed R1 is No Release, while the newest 2 September records select a narrower V2.1 local profile | Quoting the middle of the status document without following newer records can reverse the current interpretation | High |
| Not every registry row has a machine-readable record | 241 of 315 rows have linked JSON records; 74 rely on summaries or other artifacts | Numeric comparisons should prefer rows with records, or explicitly disclose summary-only provenance | Medium |
| Record filenames cannot always be treated as result IDs | Eleven legacy record filenames differ from their internal `run_id` | Automated joins by filename can attach the wrong label; use the registry link and internal `run_id` | Low |
| Committed dataset case counts overlap | The 58 JSON datasets contain reused controls, corrections, transforms, and nested packages | Summing their `case_count` values would overstate the number of independent evaluation cases | High if summed; otherwise low |
| Most detailed run data is intentionally ignored | 12.81 GiB of local data and generated outputs is represented by durable summaries, selected hashes, and aggregate inventory only | Claims remain reproducible only where the result record preserves exact revisions, hashes, configurations, and output locations | Medium |

The next claims artifact should be a new final-report claim matrix rather than an
edit to the frozen August 18 matrix. Historical evidence must remain unchanged.

## What is safe to claim now

- An exact experimental local V2.1 profile passed its named synthetic/public
  grounding, governed-autonomy, persistence, restart, rollback, and local HTTPS
  qualification gates.
- Deterministic application code retains authority over identity, scope,
  evidence, factual claims, publication, state commit, delivery, and rollback;
  the selected model planner is bounded.
- Earlier integrated factual and cross-engine evaluations produced valid
  unfavorable results that motivated architecture successors.
- The final selected profile has an explicit T0 rollback and important pending
  components and human-evidence gaps.

## What is not safe to claim

- The system is generally production-ready, durably hosted, institution-scale,
  or proven secure under all threats.
- The system is faithful to a real professor or approved by one.
- Students find it usable, trustworthy, or satisfying.
- It improves learning, engagement, retention, or academic outcomes.
- It provides a selected, representative multimodal tutoring capability.
- An LLM independently produces release-quality factual answers; the selected
  local factual compiler is deterministic.
- The 10,000-row synthetic pipeline represents 10,000 independent facts or
  real-student questions.

## Recommended reading order for the next discussion

1. Read this map and agree on the five-phase interpretation.
2. Review the [current local profile](../../05_evaluation/profiles/student-tutor-r1-local-candidate-v3.json).
3. Compare the negative [Program 011 result](../../05_evaluation/course-digital-twin-evaluation-program-011-results.md)
   with the later [grounding successor 011](../../05_evaluation/governed-full-autonomy-v2-1-grounding-successor-011-results.md).
4. Review the original [confirmation 013](../../05_evaluation/governed-full-autonomy-v2-1-actual-product-confirmation-013-results.md)
   beside its [reference-validity correction](../../05_evaluation/governed-full-autonomy-v2-1-actual-product-confirmation-013-reference-validity-correction-001-results.md).
5. Finish with the [local release qualification](../../05_evaluation/local-r1-governed-v2-1-release-qualification-006-results.md)
   and its limitations.

Only after this interpretation is accepted should the report introduction or
results section be expanded.
