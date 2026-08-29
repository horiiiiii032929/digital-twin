# Evaluation result: autonomous-tutoring-r1-confirmation-002

## Run identity

- Component: local R1 student conversation orchestration
- Date: 2026-08-29
- Clean execution revision: `fafe1eaf389cb5afabf72ce953cf636dee86523d`
- Instrument: `autonomous-tutoring-r1-confirmation-002`
- Executed instrument SHA-256:
  `217b86c9c9c1cf4bc9751e356a83c06b2e52690e566bca301b45ba7a6a48ac60`
- Profile: `student-tutor-r1-local-candidate@v1`
- Profile SHA-256:
  `1b3257e80e2bcb6f49871a537d022a6c65f0bf43fe1a37a535cf5b6eb8d34eec`
- Conditions: deterministic T0 grounded assistant and deterministic T1 bounded
  LangGraph tutor
- Boundary: provider-free, network-free, synthetic, no private or held-out data
- Machine record:
  `research/05_evaluation/records/autonomous-tutoring-r1-confirmation-002.json`

## Decision question

Does the bounded T1 graph preserve the local R1 grounding, citation, policy,
persistence, and recovery boundaries while adding valid restart-safe
pedagogical state transitions?

## Method

The run sent 200 student turns through each condition across 50 isolated
four-turn trajectories. The ten equally represented scenario families covered
direct questions, partial attempts, repeated confusion, misconceptions,
ambiguity, no evidence, academic integrity, cross-course requests, forced
generation failure, and process restart.

Both conditions used the same synthetic releases, deterministic generator,
structured lexical evidence gate, policy, and SQLite repository. T1 added the
bounded LangGraph path and privacy-minimized learner state. Every trajectory
also repeated its final request ID to verify idempotency. No model or provider
was called.

## Result

The execution completed as `completed-keep`:

- T0 and T1 grounded success: 100% each; delta 0 percentage points;
- T1 transition validity: 100%;
- action, citation, claim-support, state, persistence, duplicate-protection,
  and restart checks: 100%;
- forced-failure safe fallback: 100%;
- zero unsupported releases, permission violations, invalid citations,
  duplicate persisted turns, unbounded loops, or authoritative model
  mutations;
- mean/maximum local turn latency: 1.973/10.893 ms across both conditions; and
- provider calls, input tokens, output tokens, and cost: zero.

No failure trajectory was recorded. The one-time network-free authorization
was revoked after the result was persisted.

## Decision

- Outcome: **Keep** T1 for the production-like local R1.
- Bind the exact profile and result hashes to staging validation.
- Keep T0 available through one configuration setting as immediate rollback.
- This decision does not select an LLM product model and does not repair the
  failed academic model cascade.

## Limitations

This is a synthetic local release qualification. The 50 source namespaces are
isolated fixtures rather than independently authored course sources. The result
does not establish professor fidelity, learning outcomes, external usability,
natural LLM answer quality, hosted reliability, or the final 10,000-case
academic product result.
