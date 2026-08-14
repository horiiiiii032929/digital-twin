# Professor-fidelity anchor v4 P3 plan

Date frozen: 2026-08-14

Status: prospectively frozen after V4 Pro/P3 development and semantic review

## Trigger and decision boundary

The original `anchor-001` attempt is invalid and rerun-prohibited because the
selected V4 Flash fingerprint drifted on its first response. V4 Pro/P3 then
passed 48/48 public-synthetic deterministic checks and a sensitivity-gated
48/48 same-family semantic review. Those results permit an anchor-only
candidate, not component selection.

This plan creates `professor-fidelity-v2-anchor-002`. It may run while the
41-case independent-human authoring audit is pending solely to prepare judge
calibration. It cannot approve the v1.2.3 authoring draft, create a seal, run
development or held-out, select P3, or substitute model agreement for human
review.

## Frozen bindings

- Dataset: unchanged separately sealed 12-case anchor and its frozen C0-C3
  condition set.
- Generator: official `deepseek-v4-pro`, non-thinking JSON, temperature 0,
  1,200 output tokens, 60-second timeout, no retry.
- Generator fingerprint:
  `a307abda487cd1b463329ccb945ce396`.
- Prompt: P3/v4 through
  `professor-fidelity-integration-prompt-v3-p3`.
- Candidate profile:
  `professor-fidelity-anchor-v4-p3-candidate` with raw qualification hashes.
- Retrieval/chunker: unchanged selected M2 Qwen3 hybrid and page-bounded
  chunker; C1/C2 oracle and C3 retrieval assignments remain frozen.
- Cost stop: USD 1 for 48 outputs; provider identity and usage required on
  every call.
- Output: new ignored `anchor-002` directory; `anchor-001` is never reused.

## Ordered anchor work

1. Execute 12 cases × C0-C3 once as `anchor-002`.
2. Run all-case DeepSeek V4 Pro high-thinking judgments. Primary attempt 001
   stopped invalid after 5/12 checkpointed cases and must not be rerun. Follow
   the separately frozen judge-v4 recovery plan and public probe before primary
   attempt 002.
3. Run the swapped-order DeepSeek judgments.
4. Run local Qwen sensitivity judgments and treat them as diagnostic because
   Qwen failed the generator citation-completeness stress gate.
5. Prepare the blinded output-reference packet and compute prehuman
   calibration only.
6. Stop for the bounded human reference. Do not fill it with Codex/model
   judgments and do not proceed to professor-fidelity development.

## Outcome update

Anchor generation completed 48/48. Primary DeepSeek attempt 002 completed but
failed the 90% repeat-consistency gate at 68.75% and produced one all-pass
pedagogy judgment on a deterministic hard-gate failure. Swapped DeepSeek
attempt 001 stopped invalid after 5/12 cases; local-Qwen attempt 001 stopped
invalid after 2/12. Both are rerun-prohibited. The blinded 48-response packet
was prepared with zero labels filled. Automated calibration is ineligible, so
the human reference and separate authoring audit may be deferred but cannot be
treated as passed.

Any generator model/fingerprint drift, missing cost, incomplete attempt,
private-boundary mismatch, judge sensitivity failure, or unresolved reference
keeps the anchor diagnostic and blocks calibration claims.
