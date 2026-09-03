# Successor architecture development fold 001 — invalid attempt 001

Attempt 001 is preserved as `invalid-execution`; it is not an architecture-quality result.

- 17 direct OpenAI calls completed with no retry: two canaries and 15 planner batches.
- 16,564 input and 13,071 output tokens were reported at USD 0.018998.
- Zero architecture cells were persisted and hidden gold was never opened.
- The failure was not caused by connectivity or model identity drift.

The strict provider schema allowed a bounded episode to repeat an action, while `HierarchicalPlanningProposalV1` imposed an additional local-only uniqueness rule. A schema-valid provider response therefore failed local parsing. This is finding `SA7`, a harness contract defect.

The only permitted correction removes that unsupported uniqueness invariant while retaining the three-step bound and deterministic action-envelope validation. The same 150 cases, hidden gold, prompts, model role, metrics, gates, and USD 2 ceiling remain unchanged. Attempt 001 cannot be resumed and its completed calls cannot be imported into the fresh corrective attempt.
