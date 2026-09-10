# Post-report source assessment V2

Decision: **Keep V2 as the explicit experimental assessor; Go Deeper on generalization.** The earlier failure to abstain on an unsupported professor target is fixed in this32-case exposed development packet. No global quality or real mastery claim follows.

| Method | Label agreement | Assessed coverage | False correct | Boundary judgments |
| --- | --- | --- | --- | --- |
| Literal control | 24/32 | 8/32 | 0 | 0 |
| Luna V1, prior run | 30/32 | 18/32 | 0 | 1 |
| Luna V2 | 32/32 | 16/32 | 0 | 0 |

V2 first requires every professor-target clause to be literally supported in an approved source range, then lets Luna interpret the student's attempt. It correctly abstained on the unsupported target and the extra unsupported assertion that had caused V1 errors. Seven cases prevented any provider call. Other abstentions are retained; increasing coverage alone is not the objective. The32/32 accuracy Wilson95% interval is[0.8928,1.0], so the small observed perfect result does not establish95% population accuracy. Gold is assistant-authored and the same cases were already exposed.

Runtime:25 provider calls,13,709 input and2,175 output tokens, US$0.0053518, 57.946s, peak RSS323960832 bytes, zero unknown-cost calls. Sources unchanged. No new Sol call was made. The [record](records/post-report-source-assessment-002-luna-live-001.json) retains per-case expected/outcome, exact configuration, failure slices and hashes. Artifact directory: `reports/generated/post-report-source-assessment-002-luna-live-001`. Code `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty tree with an archived snapshot.

Reproduce: `uv run python -m scripts.run_post_report_assessment --live --model luna --assessment-version v2 --output-dir reports/generated/post-report-source-assessment-002-luna-live-001-repeat` using a fresh output directory and the shared spending ledger. The runtime assessor and the external Nano/Mini reviewers have different roles; changing the latter did not change this Luna assessment run. Retain V1 as a historical control and literal assessment/abstention as the fallback. Do not claim student learning or independent human validation.
