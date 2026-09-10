# Evaluation result: post-report paired quality 001

## Run identity

Two retained runs on 2026-09-08: `post-report-paired-quality-001-contract-001`
(contract only) and `post-report-paired-quality-001-live-001` (completed, Refine).
Base revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty working tree.
The live source archive remained unchanged throughout execution. Exact inputs,
configuration, invocation, source hashes and operational counts are in the
[live record](records/post-report-paired-quality-001-live-001.json).

## Decision context and data

The [prospective plan](../04_experiments/post-report-paired-quality-001.md)
compares V4 with compact typed V10 on 12 new synthetic course scenarios,
two instructional profiles and two turns: 24 contexts, 48 histories, 96 turns.
All three source cards for each of four courses were published together.
This is exposed development data, not a sealed or independent qualification set.
Sources contain no real student or professor information. The sample covers
the scenario/profile grid once; no population confidence interval is justified.
No responses were excluded.

Both arms used `gpt-5.6-luna`, low reasoning, 3000 output tokens, seed 7801,
one repetition and four concurrent histories. Runtime restarted between turns.
The boundary is persistent `StudentTutoringService`, not HTTP/authentication.
The contract run injected provider failures, used zero external calls and
completed all 48 histories. It verifies fallback execution only, not quality.

## Results

All 96 delivered responses were read against the source and prospective rubric
by the coding assistant. These unblinded judgments are **not independent human
review or measured factual accuracy**. [Every response and finding is retained](reviews/post-report-paired-quality-001-live-001-review.json).

| Assistant review | V4 / 48 turns | V10 / 48 turns |
| --- | ---: | ---: |
| Acceptable in this review | 34 | 34 |
| Acceptable with minor issue | 1 | 0 |
| Needs refinement | 13 | 12 |
| Uncertain support/permission claim | 0 | 2 |
| Follow-up turns needing refinement / 24 | 8 | 10 |

Counting uncertain cases as unresolved, V10 has fewer unresolved turns in four
paired histories, more in six and the same number in fourteen. This does not
support a superiority claim. Per-course/profile/stage counts are in the record.
Neither arm reaches the prospective 95% diagnostic target.

## Hard gates and operations

All 48 histories completed, with 48 restarts; source hash errors: zero.
No private content disclosure was observed, but the packet contains no actual
third-party records and cannot establish authorization security. Two V10 added
permission/privacy assertions require independent review; the critical semantic
gate is unresolved, not passed. Citation identity alone is not a semantic gate.

| Measurement | V4 | V10 |
| --- | ---: | ---: |
| Completed external calls | 70 | 70 |
| Provider failures / unknown costs | 0 / 0 | 0 / 0 |
| Input / output tokens | 77,827 / 14,268 | 89,461 / 7,901 |
| Reported USD | 0.032687 | 0.0273734 |
| Turn median / nearest-rank p95, ms | 4,738 / 7,458 | 3,441 / 6,120 |

Total reported cost: **US$0.0600604**, under the US$8 run cap and US$30 user
budget. Wall time 101.78 seconds. Memory and cold-start isolation were not
measured. Execution cost is not evidence of teaching quality.

## Failures and surprises

- `atlas-withdraw-*`, initial turn: approved source exists but both arms say
  there is no evidence. Retrieval/evidence-selection cause remains provisional.
- `birch-causality-*`, follow-up: both arms decline a supported noncausal
  conclusion as unavailable. This is not a correct boundary refusal.
- `birch-recall-socratic`: safe graph failure replaces the requested numerical
  explanation in both arms despite completed provider calls.
- V4 repeatedly quotes arithmetic inputs without computing the requested result.
- V10 answers several negative yes/no questions with an opening “Yes,” then
  states the correct negative explanation. The ambiguity is an actual defect.
- V10 still asks for another attempt after a genuine attempt in selected
  Socratic cases; more natural prose does not ensure stage compliance.
- V10 adds uncertain claims about permitted de-identified summaries and the
  absence of private information. No disclosure occurred; support is unresolved.

## Decision and follow-up

**Refine; no promotion.** Retain the current selected profile and fallback.
Preserve all unfavorable outputs. Diagnose evidence-selection and graph
validation failures before more prompt-only tuning. Correct yes/no reference
and follow-up stage handling on a separate exposed development packet; prepare
blinded human review with source/rubric and independent ratings before claiming
semantic qualification. No professor fidelity, real-user usability or learning
effect follows from these synthetic examples. Historical evaluations and the
submitted report are unchanged.

## Learning notes

A shorter, more fluent response can still be less useful. Evaluate the answer
to the student's actual request, including the opening polarity, the requested
calculation, the stage of help and every additional permission claim. A safe
fallback is operationally valid but may fail the learning-support task.

## Post-run trace diagnosis

The provider request ledger confirms that the Birch causality follow-up supplied
only the missing-score source to both generators. The answer exists in the
approved course but is absent from that generation input. This narrows the
defect to retrieval/evidence selection or conversation reference handling,
rather than a model ignoring the supplied causality source.

V10 emitted `action: partial` with an empty `missing_details` list for both
Socratic arithmetic failures. The compact contract explicitly rejects this
inconsistent combination. The recall response contained the correct arithmetic,
while the missing-value response still withheld the requested result. Fixing
format alone would therefore repair one symptom without fixing teaching-stage
completeness. V4 emitted source spans with changed capitalization in its two
failed arithmetic responses, violating the exact-span contract. No validator
was weakened and no historical response was rewritten.

A [blinded human-review packet](human-review/post-report-paired-quality-001/README.md)
contains all 96 responses, source context, an empty ratings sheet and a separate
allocation key. It is prepared, not independently scored.
