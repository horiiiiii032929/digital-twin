# Multimodal study-material retrieval v1 plan

Date: 2026-07-31

Status: private draft and governed Claude second review complete; draft requires
researcher adjudication and correction before sealing; no retrieval candidate
has run or been selected

GitHub issue: [#60](https://github.com/horiiiiii032929/digital-twin/issues/60)

## Decision question

What is the simplest locally deployable representation that retrieves important
study evidence from diagrams, charts, tables, equations, screenshots, scanned
pages, annotations, and photos without regressing the selected text workflow or
crossing course and provider privacy boundaries?

This is a separate decision from the sealed text-only M0-M3 comparison in #7.
The existing 40/60 text benchmark remains unchanged and must never be rewritten
to include visual-dependent claims after sealing.

## Observed need

The approved cross-course portfolio contains 32 PDFs and 1,318 pages. The
ingestion audit counted 1,623 raw embedded-image objects, but that number is not
a semantic figure count: one slide can contain many fragments. More importantly,
five of eight rendered pages inspected across the four courses contained
diagram, handwriting, or spatial meaning not fully represented by selectable
text. The current parser therefore proves text coverage only.

The full authorized source universe is the canonical academic vault rather
than only the four-course PDF subset. A visible-file census found 673 files;
the subsequent hash-bound traversal found 2,636 entries and 336,913,605 logical
bytes because it also counted hidden and ignored tool state. Of the full set,
1,906 are generated/tool-state exclusions, three are secret-indicated
exclusions, 435 require review, and 292 are clear course-scoped candidates.
The vault includes 123 PDFs, 27 Draw.io diagrams, 22 notebooks, 22 CSV files,
17 PNG/JPEG images, 10 TeX sources, and seven DOCX/Pages/EPS artifacts. These
counts establish format diversity; they are not quality denominators.

## Prediction

A locally processed OCR and region-aware representation should recover most
missing evidence because the observed failures are primarily text-in-image,
table binding, arrow direction, and spatial grouping. A visual-embedding model
may improve image-semantic retrieval, but it should be added only if the simpler
candidate fails a predeclared modality slice.

## Scope

Included in v1:

- diagrams and flow relationships;
- quantitative charts;
- tables and row/column bindings;
- mathematical notation;
- application screenshots;
- scanned or rasterized text;
- handwritten annotations when legible; and
- instructional photos with an evidence-bearing region.

PDF pages, Draw.io renders, notebook outputs, tables, equations, DOCX/Pages
renders, and standalone images may be source containers when they are
evidence-bearing study material. Code, Markdown, and other textual sources stay
available to the text path and controls; they are not converted to images just
to inflate multimodal coverage.
Audio and video require temporal segmentation, transcript alignment, and
different latency measures, so they remain a separate future decision rather
than being silently mixed into this benchmark.

Permission covers eligible study materials across the canonical vault. It does
not override exclusions for solutions, graded answers, student or participant
data, credentials, secrets, generated caches, duplicates, or unrelated files.
Every sampled source receives an explicit eligibility decision before case
authoring.

## Fixed candidates

All candidates implement the same course-scoped retrieval interface and return
source, version, page, region, permission, content hash, score, and derivation
provenance.

| ID | Representation | Role |
| --- | --- | --- |
| V0 | Current selectable text, captions, and page-bounded chunks | Control and rollback |
| V1 | Locally rasterized pages plus local OCR and existing captions | Simplest visual-text candidate |
| V2 | V1 plus local region typing, reading order, table structure, and reviewed descriptions | Primary candidate |
| V3 | V2 plus precomputed local visual embeddings and text/visual rank fusion | Conditional candidate only |

V3 may run only if V2 misses the complete-evidence gate overall or fails a
specific observed modality. A hosted model or external course-content transfer
is eligible only under a prospective provider record for approved sources, with
mandatory exclusions, minimization, retention/training state, call count, cost,
and deletion or expiry recorded.

## Low-cost deployment boundary

The student-facing target is a commodity CPU-only service with approximately
two vCPUs, 4 GiB RAM, and no GPU. Visual rendering, OCR, layout analysis,
description generation, and visual embedding construction are offline ingestion
jobs on the local research workstation. The deployed request path receives only
approved, revocable derived text, region metadata, and precomputed indexes; it
does not keep an OCR, caption, layout, or vision model resident.

This separates ingestion compute from serving cost. A provider or method that
requires an always-on accelerator or server-side page processing is not
deployment-eligible for v1, even if its offline quality is higher.

## Data and split discipline

The committed
[`multimodal_retrieval_v1_synthetic.json`](../05_evaluation/multimodal_retrieval_v1_synthetic.json)
contains nine public structural cases and six hash-bound SVG assets. It covers
six core modalities plus text-control, no-evidence, and adversarial-integrity
slices. SVG assets must be rasterized before candidate execution so embedded
markup cannot leak answers. This set tests contracts and runners only; it cannot
support a quality claim.

The private course benchmark will be created separately under ignored storage
from eligible materials across the canonical vault, not only the active
four-course text corpus.
Before any candidate run, the researcher will:

1. classify candidate files by course, format, eligibility, and observed
   modality, then sample artifacts rather than raw image objects;
2. author at least 24 visual-answerable cases spanning at least four observed
   modalities, with at least four cases per included modality;
3. add at least eight text-sufficient controls, four no-evidence cases, and four
   permission or prompt-integrity cases;
4. bind every positive claim to a document hash, page, normalized region, and
   source permission;
5. personally verify every case and record absent modalities rather than
   fabricating coverage; and
6. freeze a development/held-out split and unopened access ledger before
   measuring V1-V3.

Synthetic assets never enter the private performance denominator. Private page
pixels, OCR text, descriptions, and per-case outputs remain ignored. They stay
local except for the minimized inputs of an explicitly approved, recorded
external review.

## Cross-model QA protocol

Run ID: `multimodal-benchmark-claude-second-review-v1`

Decision question: does a separate vision-language model identify claim,
region, modality, visual-dependency, no-evidence, or integrity defects that the
assistant visual QA missed before researcher verification, and is its provider
boundary acceptable for this research use?

The baseline is the corrected assistant review v2, which accepted all 40 draft
cases. Eligible independent reviewers are the locally installed `gemma3:4b`
Ollama model at digest `a2af6cc3eb7f` and an explicitly approved Claude model.
Each asset batch uses a fresh, non-resumed review with deterministic settings
where the provider supports them. Every reviewer receives the rendered page plus the
query, expected action, required claims, modality, visual-dependency label, and
selectable surrounding text, but not the assistant decision or notes.

The run covers all 40 private cases rather than a sample. Report response and
schema success, Accept / Revise / Reject counts, agreement with assistant QA,
claim-support, region-adequacy, modality, visual-dependency, action, privacy,
per-slice latency, token counts, and every disagreement. The prediction is that
at least 36 cases will be accepted, no case will be rejected for unsupported
claims or privacy, and any remaining revisions will expose useful ambiguity for
researcher review.

Hard gates are an allowlisted provider/model and source set, zero mandatory-
exclusion transfers, a complete call/cost log, 40 schema-valid decisions, and
no automatic benchmark mutation or sealing. Any Revise, Reject, privacy
concern, source-eligibility concern, or provider-boundary failure becomes an
explicit researcher-review item. Passing this run is advisory and never changes
`researcher_verified`; a model is not an independent human reviewer.

The currently authenticated Claude Code account is a consumer Max account, not
an API, Team, or Enterprise workspace. Before private pages are transferred,
the run record must capture the consumer model-improvement setting and accept
the applicable consumer retention/deletion terms. If that boundary is not
accepted, use the local reviewer or a separately approved commercial API or
enterprise workspace instead.

## Metrics

Primary quality metrics, reported overall and by modality:

- complete-evidence success@3;
- atomic evidence Recall@5;
- region nDCG@10; and
- no-evidence and integrity action accuracy.

Supporting measures:

- OCR exactness for evidence-bearing spans;
- table cell and row/column binding accuracy;
- chart label/value and diagram-edge claim fidelity;
- text-control regression versus V0;
- failed-case category: data, rendering, OCR, layout, region, query, ranking,
  model, policy, integration, or operations;
- offline render/extraction/index p50 and p95 per page;
- warm retrieval p50 and p95 per query;
- offline and deployed peak resident memory, model-cache size, derived storage
  per page, failures, retries, token use, external calls, and cost;
- a reproducible monthly quote for the declared commodity server, reported as
  operational evidence rather than a timeless price claim.

## Hard gates

A candidate is deployment-eligible on the declared reference hardware only if:

- course-isolation, permission, and source-version violations are all zero;
- every external provider call is prospectively approved, minimized, logged,
  and within its recorded cost and data boundary;
- every returned region has page-local, hash-bound derivation provenance;
- every frozen case produces a complete result or an explicitly classified
  failure;
- complete-evidence success@3 on visual-answerable cases is at least 80% and at
  least 15 percentage points above V0;
- no included modality with at least four cases falls below 60% complete-
  evidence success@3;
- text-control complete-evidence success does not regress from V0;
- no-evidence and adversarial-integrity action accuracy are both 100%;
- warm p95 retrieval latency is at most 2 seconds on the declared two-vCPU,
  4-GiB, no-GPU target;
- offline preprocessing p95 is at most 30 seconds per page;
- deployed service peak resident memory is at most 2.5 GiB, leaving capacity
  for the operating system and storage process;
- no OCR, layout, caption, or vision model is resident in the deployed service;
- the current-vault derived retrieval package is at most 2 GiB; and
- derived artifacts can be revoked by course, source, and version.

The small private benchmark will also report paired bootstrap intervals. Hard
counts and failed cases remain primary; uncertainty does not erase a failed
safety or privacy gate.

## Decision rule

Keep the highest-quality candidate that clears every hard gate. Prefer V1 over
V2, and V2 over V3, when their complete-evidence results are tied within the
paired interval and no modality shows a material loss. If V1 and V2 fail
quality, run V3 only against the failed slices plus the fixed controls. If all
candidates fail deployment gates, retain V0 for text and mark visual claims
unsupported rather than silently answering from incomplete evidence.

An accepted candidate updates a new versioned component profile only after the
one-time held-out run and end-to-end regression checks. V0 remains the rollback.

## Reproduction and current checkpoint

Validate the public contract without a model or private source access:

```bash
npm run verify:multimodal-retrieval-instruments
```

Create the private inventory, PDF review sample, and unverified draft locally:

```bash
npm run inventory:multimodal-sources
npm run sample:multimodal-pdf-pages
npm run draft:multimodal-private-benchmark
```

The commands verify the JSON Schema, fixture hashes, rasterization contract,
region bounds and ownership, modality/slice coverage, positive and boundary
semantics, permissions, and review-state rules. The retrieval candidates have
not run.

The current private checkpoint has 26 page assets and 40 cases: 24 visual-
answerable, eight text controls, four no-evidence, and four integrity cases.
An assistant visual QA round found and corrected seven cases and replaced one
ambiguous case; a second assistant pass accepted the corrected draft. All 40
remain researcher-unverified and ignored, so they cannot be sealed or run until
the researcher completes the generated visual-review checklist.

The governed Claude second review completed all 40 cases on 2026-08-01. It
accepted 22, requested revision on 17, and rejected one. Direct visual
adjudication confirmed three clipped evidence regions and one incorrect claim.
Codex then supplied a deterministic taxonomy adjudication for the remaining 14
flags: six controls are text-sufficient, seven visual candidates are held out
of the visual denominator pending replacement cases, and the integrity refusal
uses `not_applicable`. The draft still requires researcher source-content
verification and remains unsealed. See
[`multimodal-benchmark-claude-second-review-v1-results.md`](../05_evaluation/multimodal-benchmark-claude-second-review-v1-results.md).

## Stop rules

- Do not modify or reopen the sealed text benchmark for this work.
- Do not interpret raw PDF image-object counts as figures or denominator size.
- Do not send excluded, unapproved, or unlogged material to an external
  provider; approved hosted processing must follow its prospective run record.
- Do not use OCR confidence as evidence completeness.
- Do not add V3 merely because it is nominally multimodal.
- Do not move offline visual preprocessing onto the student request path.
- Do not force code or textual files through image processing merely because
  the full vault is authorized.
- Stop and record the run if the held-out ledger, permission boundary, or source
  hash is violated.
