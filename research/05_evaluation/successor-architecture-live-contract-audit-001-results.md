# Successor architecture live-contract audit 001

Date: 2026-09-02  
Decision: **Keep the corrected transport / no architecture selection**

## Finding and resolution

The A/B/C OpenAI client exposed the correct strict schemas for hierarchical
planning and reject-only verification, but its post-response dispatcher still
validated both payloads as the legacy tutor-answer contract. A valid live
response would therefore have been classified as malformed and converted into
a safe `no_action`, biasing the prospective comparison.

Revision `6bafa48ee2b404dfd431e946d104c9e7c3c558c3` adds explicit local validation
for `HierarchicalPlanningProposalV1` and `PlannerVerificationV1`. Two
transport-level regression tests prove that valid responses survive parsing,
identity verification, usage accounting, and contract validation.

## Verification

- 25 focused OpenAI/planner/comparison tests passed.
- Ruff and `git diff --check` passed.
- Provider calls, tokens, and cost: zero.

This is software-contract evidence only. It selects no architecture or engine.
