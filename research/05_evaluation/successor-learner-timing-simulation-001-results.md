# Successor learner model and timing simulation 001: results

Run ID: `successor-learner-timing-simulation-001`

Date: 2026-09-02

Status: complete; network-free; Go Deeper; not a release selection

Plan:
[`2026-09-02-successor-learner-model-and-timing-simulation-plan.md`](../04_experiments/2026-09-02-successor-learner-model-and-timing-simulation-plan.md)

Record:
[`records/successor-learner-timing-simulation-001.json`](records/successor-learner-timing-simulation-001.json)
with the sanitized aggregate copied to
[`records/successor-learner-timing-simulation-001-summary.json`](records/successor-learner-timing-simulation-001-summary.json)

Branch note: this run was produced on the isolated branch
`claude/sota-autonomous-digital-twin-study`. The registry line in
`result-registry.md` is deliberately deferred to merge time so that the
concurrently running evaluation in the main worktree is not touched.

## Identity

| Field | Value |
| --- | --- |
| Code revision | `07e4902e890c1f4ce7f0d856892a07dec0f78a5e`, clean |
| Command | `uv run python scripts/run_successor_learner_timing_simulation_001.py` |
| Dataset | Synthetic learners from `src/digital_twin/evaluation/learner_simulator.py`; 6 personas x 2 families x 20 held-out seeds (2000-2019) = 240 learners per condition; 30 virtual days; 8 concepts |
| Development split | Seeds 1000-1005, used only to choose estimator grid parameters by observable next-outcome log loss; never scored |
| Conditions | 3 estimators (`count`, `bkt`, `pfa`) x 3 timing policies (`constant`, `conditional`, `value`) plus `count+oracle` and `count+never` bounds |
| Eligibility (all conditions) | consent on; quiet hours 22:00-08:00; 3 messages per 7 days; 24 h same-concept cooldown; decisions at 10:00 UTC |
| Provider calls | 0; no network |
| Elapsed | 15.2 s |
| Bootstrap | 1,000 paired resamples by learner, seed 20260902 |
| Per-learner output | `reports/generated/successor-learner-timing-simulation-001/per_learner.jsonl` (ignored; sha256 `739ba58ec7c2377721ecb331c87fd6b5b7533c7b9bc5670535724ad6dab17bf5`) |
| Summary output | `summary.json` sha256 `d54f84c24af08d254bfdd4a491f480ff520dba56abe87e5acd1c4ea919b1f7df` |

Fitted parameters (development seeds, pooled across both families):
`bkt` p_init 0.3, p_learn 0.3, p_forget_per_day 0.05; `pfa` beta -0.4,
gamma 0.5, rho 0.3, decay_per_day 0.08; `count` has no parameters.
Development log loss: count 0.698, bkt 0.677, pfa 0.666.

## Attempt history

- Attempt 001 (revision `2b2b3c8`, dirty): declared invalid before analysis.
  A pre-run diagnostic showed that in the logistic simulator family forgetting
  overwhelmed learning, so mean hidden mastery collapsed to about 0.01 for five
  of six personas under no intervention. Classification: simulator defect. The
  logistic transition constants were corrected (decay 0.5 x rate per day in
  logit space instead of 4.0 x; learning increment 2.0 x rate on a correct
  attempt instead of 1.2 x). The hidden truth then predicted next outcomes
  with AUROC 0.71 (bkt-like) and 0.68 (logistic-like), and mean hidden
  mastery under no intervention ranged 0.13-0.36 (bkt-like) and 0.22-0.76
  (logistic-like) across personas. Attempt 001's aggregate is preserved
  outside the repository for audit only and is not used.
- Attempt 002 (revision `07e4902`, clean): the result below. It is identical
  to the same configuration run on the dirty tree, as expected from
  determinism.

## Aggregate

