# Plain-language teaching demo001 results

## Run identity

Run: `plain-language-teaching-demo-live-001`, 2026-09-08. Completed application
trajectories with one withheld response. Code revision
`9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty workspace. No source hash drift.
[Exact machine record](records/plain-language-teaching-demo-live-001.json)
contains the runner manifest, versions, role configurations, input/code hashes,
all eight delivered messages and original artifact paths.

## Decision context and data

[Prospective plan](../04_experiments/plain-language-teaching-demo-001.md).
Question: can a familiar, self-contained topic make teaching-profile behavior
understandable without invented proper names or unseen documents?
[Dataset](datasets/plain-language-teaching-demo-v1.json): one synthetic password
reset rule, explanatory and Socratic profiles, identical two student turns per
profile. No private data. Eight responses across V4 and V19 Luna audit candidate.
One topic is deliberately illustrative, not a representative quality dataset.
No exclusions or selective retries. All cases become exposed development.

Expected behavior was recorded before execution: source consistency, appropriate
initial teaching stage, meaningful follow-up, no invented account details and no
unexplained names. Inspection below is author qualitative review, not a calibrated
independent model grade or a real professor's assessment.

## Configuration and execution

Existing paired persistent application-service runner; seed7801, one repeat,
concurrency4, 3000-token output caps. `gpt-5.6-luna` low for planning/generation;
candidate revision uses the same model at medium reasoning. No Sol. Sources and
profiles pass through the actual configured application services; this is not a
standalone chat prompt or browser recording. The second turn restarts the runtime
and preserves conversation identity. Exact reproducible command is in the plan.

All four two-turn histories completed. Completion means a response was returned,
including the explicit safe failure, not that every response was useful.
The candidate retained one provider schema-validation failure and delivered one
safe failure. The precise chain behind withholding has not been fully diagnosed.

## Observations by profile

| Profile and configuration | First turn | Follow-up |
| --- | --- | --- |
| Explanatory, V4 control | Gives expiry rule, no explicit yes/no or check question | States that replacement invalidates old links |
| Explanatory, V19 candidate | Directly says the link expired and asks a check question | Directly answers the new-link question and asks a check question |
| Socratic, V4 control | Generic request for the student's explanation | Gives a relevant hint but asks for revision of an already largely correct attempt |
| Socratic, V19 candidate | Prompts reasoning about the expiration rule | Withholds response after validation fails |

These are narrow output observations. The responses, including failure, are
preserved verbatim in the machine record and
[readable presentation evidence](../../reports/presentation/examples/plain-language-ai-dialogue-ja.md).
A response asking a check question does not show that learning occurred.

## Operations

Elapsed run time62.29seconds. V4:6attempts,6completed calls, US$0.002586,
6204input/1121output tokens. V19:12attempts,11completed calls,1provider schema
failure, US$0.0099624,18270input/5257output tokens. Total18attempts,
US$0.0125484, unknown-cost calls0. Per-response elapsed milliseconds are in the
record; these eight dependent turns do not support a general latency benchmark.
Memory, hosted throughput, cold start and external-user usability were not
measured. Unused US$14.08 reservation released in the cumulative US$30 ledger.

## Decision and limitations

**Keep** the plain-language material and explanatory exchange as an understandable
illustration of actual experimental behavior. **Refine** the candidate remains
the component decision; no selected release or app default changes. Preserve
V4 as comparison and retain all failed/withheld output. A complete deck should
link the positive example to the remaining limitation rather than presenting
this as a generally reliable or professor-faithful tutor.

The source describes a synthetic course rule, not every real password-reset
service. One familiar topic, two profiles, no human learners, no independent
quality certification and no real-instructor history. No learning outcome or
robustness claim. The source wording and expected follow-up were authored for
presentation development. The observed difference is not an isolated estimate
of profile effect because configuration also differs between arms; profile
comparisons must keep that distinction visible.
