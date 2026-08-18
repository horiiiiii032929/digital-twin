# Evaluation result: multimodal-product-grounding-v2-development-attempt-003

## Run identity

- Component: compact modality routing and answerable-action integration
- Status: completed development result; one frozen operational gate failed
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Code revision: `707c08edd794656b6605212f3a21de993e44a81d`
- Working tree: dirty with the prospective issue #86 implementation
- Reproduction command: `npm run benchmark:multimodal-product-grounding-development`
- Runtime: Python 3.12, PyMuPDF 1.28.2, deterministic BM25, authored synthetic OCR
- Timing: one warm-up plus 100 timed repeats per case and candidate
- Generated artifact: `reports/generated/multimodal-product-grounding-v2-development-attempt-003/result.json`
- Generated artifact SHA-256: `537ff64bc891539fc8f8c2ecbcba854e65f95cb3d25206b0a71b1cb4ede45edb`
- Predecessor: `multimodal-product-grounding-v2-development-attempt-002`

## Decision context

Attempt 003 kept the exact `1.0.1` questions, evidence, assets, and thresholds.
It added deterministic equation-type search labels, compact routed indexes,
direct diagram routing, and a prospective 100% answerable-action gate. No
external provider, paid provider, Gemma model, generated visual description, or
online vision inference was used. The historical 24-case held-out split
remained closed.

## Aggregate results

| Candidate | Complete visual evidence@3 | Atomic recall@5 | Region nDCG@10 | Top-1 localization IoU | Answerable action | Citation lineage | Warm p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R0 text page | 0/13 | 0.0% | 0.0190 | 0.0194 | 6/13 | 0/13 | 0.023 ms |
| R3 compact region route | 13/13 | 100% | 0.9764 | 0.9316 | 13/13 | 13/13 | 0.053 ms |

R3 retained every attempt-002 quality result and corrected both equation
abstentions. It also passed 3/3 table relationships, 2/2 no-evidence cases, 2/2
integrity cases, 2/2 cross-course isolation cases, 2/2 text controls, zero
unsupported descriptions, and zero online vision calls.

The 13/13 complete@3 Wilson 95% interval is 77.2% to 100%; the small synthetic
sample therefore remains an architectural pilot rather than a general quality
claim.

## Operational results

| Candidate | Release chunks | Offline mean / p95 per asset | OCR calls | Crop bytes | Warm p50 / p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| R0 text page | 7 | 35.7 / 66.0 ms | 0 | 0 | 0.018 / 0.023 ms |
| R3 compact region route | 44 | 65.1 / 111.6 ms | 3 | 594,905 | 0.025 / 0.053 ms |

The compact route remained 0.030 ms slower in absolute p95 and 129% slower
relative to the tiny seven-chunk control. The frozen gate allowed only 20%, so
it failed. The repeated measurement makes the relative overhead reproducible;
it is not appropriate to relabel it as timer noise.

## Hard gates

Passed 13/14:

- complete visual evidence@3;
- atomic recall@5;
- region nDCG improvement;
- top-1 localization IoU;
- table relationship accuracy;
- unsupported-description rate;
- no-evidence behavior;
- isolation;
- text-control non-regression;
- citation lineage;
- zero online vision calls;
- answerable-action accuracy; and
- integrity accuracy.

Failed: relative warm retrieval p95.

## Validity review

- Calibration/development separation: preserved; development only.
- Historical held-out read: false.
- Metric implementation: corrected one-to-one multimodal evaluator from #85.
- Data corrections: only the pre-registered `1.0.1` overlay from attempt 002;
  no attempt-003 label changes.
- Run invalidated: no.
- Important limitation: the latency comparator is an extremely small local
  BM25 control, not an end-to-end product workload. Its frozen result is still
  binding for this run.

## Decision

- Outcome: **Refine**
- Selected multimodal retrieval profile: none
- Product foundation retained: region models, offline parser boundary, scanned
  PDF API ingestion with injected OCR, original crops, source-version lineage,
  access-checked crop delivery, and deterministic routing implementation
- Profile change: none
- Retained fallback: selected text profile with BM25 rollback
- Historical held-out: closed

Do not continue tuning on this 21-case development set. The next useful study
must use representative real/synthetic-at-scale documents and an end-to-end
latency budget that includes selected retrieval and generation. A production
OCR provider and any vision-description provider also require separate
prospective qualification. Opening the historical held-out split is not
justified by this result.

## Limitations and follow-up

This result does not establish OCR accuracy, layout robustness across real
lecture PDFs, description faithfulness, deployed latency, cost/capacity,
professor usability, or production readiness. It only demonstrates that the
new interfaces and deterministic synthetic path can retrieve and cite the
authored regions correctly.

## Learning notes

The system now separates three concerns correctly: original regions are source
truth, source-derived labels support search, and generated descriptions remain
non-authoritative metadata. The remaining micro-latency failure should be
evaluated in a representative product workload rather than optimized repeatedly
against the same tiny development set.
