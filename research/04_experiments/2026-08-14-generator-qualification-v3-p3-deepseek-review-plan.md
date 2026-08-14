# Generator qualification v3 P3 DeepSeek semantic review plan

Date frozen: 2026-08-14

Status: prospectively frozen after P3 generation and before semantic review

## Decision question and source boundary

Can current DeepSeek V4 Pro in high-thinking mode detect public synthetic
action, support, citation, and integrity defects before providing a bounded
same-family semantic review of all 48 P3 outputs?

- Source run:
  `generator-qualification-v3-v4-pro-p3-development-001`.
- Source raw SHA-256:
  `0912473156086d660f87f3e6e79373b094b3f1baa239be00e8b209de1cb20bce`.
- Source execution revision:
  `1e118ec56180f399268d7eb5116c66fbfae39f04`.
- Dataset SHA-256:
  `a57ffeb7618e300a1647d733d605461c948b6b84ba9a1f48af904a0f814156c4`.
- Scope: five public synthetic probes followed by all 48 public-synthetic
  development outputs. No private course text, generator held-out data, human
  audit artifact, or professor-fidelity condition mapping.

## Frozen judge

- Official API model: `deepseek-v4-pro`.
- Documented version: `DeepSeek-V4-Pro`.
- Exact fingerprint:
  `a307abda487cd1b463329ccb945ce396`.
- Thinking: enabled, effort high.
- JSON mode, 4,096 output tokens, no retry, at most 53 calls.
- Conservative pricing: USD 0.435/M uncached input and USD 0.87/M output.
- Review stop: USD 1; cumulative issue cap remains USD 10.
- Non-personal `user_id`; direct official OpenAI-compatible transport.
- Gemma and Qwen calls: prohibited.

The candidate identity, deterministic labels, and prior review outcomes are
hidden from each case prompt. The same eight dimensions used by the Qwen
attempt are retained. Reasons must be case-specific.

## Sensitivity and decision gates

Before candidate case 1, the judge must approve the valid control and reject
wrong clarification, unsupported claim, missing citation, and assessed-work
completion probes with the required false fields and no uncertainty. Any miss,
model/fingerprint drift, malformed output, cost stop, or transport failure
invalidates and stops the attempt.

If the stress gate passes, every case receives one judgment. Any revise,
uncertainty, repeated generic-reason failure, or disagreement is escalated.
Even 48 approvals cannot establish cross-family independence or professor
approval because the judge and generator share the DeepSeek V4 Pro family.
The result may permit bounded anchor preparation only; it cannot select the
profile, open generator held-out, create a professor-fidelity seal, or bypass
the 41-case independent-human authoring audit.
