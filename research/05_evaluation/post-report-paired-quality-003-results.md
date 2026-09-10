# Evaluation result: post-report conditional revision probe

## Run identity and decision context

Run 002 stopped before external calls or output creation: the unchanged runner
requires US$76.80 conservative reservation for the 96-turn role-routed packet.
The proposed US$8 cap and user's US$30 total could not cover it. This unfavorable
preflight is retained in its [record](records/post-report-paired-quality-002-live-001.json).
No calls or cost occurred. We did not weaken the runner's reservation rule.

The [prospective successor plan](../04_experiments/post-report-paired-quality-003.md)
selected four already-exposed failure contexts before running 003. It compares
V4 with existing `v14-luna-sol-medium`: Luna low planner/generation and Sol medium
conditional revision, 3000 output cap, seed 7801, one repeat, four concurrent
histories, one restart between each pair of turns. Exact configuration and
invocation are in the [record](records/post-report-paired-quality-003-live-001.json).
Base revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty tree, unchanged
source archive throughout. Default and selected profiles are unchanged.

## Data, metrics and results

Eight histories / 16 responses across the four known failure contexts, using
synthetic course sources only. No exclusions. This selection is deliberately
biased toward observed failures, not a representative accuracy sample. No
population confidence interval is justified. All responses received unblinded
assistant review against the original source and prospective rubric.
[Every delivered response and finding is retained](reviews/post-report-paired-quality-003-live-001-review.json).

| Assistant-reviewed defects | V4 / 8 turns | V14 / 8 turns |
| --- | ---: | ---: |
| Major | 3 | 1 |
| Critical | 0 | 1 |
| Minor only | 1 | 0 |

Compared within four paired histories, V14 has fewer major/critical defects in
two, more in one and the same count in one. The original 95% diagnostic targets
are not reached. Independent review has not occurred.

## Failures and hard gates

The revision composition produces the requested recall/precision and mean
calculations, and avoids the earlier misleading opening Yes in the withdrawal
follow-up. It still cannot answer the initial withdrawal question when the
right course evidence is missing from generation input.

A different defect appears in `elm-groups-explanatory`, turn 2: the source says
Elm shows the summary **only when** at least five learners contribute. The
answer says reaching five means Elm **shows** it. The source establishes a
necessary display threshold, not sufficiency or guaranteed display. The rubric
requires threshold only. This is classified as a critical unsupported guarantee
under the prospective rubric, pending independent confirmation. It must not be
silently accepted because the response otherwise explains the learning limit.

All eight histories completed and restarted, with unchanged source hashes.
The critical semantic gate fails on assistant review. No private content was
disclosed, but this packet includes no actual third-party records and does not
measure authorization security.

## Operations and decision

V4: 11 calls, 12,341 input / 2,213 output tokens, US$0.0051238.
V14: 18 calls (4 planner, 7 generation, 7 revision), 27,545 input / 2,173 output
tokens, US$0.0723866. Zero provider failures or unknown-cost calls. Total for this
run US$0.0775104; total new evaluation spend US$0.1375708. Per-turn elapsed times
are preserved in the review record; memory and cold-start effects were not measured.

**Refine; no promotion.** The existing revision stage repairs some observed
failures but still introduces an unsupported implication and cannot solve missing
retrieval input. Preserve the selected fallback, require independent review,
and evaluate retrieval/context repair separately from response revision. These
results establish neither professor fidelity nor usability or learning gains.
