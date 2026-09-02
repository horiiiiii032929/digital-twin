# Hidden-state learner extension 014: results

Run ID: `governed-full-autonomy-v2-1-hidden-state-learner-extension-014`

Date: 2026-09-02

Status: complete (deterministic, network-free arm); Go Deeper; not a release
selection; the provider-backed arm has not run and has no bounded authorization

Extends: `governed-full-autonomy-v2-1-cross-engine-evaluation-010` (same
product adapter, contracts, and response payload; new dimensions scored from a
hidden-state simulated learner that never reaches the adapter)

Instrument:
[`instruments/governed_full_autonomy_v2_1_hidden_state_learner_extension_014.json`](instruments/governed_full_autonomy_v2_1_hidden_state_learner_extension_014.json)

Record:
[`records/governed-full-autonomy-v2-1-hidden-state-learner-extension-014.json`](records/governed-full-autonomy-v2-1-hidden-state-learner-extension-014.json)
with the sanitized aggregate at
[`records/governed-full-autonomy-v2-1-hidden-state-learner-extension-014-summary.json`](records/governed-full-autonomy-v2-1-hidden-state-learner-extension-014-summary.json)

Design source:
[`docs/research/sota-autonomous-digital-twin-evaluation-design.md`](../../docs/research/sota-autonomous-digital-twin-evaluation-design.md)
sections 3.2, 3.3, 3.6, and 4.

## Identity

