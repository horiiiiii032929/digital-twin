# Operational dialogue contract pilot 001

## Decision

Keep the instrumentation for a bounded live development pilot. Two matched
Socratic fast-learner histories completed three virtual days and one restart
each. All six transport attempts deliberately returned malformed-response
errors. Actual provider calls, tokens, and cost were zero.

## Evidence and scope

The [prospective plan](../04_experiments/2026-09-06-operational-dialogue-development-plan.md)
predeclared this pilot. The [machine record](records/final-profile-operational-dialogue-development-001-contract-001.json)
contains revision, dirty state, exact configuration and source hashes, per-history
metrics, and artifact hashes. Generated evidence is in `reports/generated/final-profile-operational-dialogue-development-001-contract-001`.

Each history recorded three student turns; no elicitation or outreach occurred
under this deliberately failing transport. Thus the run demonstrates failure
persistence and restart, while the separate fake-success regression exercises
bounded replies to actual question actions. This is not model quality,
teaching fidelity, learning gain, ingestion proof, or intervention utility.

## Reproduction

```bash
uv run python -m scripts.run_operational_dialogue_development --pilot-contract --output-dir reports/generated/operational-contract-fresh
```

The output directory must be new. Fresh synthetic sources and seeded students
contain no private instructor or student data. No statistical quality estimate
is justified by this two-history contract sample.
