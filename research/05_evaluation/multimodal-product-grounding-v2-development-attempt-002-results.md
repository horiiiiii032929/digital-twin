# Evaluation result: multimodal-product-grounding-v2-development-attempt-002

## Run identity

- Component: corrected OCR adapter, source-derived table context, and
  modality-routed region retrieval
- Status: completed development result; one frozen operational gate failed
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Code revision: `707c08edd794656b6605212f3a21de993e44a81d`
- Working tree: dirty with the prospective issue #86 implementation
- Reproduction command: `npm run benchmark:multimodal-product-grounding-development`
- Runtime: Python 3.12, PyMuPDF 1.28.2, deterministic BM25, authored synthetic OCR
- Generated artifact: `reports/generated/multimodal-product-grounding-v2-development-attempt-002/result.json`
- Generated artifact SHA-256: `beb3a70481e916490bcb417ee89b47b2a4ea778851a471f82b6085d9fdc78d59`
- Predecessor: `multimodal-product-grounding-v2-development-001`

## Decision context

Attempt 002 prospectively repaired the attempt-001 OCR field mapping, added
row/column context to table cells, introduced deterministic modality routing,
and used the versioned `1.0.1` correction overlay for four synthetic geometry
labels. Questions, facts, assets, other labels, and the historical held-out
boundary were unchanged.

No external or paid provider was called. No description model or online vision
model was used. The historical 24-case multimodal held-out split remained
closed.

## Aggregate results

| Candidate | Complete visual evidence@3 | Atomic recall@5 | Region nDCG@10 | Top-1 localization IoU | Citation lineage | Retrieval p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R0 text page | 0/13 | 0.0% | 0.0190 | 0.0194 | 0/13 | 0.058 ms |
| R2 region routed | 13/13 (100%) | 100% | 0.9764 | 0.9316 | 13/13 (100%) | 0.079 ms |

R2 passed complete@3, recall@5, region nDCG improvement, localization, table
relationship, unsupported-description, no-evidence, isolation, text-control,
citation-lineage, and zero-online-vision gates. Its complete@3 95% Wilson
interval is 77.2% to 100%, which is wide because this is a 13-case visual
pilot.

Both candidates passed 2/2 no-evidence, 2/2 integrity, 2/2 isolation, and 2/2
selectable-text control cases. R2 passed 3/3 table fact-support checks.

## Operational results

| Candidate | Chunks | Offline mean / p95 per asset | OCR calls | Stored crop bytes | Query p50 / p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| R0 text page | 7 | 36.2 / 65.2 ms | 0 | 0 | 0.024 / 0.058 ms |
| R2 region routed | 44 | 75.9 / 161.2 ms | 3 | 594,905 | 0.030 / 0.079 ms |

R2's absolute p95 remained below 0.08 ms, but it was 35.2% slower than the
small page control. The frozen gate allowed only 20% overhead, so it failed.
The ratio is sensitive to sub-millisecond timer noise, but the gate is retained
as failed rather than relaxed after seeing the result.

## Failures and validity review

- The only frozen gate failure was query p95 latency.
- Retrieval evidence was complete for both equation cases, but the conservative
  lexical sufficiency action abstained on 2/13 answerable cases because the
  formula chunks lacked searchable type context such as "equation" or
  "defined". Answerable action accuracy was not a frozen attempt-002 hard gate;
  this is therefore recorded as a new integration weakness, not silently folded
  into the retrieval metric.
- The multi-cell table comparison localized the broad table first, giving
  top-1 IoU 0.111 for that case, while both required cells were still found.
- The correction overlay is development-only and bound to the exact base
  instrument SHA-256. It does not provide independent real-PDF validation.

The metric implementation completed and the run is valid for the frozen
retrieval question. It is not eligible for profile selection because latency
failed and the newly observed answerable-action weakness requires a prospective
integration gate.

## Decision

- Outcome: **Refine**
- Selected implementation: none
- Profile change: none
- Retained fallback: selected text profile with BM25 rollback
- Historical held-out: closed

Attempt 003 may keep the exact dataset and evidence labels, add deterministic
region-kind search labels, remove duplicate/non-answer-bearing records from
routed indexes, and add a 100% answerable-action gate. No quality labels or
questions may change.

## Limitations

The perfect 13-case retrieval score is evidence only for this small authored
synthetic set. It does not qualify a production OCR engine, layout model,
description model, private course corpus, deployment capacity, or real user
workflow.

## Learning notes

Source-derived table context and modality routing corrected the ranking problem
without a vision model. However, retrieval completeness and the decision to use
that evidence are separate system properties; both need explicit gates.
