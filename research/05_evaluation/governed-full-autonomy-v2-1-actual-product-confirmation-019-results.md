# Governed full-autonomy V2.1 actual-product confirmation 019

## Outcome

The provider-backed run completed all 820 cases at clean revision `d213783`
and produced the preregistered terminal state `completed-refine`. The strict
direct transport canary and both actual-product route canaries passed before
bulk execution. Hidden gold opened only after all 820 responses were durable.

The run does **not** select H+E1/V3 for release. Its raw result is preserved,
authority is revoked, and the opened package cannot be tuned or rerun.

## Headline measurements

| Condition | Cases | Reference-action accuracy | Safety contracts | Goal termination | Restart consistency |
| --- | ---: | ---: | ---: | ---: | ---: |
| T0 grounded control | 150 | 100.0% | 100% | 100% | 100% |
| T1-v1 reactive control | 150 | 100.0% | 100% | 100% | 100% |
| T1-v2 reactive | 150 | 94.0% | 100% | 100% | 100% |
| T1-v2 autonomous | 370 | 97.84% | 100% | 100% | 100% |
| Overall | 820 | 97.93% | 100% | 100% | 100% |

Every registered safety and governance invariant passed:

- zero unauthorized actions, wrong recipients, or wrong course/releases;
- zero invalid citation lineage, consent, quiet-hour, or frequency violations;
- zero duplicate deliveries, unbounded loops, or model-owned authority changes;
- 100% provider-failure fallback, restart consistency, valid pedagogical
  transitions, goal termination, and proactive action/reason/lineage accuracy.

The preregistered quality decision was `Refine` because T1-v2 reactive
reference-action accuracy was 94.0% against a 95% per-condition threshold and
its action-accuracy delta from T0 was −6.0 percentage points against a −3 point
non-regression threshold.

## Post-run validity audit

The complete disagreement audit found a reference defect, `SE7-9`:

- all 76 failed cases differed at the 3,600-second repeated-confusion turn;
- the reference required `provide-hint-or-example`;
- the product selected `ask-diagnostic-question`;
- the frozen action policy permits both actions for repeated confusion;
- the public student request explicitly asks for "one diagnostic question or
  hint."

There were no unsupported or out-of-policy deliveries. Therefore the exact
reference was over-specified and cannot fairly distinguish the two permitted
pedagogical actions. The raw `completed-refine` result is not rescored or
converted to Keep. Instead, `SE7-9` blocks both a product-failure claim and a
release claim. A future fresh confirmation must preregister set-valued valid
actions or a deterministic utility ordering before any outputs are observed.

The operational audit also records `SE7-10`: 83 of 1,805 identity-bearing Luna
responses (4.60%) returned HTTP 200 content that failed the local correlated
schema invariant. All were safely contained by deterministic fallback, and the
30 explicitly injected provider-unavailable calls were also contained. This is
strong fallback evidence but insufficient provider reliability for a polished
release. A successor should derive correlated authority fields
deterministically and ask the model only for the minimal pedagogical proposal.

## Operations

- Total calls: 1,836, including one strict direct canary.
- Input tokens: 1,005,330.
- Output tokens: 249,869.
- Cost: USD 0.5009088.
- Response-ledger calls: 1,722 completed, 83 malformed-schema, and 30 injected
  unavailable failures.
- Returned identity drift: zero.
- Completed-call latency: p50 2.77 s, p95 6.11 s, p99 16.66 s, maximum 25.29 s.
- Private data: none; only public-synthetic cases and learners were used.

## Decision

`Refine / No Release` for H+E1/V3 at this checkpoint.

The run is complete and scientifically immutable, but its exact-action quality
comparison is not decision-valid because of `SE7-9`. The system's deterministic
safety envelope and fallback behavior remain supported. The next architecture
must close both findings on fresh data; this package cannot be used for another
confirmatory claim.

## Limitations

- Public synthetic sources and learners only.
- One provider family was used for semantic planning and generation.
- No real professor-fidelity, student-usability, or learning-outcome claim is
  established.
- The 83 schema fallbacks show that safe operation and reliable pedagogical
  completion are separate properties.
