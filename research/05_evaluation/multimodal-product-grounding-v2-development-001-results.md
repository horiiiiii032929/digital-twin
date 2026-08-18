# Evaluation result: multimodal-product-grounding-v2-development-001

## Run identity

- Component: region-aware multimodal ingestion, retrieval, and citation lineage
- Status: completed development diagnostic; not eligible for selection
- Date and owner: 2026-08-18, researcher with Codex implementation support
- Code revision: `707c08edd794656b6605212f3a21de993e44a81d`
- Working tree: dirty with the prospective issue #86 implementation
- Reproduction command: `npm run benchmark:multimodal-product-grounding-development`
- Runtime: Python 3.12, PyMuPDF 1.28.2, deterministic BM25, authored synthetic OCR
- Generated artifact: `reports/generated/multimodal-product-grounding-v2-development-001/result.json`
- Generated artifact SHA-256: `506c2ec4dc3b4bc85d9559e60ddceda518456cc502a09cf30dc4ae74d4dd5e70`
- Predecessor: corrected historical V2 baseline in
  `multimodal-retrieval-v1-v3-development-attempt-002-analysis-correction-001`

## Decision context

The run asked whether deterministic region-aware offline ingestion and BM25
could improve visual evidence retrieval while preserving source lineage, text
controls, isolation, and a zero-vision-call online path. `R0-text-page` was the
page-bounded text control. `R1-region-local` added first-class page regions,
tables/rows/cells, diagrams, equations, OCR boundaries, crops, and lineage.

The 21-case, nine-asset public-synthetic development instrument was frozen
before execution. The historical 24-case multimodal held-out split was not
read. No external or paid provider was called, and Gemma was not used.

## Aggregate results

| Candidate | Complete visual evidence@3 | Atomic recall@5 | Region nDCG@10 | Top-1 localization IoU | Citation lineage | Retrieval p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R0 text page | 2/13 (15.4%) | 15.4% | 0.0447 | 0.0451 | 0/13 | 0.044 ms |
| R1 region local | 3/13 (23.1%) | 42.3% | 0.0826 | 0.0431 | 7/13 (53.8%) | 0.107 ms |

R1 improved atomic recall by 26.9 percentage points and region nDCG by 0.0379,
but it remained far below the frozen 80% complete@3 and 90% recall@5 gates.
The 95% Wilson interval for R1 complete@3 was 8.2% to 50.3%, reflecting the
small pilot.

Both candidates passed 2/2 no-evidence cases, 2/2 integrity cases, 2/2
cross-course isolation cases, and 2/2 selectable-text controls. R1 passed all
three table fact-support checks, exposed no generated descriptions, and made
zero online vision calls.

## Operational results

| Candidate | Chunks | Offline mean / p95 per asset | OCR calls | Stored crop bytes | Shared peak memory |
| --- | ---: | ---: | ---: | ---: | ---: |
| R0 text page | 7 | 46.1 / 86.4 ms | 0 | 0 | 2,054,015 B |
| R1 region local | 37 | 59.8 / 107.7 ms | 3 | 357,194 | 2,054,015 B |

The query latency ratio gate failed, although both absolute p95 measurements
were below 0.11 ms and therefore dominated by small-sample timer noise. The
frozen gate remains recorded as failed.

## Failures and validity review

- **OCR adapter / integration:** the instrument used `bbox`, while the provider
  adapter passed records directly to a model requiring `bounding_box`. OCR was
  invoked three times but produced no accepted regions. The scanned and
  screenshot assets therefore failed ingestion, and the mixed asset retained
  only its selectable text. This is an implementation defect, not evidence
  against OCR itself.
- **Table representation / ranking:** value-only cell chunks lacked their row
  and column labels. Header and row-label cells occupied the first ranks, so
  exact value cells did not reliably enter the top three.
- **Duplicate representations / ranking:** broad page, table, and selectable
  text records competed with localized evidence. No modality-aware routing was
  active in R1.
- **Synthetic localization labels / data:** the authored diagram and equation
  boxes were broader than the deterministic rendered regions. Their localization
  values are not suitable for a selection decision and must be corrected in a
  prospectively versioned instrument.
- **Citation lineage:** lineage was structurally present whenever R1 retrieved
  the expected asset. Its 7/13 aggregate primarily reflects missing OCR assets,
  not missing fields on successful region hits.

The evaluator completed and the run is retained as a valid diagnostic. It is
not valid for selecting R1 because the OCR adapter and localization labels need
prospective repair. No unfavorable metric is removed or reinterpreted as a
pass.

## Hard gates

Passed: region nDCG improvement, table fact support, unsupported-description
rate, no-evidence behavior, isolation, text controls, and zero online vision
calls.

Failed: complete@3, atomic recall@5, top-1 localization, citation lineage, and
relative p95 latency.

## Decision

- Outcome: **Refine**
- Selected implementation: none
- Profile change: none
- Retained fallback: selected text profile with BM25 rollback
- Historical held-out: closed

Attempt 002 may repair only the diagnosed interfaces and representations: map
the authored OCR field explicitly, add source-derived row/column context to
table cells, add deterministic modality routing, deduplicate competing layout
records, and issue a corrected `1.0.1` synthetic development instrument. It
must receive a new run ID and preserve this result.

## Limitations

This small synthetic diagnostic does not establish real-PDF OCR quality,
vision-description quality, private-course performance, production capacity,
or professor/student usability. The OCR engine and any replacement vision
description model remain unqualified.

## Learning notes

Region extraction alone is insufficient. Retrieval needs source-derived
structural context and modality routing; otherwise exact regions lose to broad
duplicate records. Lineage must be measured jointly with retrieval success,
because perfectly modeled but unretrieved regions cannot support a student
citation.
