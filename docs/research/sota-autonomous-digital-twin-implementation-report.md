# Implementation and evaluation report: successor study, stage 1

Date: 2026-09-02

Report ID: `sota-autonomous-digital-twin-implementation-report-001`

Status: report of work done on the isolated branch
`claude/sota-autonomous-digital-twin-study`; nothing here is merged,
selected for release, or authorized for provider, paid, private-data, or
human-study use

Related documents:

- [Independent study](sota-autonomous-digital-twin-independent-study.md)
- [Evaluation design](sota-autonomous-digital-twin-evaluation-design.md)
- [Decision and experiment plan](sota-autonomous-digital-twin-decision.md)
- [Experiment plan](../../research/04_experiments/2026-09-02-successor-learner-model-and-timing-simulation-plan.md)
- [Results](../../research/05_evaluation/successor-learner-timing-simulation-001-results.md)

## 1. What was asked and what was done

The study, evaluation design, and decision documents were written first and
committed (`2b2b3c8`). The user then asked for implementation and evaluation
to begin on this branch without touching the evaluation running in the main
worktree, and with academic rigour.

The logical first step from the decision document's migration plan and its
"smallest fair experiment" table is the one that needs no model call and no
product-code change: test the calibrated-estimator and value-based-timing
components (hypotheses H1, H2, H4) against the current count-based belief and
constant timing on simulated learners with hidden state. Everything about it
is evaluation-first: the plan was frozen before the run, the baseline
reproduces the product's current rule, development and held-out seeds are
disjoint, metrics were chosen in advance, and the first attempt was declared
invalid on a simulator defect rather than tuned.

Work completed, all additive except one allowlist line in
`scripts/validate_repository_execution_freeze.py` (see section 2):

| Artifact | Purpose |
| --- | --- |
| `src/digital_twin/evaluation/learner_simulator.py` | Hidden-state learner simulator: six personas, two transition families, receptivity and crowd-out, deterministic under a seed, text free |
| `src/digital_twin/student/learner_estimators.py` | `LearnerEstimator` interface with three implementations: evidence counts (the current rule), BKT with forgetting, PFA with decay; registry by id |
| `src/digital_twin/student/intervention_policies.py` | One `EligibilityGate` (consent, quiet hours, frequency, cooldown) and the `constant`, `conditional`, `value`, `oracle`, `never` timing policies with an analytic forward model |
| `src/digital_twin/evaluation/successor_simulation.py` | Harness: thirty-day runs, calibration and intervention metrics against hidden truth, independent timestamp-based violation check, development-seed grid fit, paired bootstrap, output writers |
| `scripts/run_successor_learner_timing_simulation_001.py` | Reproducible command with code-revision and dirty-state capture |
| `tests/digital_twin/test_successor_simulation.py` | 14 tests: determinism, family divergence, crowd-out, estimator monotonicity and decay, gate enforcement, policy differences, harness invariants, bootstrap determinism |
| Plan, results, and record files under `research/` | Evaluation-first paper trail |

## 2. Verification

