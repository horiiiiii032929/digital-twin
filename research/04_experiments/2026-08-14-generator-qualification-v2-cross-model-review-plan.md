# Generator qualification v2 cross-model review plan

Date frozen: 2026-08-14

Status: frozen after generator execution and before cross-model review

## Source boundary

- Source run: `generator-qualification-v2-v4-pro-development-001`.
- Clean generator-execution revision:
  `de35210a3285b6c37a1de21ca66484f71bc0ad52`.
- Raw output SHA-256:
  `7e5e703373cd52c106d21a0336d93ebd67f2406e179145d2e4f0ba0eac15a27b`.
- Dataset SHA-256:
  `a57ffeb7618e300a1647d733d605461c948b6b84ba9a1f48af904a0f814156c4`.
- Boundary: all 48 public-synthetic development cases. No private course text,
  held-out generator case, human authoring packet, or professor-fidelity
  condition mapping may be read.

The review covers every case rather than a post-result sample. The reviewer is
not shown the generator/provider identity, deterministic pass/fail label, run
aggregate, or another review decision.

## Reviewer binding

- Reviewer: local `qwen3:4b`.
- Digest:
  `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
- Prompt version: `generator-qualification-v2-qwen-review-v1`.
- Thinking: disabled.
- Temperature: 0.
- Per-case seed: stable hash of prompt version, model digest, and case ID.
- Output: JSON schema, at most 700 generated tokens, no retry.
- Network: loopback Ollama only.
- Gemma: prohibited.

## Review contract

The reviewer evaluates expected action, required-claim recall, supported-claim
precision, citation correctness and completeness, misconception repair,
academic-integrity behavior, and clarification quality. Non-applicable checks
must be true. Approval requires every check to be true and no uncertainty.

Any Qwen revise/uncertain result, deterministic failure, or disagreement is
escalated. Cross-model approval cannot repair a deterministic failure or count
as independent-human or professor approval. This review can classify the V4
Pro candidate as Keep, Refine, Go Deeper, or Drop for later work; it cannot
select the profile, open generator held-out, create the professor-fidelity
seal, or bypass the separate 41-case human authoring audit.

## Commands

```bash
uv run python -m scripts.review_generator_qualification_v2
uv run python -m scripts.review_generator_qualification_v2 --execute
```
