# Evaluation instrument freeze v1

Date: 2026-07-23

Status: researcher-selected instrument design; no model run or sealed-output
inspection authorized by this document

GitHub issue: #11

## Decision question

Can the no-participant evaluation produce reproducible, auditable evidence
without allowing the tutor, simulator, or LLM judge to define its own success?

## Decision

Freeze four separately versioned contracts:

1. `llm-judge-v1` receives blinded responses and case-specific pedagogical
   criteria, then emits only structured subjective judgments.
2. `simulated-student-v1` receives a frozen state card plus an externally
   classified tutor event, follows exactly one declared transition, and emits
   only the next student-role turn.
3. `evaluation-run-v1` records complete run provenance and per-case or
   per-trajectory evidence without replacing bulky private output with an
   aggregate.
4. `analysis-v1` defines denominators, metrics, uncertainty, contrasts,
   calibration gates, decision order, and stop rules before sealed output.

Deterministic and researcher-authored labels remain authoritative for course
truth, claim support, citations, expected actions, privacy, permissions,
assessed-work boundaries, operational behavior, tokens, latency, and cost. The
LLM judge cannot alter these fields. The simulated student cannot read them.

## Why no interview is required

The repository already fixes the choices that would materially change the
design:

- no human participants or real-student data;
- all course-specific processing remains local;
- DeepSeek is synthetic-only under the cumulative USD 10 cap;
- eight scenario types and C0-C3 / D0-D2-D3 conditions;
- deterministic hard gates before subjective judgment;
- `fail / partial / pass` pedagogical labels;
- a frozen state-card simulator used as a stress actor, not a learner model;
- researcher-owned anchors with optional professor expert critique; and
- no usability, learning, satisfaction, engagement, or adoption claim.

An interview is needed later only if one of those boundaries changes.

## Artifact set

The frozen contracts live under
`research/05_evaluation/instruments/`:

| Artifact | Purpose |
| --- | --- |
| `llm_judge_v1.prompt.md` | Exact system and user-message template |
| `llm_judge_input_v1.schema.json` | Blinded single or pairwise task input |
| `llm_judge_output_v1.schema.json` | Strict structured judgment |
| `simulated_student_v1.prompt.md` | Exact transition-following prompt |
| `simulated_student_state_v1.schema.json` | State, event, transition, and checkpoint contract |
| `simulated_student_turn_v1.schema.json` | Strict next-turn or invalid-transition output |
| `evaluation_run_v1.schema.json` | Run provenance and per-item evidence |
| `analysis_v1.json` | Frozen metrics, intervals, contrasts, gates, and stop rules |
| `instrument_freeze_v1.json` | IDs, versions, status, and SHA-256 inventory |

Synthetic examples contain no IT5002 text and are committed beside their
schemas. Private state cards, tutor outputs, judge inputs, and per-case run
records remain ignored.

## LLM judge design

### Eligible work

The judge may evaluate only:

- student-state recognition;
- mistake localization;
- guidance and scaffolding;
- actionability;
- answer-revelation control;
- professor-policy alignment;
- clarity and coherence;
- tone and respect.

Each dimension is present only when the case marked it applicable before
generation. The input provides the student state, a policy excerpt, a
case-specific expectation, and blinded response text. It does not provide
condition IDs, model names, provider names, aggregate results, hard-gate
outcomes, or gold course claims.

### Prohibited work

The judge must not decide:

- whether a course claim is true or supported;
- whether a citation resolves;
- whether evidence is complete;
- whether an assessed-work, permission, privacy, or operational hard gate
  passed;
- whether the simulator behaved validly; or
- whether a candidate should be selected.

Ineligible or malformed tutor outputs fail or become evaluator errors before
subjective judging. The judge has no `cannot_judge` escape label: an
unparseable judgment is an evaluator failure, not a tutor score.

### Labels

- `pass`: fully satisfies the case-specific criterion with no material defect;
- `partial`: helpful and relevant but has one named material omission or defect;
- `fail`: misses, contradicts, or materially violates the criterion.

Every label requires a short exact response span and a rubric-grounded reason.
Pairwise judgments use `A`, `B`, or `tie` independently for every applicable
dimension. No overall winner or composite score is requested.

### Decoding contract

Every run records the exact judge provider, model, immutable revision when
available, prompt hash, schema hash, temperature, top-p, maximum output tokens,
seed or `null`, retry count, and structured-output mode. The default instrument
configuration is temperature `0`, top-p `1`, maximum output tokens `1200`, no
sampling seed assumption, one attempt, and strict JSON Schema output.

Changing prompt text, schema, rubric meaning, or decoding defaults creates
`llm-judge-v2`. Changing only the evaluated local model is a new judge
configuration and calibration run, not a silent instrument change.

## Judge calibration

Calibration occurs before any sealed judgment:

1. Freeze the 12 anchor cases and researcher labels.
2. Blind every response and randomize pair labels with seed `5002`.
3. Score each applicable dimension on every anchor output.
4. Run each pair in both A/B and B/A order.
5. Repeat a stratified 20% using the identical configuration.
6. Run a distinct-family sensitivity judge on the full anchor.
7. Preserve every disagreement and malformed output.

Primary use is decided per dimension, not from a pooled score. A dimension is
eligible only when all of the following pass:

- linear-weighted Cohen's kappa against the researcher anchor is at least
  `0.67`;
- exact `fail / partial / pass` agreement is at least `0.80`;
- swapped-order consistency is at least `0.90`;
- identical-repeat consistency is at least `0.90`; and
- the judge produces zero false passes on anchor outputs with an applicable
  deterministic hard-gate failure.

