# Goal completion scope development 001

**Keep the objective-scoped completion correction.** Under matched 30-day
simulation conditions, unsupported goal completions fell from 12 to zero.
Supported completions remained possible. This result validates a lifecycle
correction; it does not establish better tutoring or human learning.

## Design and evidence

The [prospective plan](../04_experiments/2026-09-06-goal-completion-scope-plan.md)
specified 72 histories per arm: six personas, two simulator families, three seeds
(9101–9103), and reactive/autonomous conditions. Each history used 30 virtual days
and a day-15 service restart. The six concepts and driver were reused from 025;
these are new stochastic histories on an exposed development fixture, not a fresh
held-out curriculum. All students, sources and time were synthetic.

Both arms used the real product services, SQLite and worker paths with deterministic
generation/planning, zero external LLM calls and zero provider cost. Source archives
and hash manifests preserve the dirty working-tree implementations at HEAD
`e441193c7fa1260ed327ebf43c59483f85817be8`. The archived runner, simulator,
profiles and dependencies match; only `autonomy_control.py` and `service.py`
differ. Actions can change later simulated student responses, so the two arms
share initial conditions and seeds rather than identical transcripts.

## Primary correctness results

| Measure | Control v1 | Objective-scoped v2 |
| --- | ---: | ---: |
| Histories completed | 72 | 72 |
| Completed goals inspected | 26 | 15 |
| Completions supported by target concepts | 14 | 15 |
| Unsupported completions | 12 | 0 |
| Histories with unsupported completion | 11 | 0 |
| Unresolvable completed objectives | 0 | 0 |
| Consistent service restarts | 72/72 | 72/72 |
| Attribution accuracy / assessment agreement | 100% / 100% | 100% / 100% |
| Quiet-hour / frequency / cooldown violations | 0 / 0 / 0 | 0 / 0 / 0 |

The control failed the target-scoped completion gate while passing the older
assessment gates. The candidate passed all 19 run gates, including a positive
completion check. A lower total completion count is expected when unsupported
completions are removed; it is not a lower measured learning success rate.

The independent audit uses committed attribution snapshots at completion time,
matched to exact approved domain objectives. It requires every target concept
to have two correct assessments, no incorrect assessment and confidence >=0.5.
It never pools evidence across conversations or counts rejected observations.
Final databases cannot disambiguate commits sharing an exact virtual timestamp;
the service regressions separately verify that boundary. The finite, dependent
history grid does not justify a population error-rate confidence interval.

The focused component/service/audit suite passed **72 tests**, including 30 new
regressions. These cover multi-goal persistence, partial multi-concept success,
incorrect/unrelated evidence, confidence, missing/ambiguous mappings, scope,
legacy state, uncommitted state, and simultaneous completion/other-goal follow-up.
Three consecutive real service turns also check that a supported objective is
not repeatedly recreated as a new support goal.

The full Python run executed 2,598 tests: 2,585 passed and 13 failed. Eleven
failures were sandbox denials of `ps` in localhost HTTPS tests; the full 13-test
HTTPS module passed with the required local execution permission. Two failures
identified the new runner's missing classification in the repository execution
validator. It was registered alongside the existing deterministic-only 025 runner,
with tests requiring `provider_backed=False`, socket denial and rejection of
`--execute`. The final 83-test targeted recheck passed. Across the initial run and
targeted rechecks, all 2,600 distinct tests were verified; this is not a claim of
one clean full-suite run after the tooling correction. Original failed JUnit
evidence is retained, and product code was unchanged after the paired run.

## Secondary outcomes and remaining limitations

| Autonomous condition, 36 histories per arm | Control | Candidate |
| --- | ---: | ---: |
| Mean proactive messages per history | 9.056 | 10.611 |
| Mean simulated wasted-message fraction | 0.3496 | 0.3572 |
| Mean final hidden simulator mastery | 0.3632 | 0.3608 |
| Mean follow-up fraction | 0.4325 | 0.4152 |

Leaving incomplete goals active increased outreach by 56 messages in total.
The mean hidden-mastery change was -0.0024, with 11 histories increasing,
nine decreasing and 16 unchanged. No learning-quality improvement is established.
Reactive controls were unchanged on the compared outcome measures. These outcomes
are descriptive simulator effects, not estimates of real-student benefit.

Observed wall time was 176.42 s for the control and 315.96 s for the candidate;
peak process RSS was 236,584,960 and 282,034,176 bytes. Broader regression tests
overlapped, so these are not controlled performance comparisons. Product execution
denied external network sockets. At dependency import, LiteLLM attempted to obtain
public pricing metadata, failed DNS and used its packaged local map; no LLM
request occurred.

The correction retains the existing cumulative contradiction rule and does not
interpret arbitrary free-text success criteria. Historical completed statuses are
not rewritten. The planner's attempt-count proxy, intervention usefulness,
professor fidelity and external-model composition require separate evidence.

## Reproduction and decision history

- [Paired record](records/goal-completion-scope-development-001.json): matched per-history differences and input hashes.
- [Baseline record](records/goal-completion-scope-development-001-baseline.json): failed gate, all completions and source identity.
- [Candidate record](records/goal-completion-scope-development-001-candidate.json): all completions, gates and source identity.
- [Historical audit](goal-completion-scope-review-audit-001-results.md): original 025 defects and preserved measurement corrections.
- [Design note](../../docs/goal-completion-scope.md): executable completion semantics and persistence responsibilities.

Run each arm with `uv run --locked python -m scripts.run_goal_completion_scope
--arm baseline|candidate --output-dir <new-directory>` from the corresponding
source snapshot. A candidate source tree cannot be labelled as the baseline.
The source ZIP files and per-case outputs are under
`reports/generated/goal-completion-scope-development-001-{baseline,candidate}/`.
The comparison command is documented in [scripts/README.md](../../scripts/README.md).
The analysis utility was added after arm snapshots and is separately hash-bound.
The new experimental component profile records this correction; the frozen final
release profile is not requalified by this network-free development comparison.
