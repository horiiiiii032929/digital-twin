# Evaluation result: post-report-audited-generation-005

## Run identity

Five sequential live development runs, 2026-09-08. Code `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty; exact source archived per run. Supersedes the failed integration in [series 004](post-report-audited-generation-004-results.md), which is retained. Per-output reviewer: coding assistant, unblinded.

## Decision context

[Prospective plan](../04_experiments/post-report-audited-generation-005.md): repeat the same known failures after repairing audit history vocabulary and recorded transport schema retention. Prediction: actual audits execute and useful corrections become deliverable. Keep V4/current release fallback. No profile promotion from this small exposed probe.

## Data and sample size

Five known-failure synthetic contexts, three approved source cards per course, two turns per arm, restart between turns, one repetition: ten histories and twenty outputs. No real learner data. Gold meaning/stage rubrics remain excluded from provider input. No representative accuracy or confidence interval claim.

## Exact configuration

V4: Luna-low, 3000 output tokens. V18: Luna-low planner/draft, Sol-medium audit/repair, 3000 output tokens each, at most one protocol repair and one audit-guided repair/re-audit. Only V18 uses previous-student-query-v1. Seed 7801 controls ordering, not provider sampling. Sequential $12/144-call reservations per context; known unused reservations released. Snapshot and exact invocation in each output manifest.

## Aggregate and slice results

V4 severity counts: {'major': 5, 'acceptable': 5}. V18: {'major': 1, 'acceptable': 8, 'minor': 1}. Candidate major issues decreased from five to one in these exposed cases; this is descriptive and includes bundled changes. Three of five contexts had fewer candidate major issues, two were tied; none had more. No delivered candidate critical error identified by assistant review. All ten histories completed two turns and restart.

| Run | V4 | V18 | Calls | Audit-role calls | USD |
| --- | --- | --- | --- | --- | --- |
| [post-report-audited-generation-005-case-01-live-001](records/post-report-audited-generation-005-case-01-live-001.json) | {'major': 1, 'acceptable': 1} | {'major': 1, 'acceptable': 1} | 5 | 1 | 0.0208338 |
| [post-report-audited-generation-005-case-02-live-001](records/post-report-audited-generation-005-case-02-live-001.json) | {'major': 2} | {'acceptable': 2} | 8 | 2 | 0.0349936 |
| [post-report-audited-generation-005-case-03-live-001](records/post-report-audited-generation-005-case-03-live-001.json) | {'acceptable': 1, 'major': 1} | {'acceptable': 2} | 8 | 2 | 0.0365276 |
| [post-report-audited-generation-005-case-04-live-001](records/post-report-audited-generation-005-case-04-live-001.json) | {'acceptable': 2} | {'acceptable': 1, 'minor': 1} | 12 | 6 | 0.1306420 |
| [post-report-audited-generation-005-case-05-live-001](records/post-report-audited-generation-005-case-05-live-001.json) | {'acceptable': 1, 'major': 1} | {'acceptable': 2} | 8 | 2 | 0.0359046 |

## Operational measurements

41 total external calls, 13 actual Sol audit-role calls, $0.2589016 known cost; zero unknown costs. Per-role tokens, timing and calls are recorded. Memory was not measured. The Elm case uses six audit-role calls across two turns, including repair/re-audit. Source start/end hashes agree. Latency is in-process persistent tutoring including model round trips, not a production HTTP benchmark.

## Failures and limitations

Atlas's initial withdrawal question still receives no-evidence despite an available source; the shared retrieval/admission boundary remains to diagnose. V4 omits the mean result, fails another follow-up and loses causal evidence. V18 provides mean=3, recall=37.5%, precision=60%, and preserves the causal limitation on follow-up. Its Elm answer correctly distinguishes reaching a necessary minimum from guaranteeing display, but uses unexplained S1 in prose (minor presentation defect). All original outputs and source quotes are preserved; no answer text replaced.

## Decision and next action

**Go Deeper for V18; Refine retrieval; no promotion.** The connection fix works and known content failures improve. Five exposed cases cannot establish general correctness, model superiority or real educational benefit. Add fresh conditions and independent review; preserve the selected fallback, runtime identity and submitted report.
