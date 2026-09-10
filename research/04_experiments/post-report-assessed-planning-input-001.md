# Assessed planning input development 001

Status: prospective development plan, 2026-09-08. No promotion authorized by
this plan; preserve `default_planning_state_card` as the control.

## Decision and prediction

Can a planning-input adapter use saved, concept-scoped assessments without
interpreting delivery attempts as evidence of understanding? Predict that
changing only delivery count leaves the candidate estimate unchanged, while
correct and incorrect assessments change it in opposite directions.

Control: existing attempt-derived planning card. Candidate: explicit adapter
feeding the existing `LearnerEstimator` interface, initially the Laplace
evidence-count estimator. BKT and PFA remain comparison options, not selected
product defaults. Their probabilities are uncalibrated model estimates; they
must not be presented as measured mastery.

## Input and failure contract

The caller binds the authorized learner key, course, release and concept.
Reject mixed-learner/course/release inputs and conflicting duplicate IDs.
Deduplicate identical observations and process in chronological order.
Use only explicit assessment concept bindings, supported correct/incorrect
outcomes, nonempty evidence keys and timezone-aware timestamps not in the
future. Leave partial, unassessed and legacy ambiguous concept bindings out
of binary estimation, recording their exclusion reasons. Do not silently turn
partial correctness into either a success or failure.

An unknown concept or no usable observations returns the estimator prior,
zero assessed count and no last-observation interval. Calculate the recent
incorrect streak from eligible observations, never from the opportunity label.
Keep delivery attempts remaining as an operational limit separate from the
estimate. Do not equate the fraction of used attempts with achieved progress.

## Evaluation

Versioned synthetic regression fixtures cover correct/incorrect histories,
partial and missing assessments, other-concept attribution, duplicate and
conflicting observations, future/naive timestamps, cross-scope records, and
delivery-count changes with constant observations. Zero privacy/scope leakage,
zero duplicate updates and all stated invariants are hard gates.

Before product selection, replay the same newly collected assessed inputs
through the count, BKT and PFA implementations and report next-observation
Brier score/calibration by history, sparse-history behavior, latency and
memory. An adapter contract test is not this prediction-quality comparison.
No provider call or human learning claim is required for the adapter stage.
Keep the product control until input quality and decision-level comparisons
justify an explicit experimental profile selection.
