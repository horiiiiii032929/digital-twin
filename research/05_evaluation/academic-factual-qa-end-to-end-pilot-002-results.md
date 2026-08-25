# Academic factual-QA end-to-end pilot 002

Result ID: `academic-factual-qa-end-to-end-pilot-002`

Decision: **Go Deeper**

## Result

The corrected network-free development run completed from clean revision
`74dcf8ca973a4b253f1b39fcf401370467984a37`. It used 160 synthetic-public
cases, 80 source/question clusters, and three paired T0 conditions. The system
received only the student question and authenticated course context; expected
actions, claims, source IDs, citations, slices, and rationales remained outside
the product boundary until after persistence.

| Condition | Action accuracy | Unsupported boundary releases | Supported retention | Claim complete | Citation precision / recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Any-hit control | 78.75% | 34/80 (42.5%) | 80/80 | 80/80 | 50% / 100% |
| Evidence-selection ablation | 160/160 | 0/80 | 80/80 | 80/80 | 100% / 100% |
| Two-boundary candidate | 160/160 | 0/80 | 80/80 | 80/80 | 100% / 100% |

All 160 draft hashes were identical between the evidence-selection ablation and
the two-boundary candidate. Persistence was 100% consistent. The candidate p50
and p95 turn latencies were 1.05 ms and 3.94 ms on this machine. All conditions
made zero provider calls, used zero tokens, cost USD 0, and read no private,
independent-gold, or held-out data.

For the any-hit control, the cluster-bootstrap 95% interval was 68.5–88.7% for
action accuracy and 25.0–59.5% for unsupported boundary releases. The all-pass
candidate bootstrap is degenerate at 100%/0%; that does not imply zero
population risk and must not be reported as a real-world confidence bound.

## Interpretation

The run validates the corrected product plumbing:

- the evidence gate can select a bounded subset of retrieved hits;
- T0 can fail closed when selected lineage is invalid;
- the generator can expose server-resolved atomic claims;
- unsupported claims are blocked without losing provider accounting;
- paired conditions can reuse exactly the same generated draft.

It also reproduces the any-hit defect: no-evidence and cross-course requests can
receive source-backed but irrelevant answers, and citing every retrieved source
reduces citation precision.

This is not academic effectiveness evidence. The data are unblinded and
deterministically authored, source aliases were created in the same development
design as the questions, and the clean draft arm did not challenge the
post-generation validator with naturally occurring generator errors. Therefore
the 100% candidate score may reflect development-set alignment. The result
cannot select the method or justify deployment.

## Next checkpoint

Freeze a new confirmation instrument using fresh source and question-family
clusters with independently validated labels. Include natural paraphrases,
mixed alias/content multi-source questions, genuine no-evidence and cross-course
boundaries, multimodal strata, and corrupted claim/citation probes. Calibrate
the automated reviewer against a compact human anchor. Numeric gates and the
analysis code must be frozen before opening that split.

If the confirmation fails, preserve the result, diagnose on development data,
and create a new version with a fresh confirmation split. Do not tune on the
consumed confirmation cases. The one-time 002 authorization is revoked.

Raw ignored artifact SHA-256:
`756dcc6624ecc1b9f1e0cd5bf7d47d10883819d310330a89df2601b2d3d27095`.