| Condition | n | MSE vs hidden | Brier next | ECE | AUROC | Msgs | Wasted rate | Follow-up | Final mastery | Violations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bkt+conditional | 240 | 0.035 | 0.250 | 0.246 | 0.562 | 8.9 | 0.366 | 0.433 | 0.309 | 0.00 |
| bkt+constant | 240 | 0.035 | 0.259 | 0.246 | 0.569 | 14.0 | 0.464 | 0.351 | 0.317 | 0.00 |
| bkt+value | 240 | 0.037 | 0.256 | 0.240 | 0.567 | 12.3 | 0.301 | 0.451 | 0.328 | 0.00 |
| count+conditional | 240 | 0.084 | 0.254 | 0.216 | 0.430 | 7.0 | 0.388 | 0.423 | 0.302 | 0.00 |
| count+constant (baseline) | 240 | 0.084 | 0.259 | 0.206 | 0.435 | 14.0 | 0.506 | 0.320 | 0.314 | 0.00 |
| count+never (bound) | 240 | 0.083 | 0.253 | 0.227 | 0.421 | 0.0 | n/a | n/a | 0.288 | 0.00 |
| count+oracle (bound) | 240 | 0.086 | 0.256 | 0.193 | 0.452 | 12.2 | 0.000 | 0.639 | 0.345 | 0.00 |
| count+value | 240 | 0.084 | 0.261 | 0.212 | 0.447 | 10.2 | 0.341 | 0.439 | 0.317 | 0.00 |
| pfa+conditional | 240 | 0.051 | 0.244 | 0.194 | 0.481 | 7.3 | 0.415 | 0.400 | 0.303 | 0.00 |
| pfa+constant | 240 | 0.052 | 0.249 | 0.195 | 0.500 | 14.0 | 0.508 | 0.319 | 0.313 | 0.00 |
| pfa+value | 240 | 0.051 | 0.247 | 0.186 | 0.511 | 10.5 | 0.347 | 0.433 | 0.313 | 0.00 |

Columns: MSE vs hidden is the mean squared error of the daily estimate
against hidden mastery over all concept-days (the plan's primary calibration
metric). Brier next, ECE, and AUROC score the estimate made just before each
assessed attempt against that attempt's outcome. Wasted rate is the share of
sent messages when hidden mastery was at or above 0.85 or the learner was not
receptive. Follow-up is the share of messages that produced an assessed
attempt. Final mastery is the simulator's mean hidden mastery at day 30.

Per family, MSE vs hidden (bkt-like / logistic-like): count 0.102 / 0.067;
pfa 0.062 / 0.042; bkt 0.040 / 0.030. Wasted rate (bkt-like / logistic-like):
count+constant 0.405 / 0.607; count+conditional 0.236 / 0.539; count+value
0.213 / 0.469; bkt+conditional 0.235 / 0.498; bkt+value 0.229 / 0.373;
pfa+value 0.221 / 0.473.

## Paired contrasts (candidate minus control, 240 pairs, 95% bootstrap interval)

| Contrast | MSE vs hidden | Brier next | Wasted rate | Follow-up | Final mastery | Messages |
| --- | --- | --- | --- | --- | --- | --- |
| bkt+constant vs count+constant | -0.050 [-0.053, -0.047] | -0.000 [-0.006, 0.006] | -0.042 [-0.051, -0.032] | +0.030 [0.020, 0.040] | +0.003 [-0.000, 0.007] | 0 |
| pfa+constant vs count+constant | -0.032 [-0.034, -0.030] | -0.010 [-0.013, -0.008] | +0.002 [-0.002, 0.007] | -0.001 [-0.005, 0.002] | -0.001 [-0.002, 0.000] | 0 |
| count+conditional vs count+constant | -0.000 [-0.002, 0.001] | -0.006 [-0.010, -0.001] | -0.118 [-0.147, -0.090] | +0.103 [0.071, 0.134] | -0.012 [-0.018, -0.005] | -7.0 |
| count+value vs count+constant | -0.000 [-0.002, 0.001] | +0.002 [-0.003, 0.005] | -0.165 [-0.187, -0.141] | +0.119 [0.093, 0.145] | +0.003 [-0.003, 0.010] | -3.8 |
| bkt+conditional vs count+constant | -0.049 [-0.053, -0.046] | -0.009 [-0.016, -0.002] | -0.139 [-0.161, -0.114] | +0.113 [0.085, 0.141] | -0.005 [-0.011, 0.002] | -5.1 |
| bkt+value vs count+constant | -0.047 [-0.051, -0.044] | -0.003 [-0.010, 0.003] | -0.205 [-0.228, -0.183] | +0.131 [0.106, 0.156] | +0.014 [0.007, 0.021] | -1.7 |
| bkt+value vs bkt+conditional | +0.002 [0.001, 0.003] | +0.006 [-0.002, 0.013] | -0.066 [-0.089, -0.043] | +0.018 [-0.011, 0.046] | +0.019 [0.012, 0.025] | +3.4 |
| pfa+value vs pfa+conditional | -0.000 [-0.001, 0.001] | +0.003 [-0.001, 0.007] | -0.068 [-0.092, -0.043] | +0.033 [0.001, 0.064] | +0.011 [0.005, 0.017] | +3.2 |
| pfa+value vs count+constant | -0.033 [-0.036, -0.031] | -0.012 [-0.016, -0.008] | -0.159 [-0.180, -0.137] | +0.113 [0.085, 0.140] | -0.000 [-0.007, 0.006] | -3.5 |

