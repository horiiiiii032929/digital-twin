# Output-cap progression comparison 001

## Decision

Refine the request/validator contract before selecting a larger output cap.
All48 paired trajectories and192 actual student turns completed with unchanged
source hashes. The1500-token arm removed the four observed truncations, but
exposed seven local count-limit failures. No overall teaching-quality upgrade
or default/profile change is justified by these results alone.

| Measure |500 tokens|1500 tokens|
|---|---:|---:|
|Actual model calls|114|114|
|Completed calls|109|107|
|Output-cap failures|4|0|
|Local schema count failures|1|7|
|Delivered safe graph failures|12/96|11/96|
|Answers|28|28|
|Questions|37|39|
|No-evidence|19|18|
|Reported cost (USD)|0.0637272|0.0661726|

The strict provider schema removes array-count constraints. The v2 prompt did
not communicate the four-aspect/two-span bounds retained by the local parser.
This is a confirmed integration defect, not evidence that more tokens improve
or worsen factual knowledge. Seven additional control and four additional
candidate delivered failures also require semantic/guard review; schema-valid
output alone is not a tutoring success.

## Design and provenance

The [plan](../04_experiments/2026-09-06-output-cap-progression-development-plan.md)
predeclared eight fresh synthetic dialogue situations, three order/repetition
seeds and two matched cap arms. All24 initial provider-message pairs were
identical. Later actual tutor messages entered history, so later requests could
diverge. Seeds label order/repetition, not provider randomness. The four fictional
cards are not four independently sampled real courses.192 turns are correlated.

The [record](records/output-cap-progression-development-001-live-001.json)
retains code revision/dirty state, exact source/profile/cap configuration,
per-trajectory outcomes, arm token/cost/latency metrics and artifact hashes.
Raw dialogues, provider requests/results and the verified source snapshot are
under `reports/generated/output-cap-progression-development-001-live-001`.
Only synthetic authorized data were used. Concurrent advisory-provider work
means latency is descriptive, not an isolated causal performance comparison.

## Reproduction

With the authorized credential loaded privately and a new output directory:

```bash
uv run python -m scripts.run_output_cap_progression_development --live --output-dir reports/generated/output-cap-paired-fresh
```

The unchanged500-token control and1500-token candidate each retain250-call/$5
reservation limits. No held-out confirmation, learning effect, professor
fidelity, or release promotion is claimed.