| Field | Value |
| --- | --- |
| Code revision | `6a244cc4b67acd4f79dc3fe9b91862c1e171d5b8`, clean (branch `claude/sota-autonomous-digital-twin-study`, includes `origin/main` through #182) |
| Command | `uv run python scripts/run_governed_full_autonomy_v2_1_hidden_state_learner_014.py --simulate` |
| System under test | The real `StudentTutoringService` and `GovernedAutonomyService` through `StudentProductAutonomyAdapterV1`, deterministic engine, multi-concept release with six approved concepts and one chunk each |
| Learner | `TextRealisingLearnerV1` over the hidden-state simulator; 6 personas x 2 families x 3 held-out seeds (2000-2002); 30 virtual days; restart on day 15; misconception statement on day 3; question every 7 days |
| Conditions | `t0-grounded-control`, `t1-v1-reactive-control`, `t1-v2-reactive`, `t1-v2-autonomous`; 36 cases each, 144 total |
| Eligibility fixture | consent on; quiet hours 23:00-02:00 UTC; 3 messages per 7 days; 24 h same-concept cooldown |
| Provider calls | 0; no network; USD 0 |
| Elapsed | 103 s |
| Bootstrap | 1,000 paired resamples by (family, persona, seed) |
| Outputs (ignored) | `reports/generated/governed-full-autonomy-v2-1-hidden-state-learner-extension-014/` with `summary.json` sha256 `21cf3f7c0be2c6b89d980438f59fbfa5997ba6400ec43c94429c479cdd9f8c45`, `scores.jsonl` `931bd3531a7eb8e565f5c519bbb9d580c1637affca45315e493d438baefb735c`, `truth.jsonl` `543f086a3504ad05736e01cdd4b4ac416bcc86c0300e23433061e6df2aca7c37`, `responses.jsonl` `2abae071568093a16b71ef24b223d5aeaf53f8e6b06e2da6feb646950f93136d` |

## Aggregate

| Condition | n | Attribution accuracy | Assessment agreement | Attempts recognised | MSE vs hidden | AUROC next | Msgs / 30 d | Wasted rate | Follow-up | Final hidden mastery | Timing violations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| t0-grounded-control | 36 | n/a | n/a | 0.000 | 0.082 | n/a | 0.0 | n/a | n/a | 0.318 | 0 |
| t1-v1-reactive-control | 36 | n/a | n/a | 0.000 | 0.082 | n/a | 0.0 | n/a | n/a | 0.318 | 0 |
| t1-v2-reactive | 36 | 1.000 | 0.590 | 1.000 | 0.057 | 0.382 | 0.0 | n/a | n/a | 0.318 | 0 |
| t1-v2-autonomous | 36 | 1.000 | 0.566 | 1.000 | 0.067 | 0.377 | 11.1 | 0.387 | 0.412 | 0.360 | 0 |

Reading the columns. T0 and T1-v1 have no v2 learner plane, so they record no
observations; their MSE is the constant-0.5 baseline against hidden mastery.
Attribution accuracy is the share of attempt turns whose first product concept
equals the hidden concept. Assessment agreement counts the product outcome
`correct` as agreeing with a hidden-correct attempt. Wasted rate is the share
of delivered proactive messages sent when hidden mastery was at or above 0.85
or the learner was not receptive. Follow-up is the share of delivered messages
that produced an assessed attempt. Timing violations are computed from
delivered timestamps against the fixture's quiet hours, seven-day ceiling, and
cooldown.

Per family (bkt-like / logistic-like): MSE vs hidden t1-v2-reactive 0.056 /
0.058, t1-v2-autonomous 0.062 / 0.071, controls 0.102 / 0.063; wasted rate
t1-v2-autonomous 0.418 / 0.356; follow-up 0.370 / 0.454; final mastery
t1-v2-autonomous 0.258 / 0.462 versus controls 0.237 / 0.398.

Delivered autonomous actions across the 36 autonomous cases: 398
`send-in-app-check-in` and 12 `ask-diagnostic-question`; 1,828 opportunities
resolved to suppressed `no-action`. Every case restarted once on day 15 with
consistent durable identity.

## Paired contrasts (candidate minus control, 36 pairs, 95% bootstrap interval)

| Contrast | MSE vs hidden | Final hidden mastery | Messages |
| --- | --- | --- | --- |
| t1-v2-autonomous vs t0-grounded-control | -0.016 [-0.032, 0.001] | +0.042 [0.023, 0.066] | +11.1 |
| t1-v2-autonomous vs t1-v1-reactive-control | -0.016 [-0.033, 0.002] | +0.042 [0.021, 0.065] | +11.1 |
| t1-v2-reactive vs t1-v1-reactive-control | -0.026 [-0.040, -0.011] | 0.000 | 0 |
| t1-v2-autonomous vs t1-v2-reactive | +0.010 [0.005, 0.016] | +0.042 [0.021, 0.065] | +11.1 |

## Findings

1. Perception attributes correctly but never grades correct. Across both v2
   conditions, all 566 hidden-correct attempts were graded `partial` and all
   719 hidden-incorrect attempts were graded `incorrect`; no attempt was ever
   graded `correct`. Cause (code): `_attribute_concepts` returns up to three
   concepts for any shared token, and `_assess_attempt` scores the attempt
   against the union of those concepts' vocabularies, so a perfect restatement
   of one concept reaches roughly one third overlap. Consequence: the product's
   `correct_evidence_count` stays zero, so goal completion rules that require
   correct evidence cannot fire, and the count-derived mastery proxy is capped
   below the mastery band. Classification: product perception defect, not a
   harness defect (the unit test in `tests/digital_twin/test_hidden_state_learner_extension.py`
   shows the same text grades `correct` when scored against its single
   concept).
2. Observations carry wall-clock time. `LearnerObservationV2.observed_at` uses
   the process clock rather than the injected virtual clock, so all
   observations in a 30-day virtual run share one real second. The harness
   joins observations to events by event id instead; the defect remains a
   product replayability issue.
3. Calibration and next-outcome prediction. The v2 belief tracks hidden mastery
   better than the constant baseline (MSE 0.057-0.067 versus 0.082), but the
   count-derived estimate predicts the next assessed outcome below chance
   (AUROC 0.38), consistent with the network-free result in
   `successor-learner-timing-simulation-001` that count-based belief lags
   discrete mastery changes.
4. Proactive behaviour. The autonomous condition delivered about eleven
   messages per learner in thirty days with zero quiet-hour, frequency, or
   cooldown violations; 39% of deliveries were wasted by hidden truth and 41%
   produced an attempt; final hidden mastery rose by 0.042 over the reactive
   and control conditions, with the interval above zero. Under the same
   simulator, the network-free value-based policy of run 001 reached a wasted
   rate of about 0.30 and a follow-up fraction of about 0.45 with fewer
   messages; that comparison is indicative only because the two harnesses
   differ in fixture and eligibility details.
5. All hard gates pass: zero timing violations, zero provider calls, one
   consistent restart per case, response payloads identical in shape to 010.

## Limitations

- Deterministic engine only; the provider-backed arm has not run and would
  need a bounded pilot authorization for this program id.
- Simulated learners with the author's transition, receptivity, and text
  realisation assumptions; nothing about real students, usability, or learning.
- Three seeds per persona and family (36 pairs per contrast) is small; the
  intervals reflect that.
- The attempt-rendering rule is fixed and lexical by construction; a learner
  who paraphrases would be graded differently by the product.

## Decision

Go Deeper. Keep the extension as the learner-state, perception, and proactive
dimension of the evaluation framework alongside 010. File the two product
findings (perception grading with multi-concept attribution; wall-clock
observation timestamps) as issues before any successor work relies on the v2
belief plane. Run the provider-backed arm only after an authorization entry
and only with the same cases, seeds, and gates.
