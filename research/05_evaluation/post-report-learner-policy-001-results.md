# Post-report learner and policy comparison 001

Decision: **Keep the count control, Refine decay-based intervention, Go Deeper on utility; no product promotion.**

The fixed grid completed 8,160 thirty-day synthetic histories: four estimators × four timing policies plus a count/oracle reference, each over 12 personas, two simulator families and 20 seeds. Zero eligibility violations occurred. The experiment took 12.924 seconds and 319750144 bytes peak RSS, with no external calls or cost. See the [complete configuration, slices and paired intervals](records/post-report-learner-policy-001-local-001.json).

| Estimator | Observable-outcome Brier, lower is better | Paired mean change vs count (95% bootstrap interval) |
| --- | --- | --- |
| Count | 0.25508 | Reference |
| Decay | 0.24821 | −0.00687 [−0.00837, −0.00549] |
| BKT | 0.25141 | −0.00367 [−0.00659, −0.00093] |
| PFA | 0.26588 | +0.01080 [+0.00739, +0.01389] |

Forecast comparison uses exactly the same 480 open-loop observation histories (7,535 observations); BKT latent probability is converted through guess/slip into observable-success probability. History means receive equal weight. Raw closed-loop score errors are not interchangeable probability measures and are not used to rank these estimators.

Better forecasting did not establish a better intervention. Decay+conditional versus count+conditional changed simulated final hidden mastery by +0.00112 [−0.00076, +0.00298], while increasing messages by +0.7479 and wasted interventions by +0.3542 [0.2729, 0.4354]. It therefore does not justify replacing count+conditional. BKT+value increased simulated final hidden mastery by +0.02885 [0.02413, 0.03345], but added approximately 5.16 messages; it needs a utility decision rather than unconditional adoption. PFA's worse open-loop forecasting also prevents declaring it best from a single closed-loop gain.

These timing-policy components differ from the application's analytic planner. Simulator assumptions generate hidden mastery and cannot show actual learner benefit. The oracle accesses synthetic hidden state only as a reference. Bootstrap intervals describe the declared simulation grid, not a human population. All unfavorable conditions and per-history outputs are retained; no parameter was tuned in this run.

Reproduce: `uv run python -m scripts.run_post_report_learner_policy --output-dir reports/generated/post-report-learner-policy-001-local-001-repeat`. Artifacts: `reports/generated/post-report-learner-policy-001-local-001`. Code `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty tree, exact archived source/configuration. Historical release remains unchanged.