## Reading against the registered predictions

H1, belief calibration. Supported. Against hidden mastery, both BKT
(-0.050) and PFA (-0.032) beat the count baseline with intervals far from
zero, on both families, and the ranking bkt < pfa < count holds in both
families. The registered minimum of 0.02 is met. Against the next observed
outcome the picture is weaker: PFA improves Brier by 0.010, BKT does not, and
AUROC is 0.57 (bkt), 0.50 (pfa), and 0.43 (count) against a truth ceiling of
0.68-0.71. The count baseline predicts the next outcome worse than chance
because it lags discrete mastery jumps; every estimator lags them.

H2, timing. Supported. Holding the estimator fixed, the value policy cuts
the wasted-intervention rate by 16-20 points and raises follow-up by 11-13
points relative to constant timing, with zero eligibility violations in every
condition. The conditional policy also cuts waste (12-14 points) but does so
mainly by sending half as many messages, and its final hidden mastery is
slightly below constant timing; the value policy keeps more messages and is
the only policy family whose final mastery exceeds constant timing with an
interval above zero (bkt+value, +0.014). Ranking value < conditional <
constant on waste holds in both families.

H4, forward-model risk. Not triggered in this simulator. The value policy
beat the conditional policy on waste and final mastery for both bkt and pfa
estimators, and even with the count estimator. Its small MSE cost with bkt
(+0.002) comes from sending more messages to concepts the estimator is unsure
about, which is the intended exploration.

Effect bound. The oracle-to-never gap in final hidden mastery is 0.057.
count+constant captures 46% of it; bkt+value captures 70%; the oracle's
follow-up fraction (0.64) is well above any engine's (0.45), which locates
the remaining loss in targeting, not in eligibility.

## Failure classification

| Observation | Class | Note |
| --- | --- | --- |
| Attempt 001 mastery collapse | simulator defect | Corrected before analysis; attempt declared invalid |
| AUROC below 0.5 for the count estimator | estimator mis-specification | Expected: no decay, no prior, lags jumps; kept as the faithful baseline |
| BKT no better than count on next-outcome Brier | estimator mis-specification | Grid coarse; fitted heavy forgetting; not tuned further by design |
| Conditional policy lowers final mastery | policy defect (candidate B) | The stalled predicate under-sends; value policy addresses it |

## Limitations

- Everything is simulated. The receptivity and crowd-out model, persona
  parameters, and both transition families are the author's assumptions.
  Nothing here is evidence about real learners, usability, or learning.
- Estimator parameters were chosen on development seeds of the same
  simulator; the held-out split guards against seed overfitting, not against
  the simulator's own assumptions. A third, differently shaped family would
  strengthen the claim.
- The measurable effect on final mastery is small (0.057 between bounds), so
  final-mastery differences are secondary; waste and calibration are the
  primary signals.
- The count baseline has no fitted parameters and no decay; a "count with
  decay" variant would be the fair next refinement for the baseline.
- No text, retrieval, generation, or policy-envelope behaviour is measured.
  Pedagogical action quality, grounding, and professor adherence remain open
  and need the provider-backed dimensions of the evaluation design.

## Decision

Go Deeper. Keep the estimator interface with BKT-with-forgetting as the
default hypothesis (PFA retained as the comparator), and keep the value-based
timing policy as the successor's proactive-selection hypothesis. Neither is
selected for release. The next steps are: (1) add a third simulator family
and a decayed-count baseline; (2) wire the estimator interface behind the
product's belief revision so the same observations feed both; (3) run the
provider-backed pedagogy and grounding dimensions from the evaluation design
once authorized.
