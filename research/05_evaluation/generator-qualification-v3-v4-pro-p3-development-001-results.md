# Generator qualification v3 V4 Pro P3 development 001 results

Result ID: `generator-qualification-v3-v4-pro-p3-development-001`

Date: 2026-08-14

Status: Deterministic development gates passed; calibrated semantic review
pending

Decision: Go deeper to the frozen DeepSeek high-thinking semantic review. Do
not select P3 or open generator held-out.

## Run identity and boundary

- Candidate: official `deepseek-v4-pro`, non-thinking JSON mode, temperature
  0, one attempt, clarification-first P3/v4.
- Clean execution revision:
  `1e118ec56180f399268d7eb5116c66fbfae39f04`.
- Provider fingerprint on all 48 calls:
  `a307abda487cd1b463329ccb945ce396`.
- Dataset: unchanged 48-case public-synthetic development split, SHA-256
  `a57ffeb7618e300a1647d733d605461c948b6b84ba9a1f48af904a0f814156c4`.
- Ignored raw output:
  `reports/generated/generator-qualification-v3-v4-pro-p3-development-001.json`,
  SHA-256
  `0912473156086d660f87f3e6e79373b094b3f1baa239be00e8b209de1cb20bce`.
- Private-course external calls, held-out access, Gemma calls, and retries:
  zero.

## Result

- Completed attempts: 48/48.
- Deterministic all-check passes: 48/48.
- Every scenario slice: 6/6, including ambiguity.
- Input/output tokens: 14,446 / 1,195.
- Conservative cost: USD 0.00732366, below the USD 1 stop.
- Median latency: 1.505 seconds.
- p95 latency: 3.075 seconds, below the 30-second floor.

All six ambiguity responses ask a targeted “Which meaning” question. The
previous real failure, `gqv1-dev-045`, now asks the learner to choose between
the two supported meanings. No deterministic regression appeared in another
slice.

## Limits and next action

Deterministic checks do not independently establish supported-claim precision,
semantic citation completeness, or pedagogy. Local Qwen cannot clear those
dimensions because its v2 reviewer failed the missing-citation stress probe.

Run the frozen same-family DeepSeek high-thinking semantic review over five
public defect probes and then all 48 outputs. This is useful triangulation but
not an independent model family, human review, professor approval, or
permission to open held-out. The separate 41-case authoring audit remains a
hard gate for professor-fidelity sealing.
