# V2 finite dialogue progression live pilot 001

## Decision

Refine pedagogical quality while retaining the v2 candidate for development.
All 24 external calls returned schema-valid output, with reported cost
$0.0113548. Four histories completed four turns each and one restart before the
new-concept turn; frozen source hashes remained unchanged. Schema success is
not equivalent to successful teaching: two delivered turns failed closed.

## Findings

The Socratic incorrect-attempt history followed a useful sequence: diagnostic
question, one partial cited hint, relevant explanation, then a fresh diagnostic
question for a new concept. The correct Socratic attempt received an explanation.
Explanatory initial and new-concept turns gave explanations, but its correct
attempt still received a generic question followed by a hint. This remains a
weakness in pedagogical continuation.

Two further-help proposals labelled the entire requested answer as a hint.
The new conservative span-coverage check rejected both (Socratic correct and
never-direct-answer histories), resulting in safe graph failures. This prevents
those literal full-answer hints; it does not guarantee partial disclosure when
model requirement coverage is wrong. Eight delivered turns were questions, six
were answers (including two hints), and two were safe graph failures.

## Design and provenance

The [plan](../04_experiments/2026-09-06-operational-dialogue-development-plan.md)
predeclared four synthetic histories, sixteen fixed stimuli, a 100-call/$1
reservation limit, and independent content review. No student understanding was
simulated or measured from successful calls. The [machine record](records/final-profile-operational-dialogue-development-001-progression-live-001.json)
contains exact profile/source/code hashes, dirty revision, costs, raw artifact
hashes and review notes. Full turns and provider ledgers remain under
`reports/generated/final-profile-operational-dialogue-development-001-progression-live-001`.

The preserved v1 pilot is a descriptive baseline; these are not matched random
trials or a learning-effect comparison. Sources and profiles are synthetic,
with no private course/student data. This is neither deployed qualification nor
real-professor fidelity. Independent G7 content review is pending.

## Reproduction

With the authorized provider credential loaded privately and a new directory:

```bash
uv run python -m scripts.run_operational_dialogue_development --progression-live --output-dir reports/generated/progression-live-fresh
```
