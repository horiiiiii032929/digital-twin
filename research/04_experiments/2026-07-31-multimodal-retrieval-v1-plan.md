# Multimodal study-material retrieval v1 plan

Date: 2026-07-31

Status: prospective groundwork complete; public synthetic instrument validated;
no private benchmark authored, no model run, and no candidate selected

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

PDF pages, slide renders, and standalone images may be source containers.
Audio and video require temporal segmentation, transcript alignment, and
different latency measures, so they remain a separate future decision rather
than being silently mixed into this benchmark.

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
specific observed modality. No hosted model or external course-content transfer
is permitted in this experiment.

## Data and split discipline

The committed
[`multimodal_retrieval_v1_synthetic.json`](../05_evaluation/multimodal_retrieval_v1_synthetic.json)
contains nine public structural cases and six hash-bound SVG assets. It covers
six core modalities plus text-control, no-evidence, and adversarial-integrity
slices. SVG assets must be rasterized before candidate execution so embedded
markup cannot leak answers. This set tests contracts and runners only; it cannot
support a quality claim.

The private course benchmark will be created separately under ignored storage.
Before any candidate run, the researcher will:

1. sample rendered pages by course and observed modality, not by image-object
   count;
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
pixels, OCR text, descriptions, and per-case outputs remain ignored and local.

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
- peak resident memory, model-cache size, derived storage per page, failures,
  retries, token use, external calls, and cost.

## Hard gates

A candidate is deployment-eligible on the declared reference hardware only if:

- course-isolation, permission, and source-version violations are all zero;
- external provider calls and API cost are zero;
- every returned region has page-local, hash-bound derivation provenance;
- every frozen case produces a complete result or an explicitly classified
  failure;
- complete-evidence success@3 on visual-answerable cases is at least 80% and at
  least 15 percentage points above V0;
- no included modality with at least four cases falls below 60% complete-
  evidence success@3;
- text-control complete-evidence success does not regress from V0;
- no-evidence and adversarial-integrity action accuracy are both 100%;
- warm p95 retrieval latency is at most 2 seconds;
- offline preprocessing p95 is at most 30 seconds per page;
- peak process memory is at most 4 GiB; and
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

The command verifies the JSON Schema, fixture hashes, rasterization contract,
region bounds and ownership, modality/slice coverage, positive and boundary
semantics, permissions, and review-state rules. No candidate evaluation has run,
so there is no result-registry entry or Keep / Refine / Go Deeper / Drop
decision yet.

## Stop rules

- Do not modify or reopen the sealed text benchmark for this work.
- Do not interpret raw PDF image-object counts as figures or denominator size.
- Do not run private pages through a hosted OCR, caption, or embedding service.
- Do not use OCR confidence as evidence completeness.
- Do not add V3 merely because it is nominally multimodal.
- Stop and record the run if the held-out ledger, permission boundary, or source
  hash is violated.
