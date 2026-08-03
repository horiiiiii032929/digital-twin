# Retrieval and evaluation research synthesis

Date: 2026-08-03

Status: durable synthesis of the repository research record; not a new
evaluation result.

## Executive summary

This repository is a research-and-prototype workspace for a professor-
configurable pedagogical Digital Twin. Its primary technical contribution is
not a generic chatbot or a claim of universal state of the art. It is an
evidence-complete, course-scoped tutoring pipeline evaluated together with
professor-configured teaching behaviour and evaluation-before-publication.

The repository's research programme has three tracks:

- **R1 — cross-course evidence retrieval:** compare BM25, dense, hybrid, and
  reranked retrieval under common data, provenance, isolation, quality, and
  operational gates.
- **R2 — professor fidelity and pedagogy:** hold generator and evidence
  constant while testing whether an explicit professor policy changes tutoring
  behaviour, misconception handling, citation use, and academic-integrity
  actions.
- **R3 — end-to-end product validity:** test professor and student journeys,
  publication control, persistence, authorization, isolation, failure
  recovery, and bounded capacity.

R1 is now decision-bearing locally. The one-time 60-case held-out comparison
selected M2, BM25 plus Qwen3 dense reciprocal-rank fusion, for the experimental
profile. BM25 remains the explicit rollback. M1 dense retrieval regressed
quality and failed latency; M3 improved quality but failed the deployment
latency gate. R2 and R3 remain open, and the selected retrieval profile has
not yet been activated in the student-facing product path.

## Research boundary and claims

The authoritative project baseline is
[`2026-07-27-frontier-digital-twin-scope.md`](../00_admin/2026-07-27-frontier-digital-twin-scope.md).
It defines the project as a multi-professor, multi-course Digital Twin with
professor control over approved evidence, teaching policy, evaluation cases,
publication, withdrawal, and rollback.

The evidence can support bounded claims about:

- the tested retrieval methods on the named course corpus and revision;
- professor-policy fidelity and pedagogical behaviour under the frozen
  evaluation protocol;
- citation, permission, isolation, failure, latency, cost, and rollback
  behaviour;
- frozen simulated-student trajectories and synthetic-account workflows; and
- local deployment and reproducibility constraints.

The evidence cannot support claims about human usability, student satisfaction,
adoption, engagement, learning gains, classroom effectiveness, or universal
state-of-the-art performance. No human-participant study is required by the
current design.

## Retrieval pipeline

### Ingestion and representation

Approved local text, Markdown, and selectable-text PDF sources pass permission,
version, checksum, sensitivity, and provenance checks before processing.
PyMuPDF extracts page-numbered text blocks and preserves source locators. The
current selected chunker is the deterministic
`PageBoundedHeadingParagraphChunker` with:

- maximum chunk size: 1,200 characters;
- overlap: 160 characters; and
- zero cross-page chunks in the cross-course ingestion result.

The page-bounded design produced 1,322 chunks with preserved provenance,
whereas the document-wide comparison produced 598 chunks and 591 crossed PDF
page boundaries. The chunker was kept on the page-locality and provenance
gates.

There is no external vector database in the current research stack. Candidate
retrievers build deterministic in-memory indexes over eligible chunks. Before
ranking, the system filters out retrieval-disallowed material and inactive
source versions. Course-scoped retrieval fails closed on unauthorized course
scope or cross-course leakage.

### Candidate ladder

| Method | Description | Current interpretation |
| --- | --- | --- |
| M0 | Heading-aware BM25; `k1=1.2`, `b=0.75` | Simple control and rollback |
| M1 | Local Qwen3 dense retrieval | Quality and latency regression on held-out data |
| M2 | BM25 plus Qwen3 dense RRF; `k=60`, candidate depth 20 | Selected experimental method |
| M3 | M2 plus Qwen3 reranking | Quality reference, deployment-ineligible |

The experimental M2 binding uses local Qwen3 embedding components and a
deterministic reciprocal-rank-fusion layer. Heavy model preparation remains an
offline concern. The target deployment boundary is a two-vCPU, 4-GiB,
CPU-only serving tier, so workstation quality results cannot be presented as
concurrent capacity evidence.

## Evaluation methodology

The repository uses evaluation-first engineering. Each replaceable method has
a control, a bounded candidate set, frozen inputs, predefined quality metrics,
operational measurements, hard gates, a failure taxonomy, and a Keep / Refine /
Go Deeper / Drop decision.

The evaluation process separates development and held-out evidence. Sealed
benchmarks are hash-bound, researcher-verified, and guarded by a one-time
access ledger. Held-out thresholds are frozen from development and are not
recalibrated after inspection. Any unrecorded held-out access invalidates the
run rather than permitting a convenient rerun.

The main retrieval measures are complete-evidence success@3, evidence
recall@5, binary nDCG, MRR, no-evidence accuracy, latency, memory, provider
failures, retries, and course-isolation violations. Hard gates take priority
over average quality: a candidate that violates provenance, privacy,
authorization, isolation, provider, or deployment constraints cannot be
selected by a higher quality average.

The broader tutor protocol is defined in
[`2026-07-22-deployable-tutor-evaluation-protocol.md`](../04_experiments/2026-07-22-deployable-tutor-evaluation-protocol.md).
It freezes controlled conditions for generator, evidence, and professor policy.
The no-participant replacement is defined in
[`2026-07-23-simulated-student-llm-judge-protocol.md`](../04_experiments/2026-07-23-simulated-student-llm-judge-protocol.md):
deterministic safety and grounding checks, researcher-frozen course anchors,
calibrated LLM judging for subjective pedagogy, and frozen simulated-student
trajectories.

