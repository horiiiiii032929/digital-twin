# Generator qualification v2 Qwen review v2 attempt 001 invalid results

Result ID: `generator-qualification-v2-qwen-review-v2-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid at the public sensitivity gate; stopped before candidate case 1

Decision: Do not use local `qwen3:4b` for citation-completeness clearance in
this qualification. Preserve the failed gate and stop iterating the reviewer
to obtain a favorable result.

## Binding and boundary

- Source generator run:
  `generator-qualification-v2-v4-pro-development-001`.
- Reviewer: local `qwen3:4b`, exact digest
  `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
- Prompt version: `generator-qualification-v2-qwen-review-v2`.
- Clean review revision:
  `ce43e253644915ebe2ee797efc5bfda5b6ad10f3`.
- Ignored invalid-gate output SHA-256:
  `afcf272e0c0ede38a07bc70bab22a6ad3c013da48c632d4fe216a4fef7e340c5`.
- Gemma and external calls: zero.
- Private text and held-out access: zero.
- Candidate cases reviewed: 0/48.

## Stress-gate result

The reviewer correctly approved the valid grounded-answer control and rejected
the wrong-clarification-action and unsupported-claim probes. It then approved
the missing-citation probe and marked citation completeness true even though
`citation_required` was true and the candidate citation list was empty. The
runner wrote the invalid gate artifact and stopped. The assessed-work probe
was not called.

This is useful unfavorable evidence: the repaired prompt demonstrated some
semantic sensitivity, but the exact local model is not reliable enough for the
project's citation-completeness boundary. No candidate decision from the
invalid v1 review is rehabilitated.

## Next action

Keep deterministic citation checks as hard gates and use a separately
calibrated reviewer or a bounded human reference for semantic citation review.
First correct the discovered deterministic clarification-classifier omission
without changing the original generator result. The V4 Pro candidate remains
Refine and generator held-out remains closed.
