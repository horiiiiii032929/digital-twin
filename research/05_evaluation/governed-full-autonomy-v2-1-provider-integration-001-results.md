# Evaluation result: governed-full-autonomy-v2-1-provider-integration-001

## Run identity

- Date: 2026-08-31
- Clean execution revision: `7e565c401e541511676e51d2283da2e9f9c0f4c7`
- Candidate: governed full-autonomy V2.1 release candidate 001
- Planner: exact `gpt-5.6-terra`
- Generator: exact `gpt-5.4-mini-2026-03-17`
- Data: public synthetic cache-coherence release and synthetic users only
- Executed instrument SHA-256: `9a54a4dd6c647085168a956b86352b98cc40534421aca3075bb0c02169a35604`
- Ignored generated result: `reports/generated/governed-full-autonomy-v2-1-provider-integration-001/result.json`
- Generated result SHA-256: `3cfa5b4974b802563092d87dfe77e3207dd84b6645a3889a48b026dee8bd0f3f`

## Decision question

Can the frozen V2.1 candidate cross its real planner and grounded-generator
boundaries for reactive and proactive tutoring while deterministic code retains
identity, policy, evidence, state, delivery, and loop authority?

## Method

The actual product services processed one simple factual turn through the fast
path, one misconception turn through the semantic planner, and one due
spaced-review opportunity through the proactive graph. The run then attempted
the same due job from a second worker and reopened the SQLite state to check
duplicate suppression and restart consistency. It used direct OpenAI Responses
API calls with `store: false`, exact returned-model checks, zero retries, a
12-call ceiling, and a USD 1 stop.

## Result

The clean execution completed as `completed-go-deeper`:

- two reactive turns were grounded and persisted with atomic claims;
- the simple fast path and the one-call complex planner path both executed;
- one proactive job reached a terminal `delivered` outcome and produced one
  private in-app message;
- the duplicate worker produced no second job or delivery;
- state, traces, inbox, and actions matched after restart;
- exact planner and generator identities were returned;
- all 12 aggregate integration gates passed; and
- five calls reported USD 0.0017055 total cost, below the USD 1 ceiling.

The one-time authorization was revoked after completion.

## Decision

Outcome: **Go Deeper**. Real provider integration is demonstrated, but V2.1 is
not selected for release. T1-v1 remains the current control and T0 remains the
rollback until #157 completes representative full-autonomy evaluation.

## Limitations

This was a deliberately small public-synthetic integration checkpoint: two
reactive turns, one proactive opportunity, one topic, and no real professor or
student. It does not establish long-horizon pedagogical quality, professor
fidelity, usability, or learning improvement.

The aggregate runner retained call counts and reported cost but did not surface
input/output token totals or per-call latency in its durable result. The run is
therefore valid as provider-boundary evidence, not complete operational or
academic evidence. #157 must collect those measures prospectively.