If one dimension fails, that dimension remains diagnostic. Other dimensions
may remain eligible if they independently pass. Without professor labels, all
eligible results are named **researcher-anchor-calibrated proxy evidence**.

## Simulated student design

### Separation from evaluation

The simulator never interprets whether the tutor was correct. The orchestration
layer supplies one observable event from the frozen vocabulary, derived from
the tutor's structured action and deterministic evaluator:

- `answer`;
- `scaffold`;
- `clarify`;
- `redirect`;
- `abstain`;
- `prohibited_completion`;
- `unsupported_claim`;
- `operational_failure`; or
- `recovery`.

The state card contains at most one transition for each
`from_state_id + observed_event` pair. The simulator follows that transition
and verbalizes the declared student act under explicit content constraints. If
there is no matching transition, it emits an invalid-transition record and no
student message.

This design makes event classification auditable and prevents the simulator
from becoming a hidden judge.

### State-card requirements

Every card fixes:

- scenario, split, data boundary, initial state, and two-to-four tutor turns;
- permitted knowledge IDs, unknown knowledge IDs, misconception IDs, goal,
  assessed-work attempt status, and pressure level for every state;
- an event-triggered transition graph;
- the student act, required intent, prohibited content, maximum words, and stop
  flag for every transition;
- expected tutor actions, required pedagogical dimensions, and hard-gate focus
  for each checkpoint; and
- invalidity rules.

Knowledge and misconception IDs reference private case artifacts. The committed
schema and example contain only synthetic public content.

### Simulator validity

A trajectory is invalid when the simulator:

- emits knowledge or evidence outside the destination state's permitted IDs;
- changes misconception or assessed-work state without the declared
  transition;
- uses a transition not uniquely selected by the observed event;
- exceeds the maximum student-message length;
- emits prohibited content;
- reports the wrong state or transition ID;
- stops before a terminal transition or continues after one; or
- returns malformed output.

Invalid trajectories are counted and reported before quality aggregates. They
are excluded from the valid-trajectory completion denominator but never
deleted, regenerated, or hidden. A correction requires a new simulator version
and a registered run.

## Run-record design

One `evaluation-run-v1` file records:

- stable run ID, run type, status, timestamps, Git revision, dirty state, and
  environment;
- dataset, split, hash, corpus, permission, condition, and profile identity;
- exact tutor, retriever, verifier, judge, simulator, prompt, schema, decoding,
  and randomization configuration;
- provider-boundary and cost-cap status;
- every attempted single-turn case and trajectory;
- raw actions, responses, retrieval hits, presented passage IDs, context labels,
  atomic claim results, citations, hard gates, judgments, failures, latency,
  tokens, retries, and cost; and
- missing, invalid, and excluded records with explicit reasons.

A missing tutor output remains in the unconditional denominator and fails safe
grounded task success. An invalid simulator trajectory is not converted into a
tutor failure, but its count is always displayed beside the valid denominator.
Raw private records stay under ignored `reports/generated/`; sanitized
aggregate records and representative redacted failures are committed later.

## Frozen analysis

The machine-readable analysis file freezes:

- Wilson two-sided 95% intervals for reported proportions;
- a one-sided exact 95% upper bound for zero-observed hard failures;
- 10,000 case-level paired bootstrap replicates with seed `5002`;
- exact two-sided McNemar tests for predeclared paired binary contrasts;
- Holm correction across H1-H3 at alpha `0.05`;
- H4 as conditional and descriptive unless C4 eligibility was frozen before
  generation;
- aggregate primary decisions and descriptive scenario/topic slices;
- per-dimension judge calibration;
- raw numerators, denominators, exclusions, and invalid counts;
- fixed rounding and failure categories; and
- lexicographic hard-gate, quality, operations, relative-effect, complexity,
  and reversibility decisions.

The primary outcome definitions and project floors remain those in the main
protocol. `analysis_v1.json` removes remaining ambiguity about population,
denominator, interval, comparison direction, multiplicity, and stopping.

## Stop rules

Stop and preserve the run when:

1. private course content crosses the approved local boundary;
2. any secret, cross-course data, prohibited evidence, or assessed-work answer
   is exposed;
3. the cumulative synthetic external-provider cost would exceed USD `10`;
4. dataset, prompt, schema, code revision, or analysis hash differs from the
   run manifest;
5. sealed data was inspected before the freeze;
6. judge calibration fails for a required dimension;
7. simulator invalidity exceeds 10% of attempted final trajectories;
8. more than 5% of required outputs are missing or malformed;
9. the predeclared maximum attempts have completed; or
10. the candidate fails a hard gate or component floor and no diagnostic run
    was predeclared.

Do not rerun to obtain a favorable result. A corrected configuration receives
a new run ID and, when an instrument changes, a new instrument version.

## Validation and readiness

Run:

```bash
uv run python scripts/validate_evaluation_instruments.py
```

The validator checks every public synthetic example against its JSON Schema,
cross-file judge dimensions, simulator graph uniqueness and transitions, run
record references, analysis IDs, and every SHA-256 listed in the freeze
manifest.

The instrument is ready for #24/#43 development work when validation passes and
the Git revision is recorded. It is ready for sealed evaluation only after the
exact tutor, judge, simulator, provider, model revisions, and runtime
configuration are added to a run manifest without changing the frozen
instrument hashes.

## Professor reporting statement

> I designed the evaluator so the LLM judge cannot override factual or safety
> checks, and the simulated student cannot judge the tutor. The analysis,
> denominators, calibration gates, and stopping rules are frozen before sealed
> output. Professor review can test external validity, but the method and
> resulting limitations remain my research decision.
