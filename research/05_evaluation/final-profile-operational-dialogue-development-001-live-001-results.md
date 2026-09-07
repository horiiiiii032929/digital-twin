# Operational dialogue live pilot 001

## Decision

Refine pedagogical progression before treating this as effective tutoring.
The actual provider and persistence paths completed: 18/18 external calls
succeeded, both matched histories completed three virtual days and one restart,
and all recorded source hashes were unchanged at completion. Reported cost was
$0.0077112. This is a development operating test, not release qualification.

## Design and observations

The [plan](../04_experiments/2026-09-06-operational-dialogue-development-plan.md)
predeclared two Socratic fast-learner histories in reactive and autonomous modes,
seed 6209, with at most 80 external calls. The actual Luna provider received
fresh synthetic protocol sources and approved synthetic teaching profiles.
Virtual elapsed time, attendance, attempts, and receptivity were simulated;
question generation, message persistence, scheduled processing, and restart
used the actual application services. Fixture setup does not prove ingestion.

Twelve delivered tutor turns contained ten elicitation questions and two
clarifications. Six synthetic attempts occurred only after an actual tutor
question. None was counted as learning gain. Correct attempts still received
generic further elicitation or clarification, so the pilot exposes weak
pedagogical progression despite valid provider responses. There were no
proactive deliveries in these short fast-learner histories; proactive content
and intervention utility are untested here.

## Provenance and limits

The [machine record](records/final-profile-operational-dialogue-development-001-live-001.json)
contains exact source/configuration hashes, revision and dirty state, metrics,
per-call artifact hashes, and the review. Generated full dialogue and model
ledgers are in `reports/generated/final-profile-operational-dialogue-development-001-live-001`.
The sample is a contract pilot, too small for statistical quality estimates;
no private course data, real students, or held-out evaluation set were used.
The later neutral no-evidence wording change was not part of this run.

## Reproduction

With the configured provider credential loaded privately:

```bash
uv run python -m scripts.run_operational_dialogue_development --pilot-live --output-dir reports/generated/operational-live-fresh
```

Use a new directory. Retain the 80-call cap and inspect the full dialogue, not
only the successful HTTP/model-schema counts.
