# Evaluation result: post-report-audited-generation-004

## Run identity

Five sequential live runs on 2026-09-08, code `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty. Per-run records preserve exact source snapshots, input hashes, calls and roles. Status: completed, failed integration gate. Review by coding assistant, not independent.

## Decision context

The [prospective plan](../04_experiments/post-report-audited-generation-004.md) compares V4 with V18 plus context retrieval. Prediction: fewer known content/coverage failures; no candidate-owned critical errors, complete cost accounting, all histories and working final-audit integration. Keep existing release fallback; no promotion.

## Data and sample size

Five deliberately exposed failure contexts, three synthetic approved source cards per course, two turns per arm with restart: ten histories, twenty responses. No real student data. These are diagnostic repeats, not fresh confirmation or a powered accuracy sample.

## Exact configuration

V4 control uses Luna-low; V18 uses Luna-low planner/draft and configured Sol-medium final audit/repair, output cap 3000. Only candidate has previous-student-query-v1. One repetition, schedule seed 7801, no provider seed guarantee. Every run reserves $12 and 144 calls, sequentially releasing unused known reservation. All selected/default profiles remain unchanged.

## Aggregate and slice results

All 10 candidate responses were withheld: one no-evidence and nine safe graph failures. Final-audit role calls were zero. V4 had five major, one minor and four acceptable outputs in assistant review. All ten histories completed both turns and restart; that operational success did not satisfy the quality gate. Per-output reviews retain source, question, response, severity and cause. No population confidence intervals are appropriate.

| Run | V4 severity | V18 severity | Calls | USD |
| --- | --- | --- | --- | --- |
| [post-report-audited-generation-004-case-01-live-001](records/post-report-audited-generation-004-case-01-live-001.json) | {'major': 1, 'acceptable': 1} | {'major': 2} | 4 | 0.0016518 |
| [post-report-audited-generation-004-case-02-live-001](records/post-report-audited-generation-004-case-02-live-001.json) | {'major': 2} | {'major': 2} | 6 | 0.0026516 |
| [post-report-audited-generation-004-case-03-live-001](records/post-report-audited-generation-004-case-03-live-001.json) | {'acceptable': 1, 'major': 1} | {'major': 2} | 6 | 0.0027600 |
| [post-report-audited-generation-004-case-04-live-001](records/post-report-audited-generation-004-case-04-live-001.json) | {'acceptable': 2} | {'major': 2} | 6 | 0.0025846 |
| [post-report-audited-generation-004-case-05-live-001](records/post-report-audited-generation-004-case-05-live-001.json) | {'minor': 1, 'major': 1} | {'major': 2} | 6 | 0.0028090 |

## Operational measurements

Total 28 calls, $0.0124570 reported cost, zero unknown-cost calls. Per-run elapsed time and tokens are in records; process memory was not measured. Latency includes in-process persistent tutoring, not HTTP/network throughput. Source start/end checks pass.

## Failures and limitations

Runtime history uses student/tutor roles and an action field, while the final auditor accepts only user/assistant and content. Follow-ups were rejected before audit. The recorded transport also recreated a generic schema serializer, losing the audit client's explicit task schemas. Local replay and a new actual-history plus recorded-role regression reproduce these boundaries. Direct generator tests with empty history and simple injected clients had missed both integration problems. Neither problem justifies weakening the auditor's source or history boundary.

V4 still misses requested numerical applications and retrieval context. Withholding is counted as failure; it is not evidence of improved truthfulness. Generated but withheld V18 drafts are not delivered-answer successes. All model judgments remain fallible and independent human review is pending.

## Decision and next action

**Refine, no promotion.** Add explicit role translation with exact content preservation and retain the concrete transport's schema in cost/admission serialization. Repeat the same frozen five contexts only after the integration regression passes; retain this unfavorable series. Submitted report unchanged; these results are post-submission development.