## Decision-bearing results

The complete chronology is maintained in
[`result-registry.md`](../05_evaluation/result-registry.md). The important
current evidence is:

| Area | Result | Decision |
| --- | --- | --- |
| Local ingestion | Page-bounded chunking preserved page locality and provenance | Keep |
| Retrieval v1 | BM25 passed the small synthetic control suite | Keep BM25 control |
| Retrieval v2 | Dense/RRF exploration did not clear the required gates | Refine; no replacement |
| Evidence sufficiency | Candidate answerability gates were not calibrated safely | Refine; no gate selected |
| Generation | Deterministic control passed structural checks; Gemma exploratory support review was 15/18 | Refine; no generator/prompt selected |
| Local deployability | M3 led development quality but failed the latency gate at depth 40 and 20 | Retain M2 operational candidate |
| Multimodal retrieval | V3 failed quality and online-vision-model gates | Drop V3; retain text rollback |
| Cross-course held-out retrieval | M2 passed global gates and led eligible methods | Keep M2; retain BM25 rollback |

### Latest held-out retrieval result

The latest result is
[`cross-course-retrieval-v1-heldout-results.md`](../05_evaluation/cross-course-retrieval-v1-heldout-results.md),
with machine-readable evidence in
[`cross-course-retrieval-v1-heldout.json`](../05_evaluation/records/cross-course-retrieval-v1-heldout.json).
The run contained 60 held-out cases: 40 answerable and 20 boundary cases.
All 240 method-case rows completed with zero course-isolation violations,
provider failures, retries, or external calls.

| Method | Complete evidence@3 | Evidence recall@5 | nDCG@10 | Warm p95 | Eligible |
| --- | ---: | ---: | ---: | ---: | --- |
| M0 BM25 | 80.0% | 87.0% | 0.795 | 75 ms | Yes |
| M1 Qwen3 dense | 72.5% | 82.6% | 0.783 | 11,959 ms | No |
| M2 hybrid RRF | 85.0% | 87.0% | 0.867 | 164 ms | Yes |
| M3 reranked hybrid | 90.0% | 93.5% | 0.864 | 106,544 ms | No |

M2 is therefore the selected experimental retriever because it improved on
BM25 across the primary quality measures while passing the frozen operational
gates. The result is a text-only retrieval decision and does not support
image-dependent coverage claims. It was run at revision `04e484d` with a dirty
working tree; that provenance is disclosed in the result summary and record.

## What remains experimentally unresolved

### R2: professor fidelity and pedagogy

This is the next decision-bearing research experiment. The planned single-turn
conditions are:

- generic assistant without course evidence or professor policy;
- oracle evidence with generic tutoring policy;
- the same oracle evidence with professor policy; and
- retrieved evidence with professor policy.

Questions and generator settings remain fixed across paired conditions. The
study should measure unconditional safe grounded task success, required-claim
support, citation validity, professor-policy pedagogical success, misconception
handling, academic-integrity action, answer-revelation control, no-evidence
behaviour, latency, tokens, cost, and provider failure behaviour.

The deterministic checks must run before subjective judging. LLM judge results
can contribute to a primary pedagogical claim only after anchor calibration,
order-swap checks, repeat checks, and false-pass checks satisfy the frozen
thresholds. Otherwise they remain diagnostic.

### R3: product validity

The current web application is still primarily a professor onboarding/review
prototype. A durable student account, course membership boundary, persistent
conversation, citation navigation, release/withdrawal path, and provider
failure recovery are not yet complete. The selected M2 profile is an
experimental configuration; it does not by itself activate a live student
retrieval path.

R3 must test synthetic professor and student journeys, including:

- evaluation-before-publication and rollback;
- authorized course access and cross-role denial;
- conversation persistence and restart survival;
- citation identity and source-locator navigation;
- timeout, malformed output, provider outage, retry, and recovery;
- redacted logs, secret isolation, retention, deletion, backup, and restore;
- bounded capacity under the declared local planning envelope.

These are product-validity and operational results, not human-usability
evidence.

## Methods that are intentionally not next

The literature notes motivate candidate families and evaluation instruments;
they do not select a method. The project should not broaden into another
retrieval sweep merely because a paper names a newer reranker or multimodal
model.

The current stop boundary excludes, unless a new failure creates a prospective
case for them:

- further tuning of the dropped multimodal V3 branch;
- new retrieval variants, chunk-size sweeps, or RRF tuning on the same sealed
  data;
- OCR, graph orchestration, proactive intervention, and full learning-gap
  analytics;
- human-participant usability or learning-outcome studies; and
- production-scale or institution-wide service claims.

Any new method would require a new prospective plan, control, dataset split,
hard gates, and registered result. It cannot be silently inserted into the
selected profile.

## Current project position

As of 2026-08-03, the project is in the transition from R1 retrieval
qualification to R2/R3. This is the middle of the overall research programme,
not an unfinished Claude workflow:

1. the Claude Code deep-read that informed this synthesis is complete;
2. the retrieval decision is complete locally but its implementation and
   result artifacts are still uncommitted in the working tree;
3. the selected profile needs product activation with BM25 fallback; and
4. professor-fidelity and end-to-end evidence are still required before the
   final research claim can be frozen.

The authoritative implementation map is
[`docs/architecture.md`](../../docs/architecture.md), while the research
definition of done is
[`docs/quality-and-learning-plan.md`](../../docs/quality-and-learning-plan.md).
Some older implementation summaries still say that the M0-M3 comparison is
pending; those should be aligned with this synthesis and the held-out result,
but they do not supersede the registered result.