| Check | Result |
| --- | --- |
| `uv run pytest tests/digital_twin -q` | 402 passed (388 pre-existing plus 14 new) |
| `uv run pytest tests -q` (whole suite, one data-dependent test deselected) | 1,488 passed, 67 failed, 22 errors. Every failure and error was inspected: all but one are missing ignored inputs in a fresh worktree (local source snapshots under `data/external`, processed data under `data/processed`, diagram assets and prior run outputs under `reports/generated`) and are unrelated to this branch. The one branch-caused failure was the repository execution-freeze registry test, which requires every `run_*` script to carry a freeze guard or be listed as a network-free entrypoint; the new script was added to that allowlist with a comment, following the precedent of the other deterministic simulations, after which the freeze tests pass (25 passed across the freeze and simulation test files). This is the only change to a pre-existing file on this branch |
| `uv run python scripts/validate_markdown_links.py` | all local links valid |
| External links in the three study documents | 109 checked; 98 return 200; 11 return 403 to automated fetches (ten publisher DOI landing pages behind bot walls and OpenAI's open-models page). Those DOIs are canonical identifiers whose metadata was verified through OpenAlex or Semantic Scholar at research time, as stated in the study |
| Simulation run | 15 s, zero provider calls, clean revision, deterministic across repeated runs |

## 3. Headline result

Run `successor-learner-timing-simulation-001`, 240 learners per condition,
paired by learner, 95% bootstrap intervals.

| Contrast | MSE vs hidden mastery | Wasted-intervention rate | Follow-up fraction | Final hidden mastery |
| --- | --- | --- | --- | --- |
| BKT estimator vs count (constant timing) | -0.050 [-0.053, -0.047] | -0.042 [-0.051, -0.032] | +0.030 [0.020, 0.040] | +0.003 [-0.000, 0.007] |
| Value timing vs constant (count estimator) | no change | -0.165 [-0.187, -0.141] | +0.119 [0.093, 0.145] | +0.003 [-0.003, 0.010] |
| BKT + value vs count + constant (current-like) | -0.047 [-0.051, -0.044] | -0.205 [-0.228, -0.183] | +0.131 [0.106, 0.156] | +0.014 [0.007, 0.021] |
| BKT + value vs BKT + conditional (C vs B analogue) | +0.002 [0.001, 0.003] | -0.066 [-0.089, -0.043] | +0.018 [-0.011, 0.046] | +0.019 [0.012, 0.025] |

Every condition had zero eligibility violations. The estimator ranking (BKT
better than PFA better than counts) and the policy ranking (value better than
conditional better than constant on waste) held in both simulator families.
The oracle-to-never gap in final mastery was 0.057; the current-like
configuration captured 46% of it and BKT with value timing captured 70%.

Two honest negatives: no estimator predicts the next assessed outcome well
(AUROC 0.57 at best against a truth ceiling of about 0.70), and the
conditional policy, the candidate-B analogue, reduced waste mainly by sending
fewer messages and ended with slightly lower hidden mastery than constant
timing.

## 4. What this does and does not show

Shows, within the simulator: a calibrated, decaying estimator keyed to the
learner tracks hidden mastery far better than the current count rule; a
value-margin policy over an analytic forward model sends fewer wasted
messages and more messages that produce an attempt than either constant or
predicate-only timing; the shared eligibility gate holds under every policy.

Does not show: anything about real students, usability, learning outcomes,
pedagogy of generated text, grounding, or professor adherence. The simulator's
receptivity and forgetting assumptions are the author's. The estimators were
grid-fit on development seeds of the same simulator.

## 5. Decision and next steps

Decision recorded in the results file: Go Deeper. The estimator interface
with BKT-with-forgetting and the value-based timing policy become the
successor's default hypotheses for the learner-belief and proactive-selection
planes, pending the provider-backed dimensions.

Next steps in order, none started:

1. Add a third simulator family and a decayed-count baseline to test whether
   the estimator ranking survives a different generator and a fairer baseline.
2. Stage 1 of the migration plan (commit-before-deliver, global kill switch,
   claim validator in every mode, prompt hashing), each behind the existing
   restart and duplication tests.
3. Wire `LearnerEstimator` behind the product's belief revision so the same
   observations feed the product ledger and the estimator, keyed by learner
   and course, in shadow mode.
4. Build the remaining evaluation-design pieces (adversarial and provider-
   failure families, out-of-process adapter, McNemar and Holm as code).
5. Run the provider-backed pedagogy and grounding dimensions only when
   authorized.

## 6. Isolation statement

All work was done in the worktree
`.claude/worktrees/sota-autonomous-digital-twin-study` on branch
`claude/sota-autonomous-digital-twin-study`. No file under `main`'s working
tree, `reports/generated/` of the main worktree, the result registry, hidden
gold, sealed datasets, or existing evaluation instruments was read or
modified. The registry line for this run is deferred to merge time for the
same reason. No pull request was opened.
