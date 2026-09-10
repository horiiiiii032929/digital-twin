# Final experimental generation selection004

Decision: **Keep the existing release unchanged; retain V4 as the experimental
comparison control and Refine the V19 Luna audit candidate.** V4 is not the
submitted release's deterministic factual generator. This experiment does not
replace that release profile or demonstrate a globally best model.

## Paired evidence

Twelve exposed synthetic cases, two dependent turns per arm, one live pass under
the same code epoch. All48 outputs retained, including withheld/failed responses.
The Mini reviewer rated every output twice under the same source/profile inputs.

| Diagnostic measure | V4 experimental control | V19 Luna-low + Luna-medium audit |
| --- | --- | --- |
| Outputs acceptable in both ratings | 13/24 | 17/24 |
| Outputs with any grounding-defect rating | 2/24 | 0/24 |
| Outputs with any profile-defect rating | 9/24 | 4/24 |
| Outputs with any citation-defect rating | 0/24 | 0/24 |
| Safe graph failure responses | 1/24 | 4/24 |
| Median end-to-end turn time | 5.36s | 13.15s |
| 95th-percentile turn time, nearest rank | 10.63s | 32.12s |
| Generation-run cost for24turns | US$0.014497 | US$0.049363 |

**These ratings are diagnostic, not qualified accuracy estimates.** The earlier
standalone instrument003 calibration passed64/64. In this run its repeated
calibration passed63/64: one correct-looking semantic review supplied an invalid
exact evidence excerpt. Six of96 product ratings also failed validation. The
strict predeclared gate remains failed; no averaging or post-hoc threshold change
converts it to a pass. Repeated model ratings do not establish human validity.

Even setting that limitation aside, the exploratory paired difference of+16.7
percentage points has a case-cluster95%bootstrap interval of−8.3to+41.7points
(12clusters,10000resamples,seed20260908). The interval includes no improvement.
The candidate also has profile defects and more safe failures, so replacement is
not supported. A hypothetical withdrawal question receives a useful explanation
in the candidate, but some later turns are withheld; improvements are not uniform.
No population95%quality, real learning, instructor fidelity or usability claim.

## Reproducibility and failures

[Review and selection record](records/post-report-final-selection-004-mini-review-live-001.json)
contains all control/product ratings, exact model/prompt/caps, hashes, paired
outputs, operational metrics and gates. [Generation series004](post-report-final-selection-004-results.md)
links all twelve run records. Series002 wrapper-identity failures and series003
adapter-keyword failures remain registered separately, not pooled into this code
epoch. The seven newly authored cases became exposed development during those
runs. The final comparison did not revise questions, sources or expected meanings.

Review: gpt-5.4-mini-2026-03-17, low,1800tokens, concurrency4,no retries;160calls,
US$0.410598,130.75s,unknown-cost calls0,source unchanged. Product: gpt-5.6-luna
low planning/draft and medium audit/repair,3000caps. Candidate three provider schema
failures retained. All exact requests and returned identity/usage are in artifacts.
Process memory for external-review/product runs was not separately sampled.
The independent local integration003 measured its own memory and passed152checks;
it is not a live-model quality result.

The source-only semantic reviewer command is reproducible via
`uv run python -m scripts.run_post_report_blind_review --execute --model mini --version 3 --expected-count 48 --product-run-ids <the twelve series004 run IDs> --output-dir reports/generated/<fresh-id>`.
Reserve US$4.80 before160calls under the cumulative US$30ceiling. The exact analysis
script and its hash are stored with the ignored run artifacts; durable per-rating
and per-case records allow independent recalculation. No new run is implied.
