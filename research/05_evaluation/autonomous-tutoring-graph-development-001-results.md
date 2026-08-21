# Evaluation result: autonomous-tutoring-graph-development-001

## Run identity

- Component: student conversation orchestration
- Date: 2026-08-22
- Clean execution revision: `51eb43a7e0fc2321ce0b17a936c58142094a2efc`
- Instrument: `autonomous-tutoring-graph-contract-v1`
- Executed instrument SHA-256:
  `64e54298b5419fa3e6d9d4a31f481201cd9fe1de73feeb5832b72d5e50cfaa33`
- Conditions: T0 grounded-assistant control and T1 bounded tutoring graph
- Data: ten synthetic trajectories and 13 identical turns per condition
- Boundary: no network, provider, paid, private, or held-out use
- Generated per-turn result:
  `reports/generated/autonomous-tutoring-graph-development-001.json`
- Generated result SHA-256:
  `beceb875c709573d318aadfa1dd8e92a5f25a7ff7005d55c7d90a7e6fe376b7d`

## Decision question

Does the bounded T1 tutoring graph select the expected pedagogical transitions
and terminate safely without weakening the T0 grounding, citation, policy,
persistence, and failure-recovery controls?

## Method

The runner sent the same synthetic student messages, release, source
permissions, evidence labels, and deterministic generator through both
conditions. T0 used the existing grounded-assistant path. T1 added the typed
learner state, deterministic tutoring-intent selection, bounded LangGraph path,
one-repair limit, and atomic state revisions.

The ten trajectories covered direct questions, repeated confusion, partial
work, a misconception, ambiguity, no evidence, academic integrity, a
cross-course request, forced malformed generation, and process restart. The
result preserves every turn's expected and observed action, T1 intent, learner
state revision, help level, citations, support decision, fallback, persisted
message count, restart marker, latency, tokens, and cost.

## Result

The execution completed as `completed-go-deeper`:

- 13/13 T0 actions and 13/13 T1 actions and intents matched the frozen contract;
- 11/11 citation-applicable turns in each condition used valid source citations;
- supported-claim, action, persistence, restart, and forced-fallback rates were
  all 100%;
- zero unauthorized, cross-course, unsupported, policy-violating, duplicate,
  unbounded, or model-owned authoritative-mutation events occurred;
- T1 learner-state revisions and help-level changes matched the expected
  trajectories, including escalation from hint to explanation after repeated
  confusion and state continuity after restart;
- T0 mean/maximum latency was 0.808/1.465 ms and T1 was 6.129/27.175 ms on this
  local deterministic harness; and
- provider calls, input tokens, output tokens, and cost were all zero.

No failures were classified. The one-time network-free execution authorization
was revoked after recording the result.

## Decision

- Outcome: **Go Deeper** to one separately frozen confirmation.
- Keep T0 as the active staging configuration and rollback.
- Do not promote T1 from a synthetic development pass.
- Do not begin another prompt-refinement sequence. A confirmation failure must
  trigger an explicit method-level decision.

## Limitations and next gate

This run establishes deterministic graph behavior, not real autonomous tutoring
quality. It uses synthetic development trajectories, deterministic turn
signals, and a deterministic generator. It does not establish model-based
learner-state interpretation, natural response quality, professor fidelity,
student learning, human usability, provider reliability, or hosted latency.

The next T1 action is one separately designed and authorized confirmation. It
must remain distinct from the professor-dependent T2 fidelity evaluation and
from the separately paused factual-QA scale track.
