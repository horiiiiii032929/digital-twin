# Generator qualification v2 Qwen review attempt 001 invalid results

Result ID: `generator-qualification-v2-qwen-review-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid review; completed 48/48 local judgments but demonstrated no
defect sensitivity

Decision: Preserve but do not use the 48 approvals. Repair the review prompt
prospectively and require public sensitivity probes before another all-case
review.

## Binding and boundary

- Source generator run:
  `generator-qualification-v2-v4-pro-development-001`.
- Reviewer: local `qwen3:4b`, digest
  `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
- Prompt version: `generator-qualification-v2-qwen-review-v1`.
- Clean review revision:
  `7bac41d1399418bfd3aa7fe4b4414a9b8505d39d`.
- Ignored raw review SHA-256:
  `bbd70c751f4381081ab3723c9218c34789e0561a5eec9bb1d088d9dc8fa71506`.
- Gemma calls: zero.
- External calls: zero.
- Private text and held-out access: zero.

## Observed result

Qwen returned 48 approvals, zero revisions, and zero uncertainty. The runner
still escalated the two deterministic failures. Both failed ambiguity cases
were marked action-correct and clarification-correct, including
`gqv1-dev-045`, which only listed two meanings and did not ask the student which
meaning they intended.

Every case used the exact same reason copied from the prompt's example:
`All applicable checks pass using only the supplied evidence.` This establishes
template imitation, not independent semantic review. The attempt therefore
cannot clear any case or support candidate advancement.

## Failure classification and repair

- Primary cause: judge-prompt design; the output example supplied a complete
  approve object and reusable reason.
- Secondary cause: no pre-run sensitivity gate demonstrated that the local
  model could reject obvious action, support, citation, or integrity defects.
- Candidate implication: unchanged. The V4 Pro generator remains Refine
  because its 46/48 deterministic result still contains two failures.

The prospective v2 reviewer removes the approval example, rejects generic
template reasons, and must correctly classify five public synthetic stress
probes before seeing any of the 48 candidate cases. It remains local Qwen only;
Gemma is prohibited.
