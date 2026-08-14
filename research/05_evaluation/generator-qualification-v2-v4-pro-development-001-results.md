# Generator qualification v2 V4 Pro development 001 results

Result ID: `generator-qualification-v2-v4-pro-development-001`

Date: 2026-08-14

Status: Completed execution; Refine pending frozen all-case cross-model review

Decision: Do not advance or select the candidate. Preserve the exact run and
classify the two ambiguity-action failures with the separately frozen local
Qwen review.

## Run identity and boundary

- Candidate: official `deepseek-v4-pro`, model version
  `DeepSeek-V4-Pro`, non-thinking JSON mode, temperature 0, one attempt,
  strict-evidence P2/v3.
- Provider fingerprint:
  `a307abda487cd1b463329ccb945ce396` on all 48 calls.
- Clean execution revision:
  `de35210a3285b6c37a1de21ca66484f71bc0ad52`.
- Dataset: unchanged 48-case public-synthetic development split, SHA-256
  `a57ffeb7618e300a1647d733d605461c948b6b84ba9a1f48af904a0f814156c4`.
- Ignored raw output:
  `reports/generated/generator-qualification-v2-v4-pro-development-001.json`,
  SHA-256
  `7e5e703373cd52c106d21a0336d93ebd67f2406e179145d2e4f0ba0eac15a27b`.
- Private-course external calls: zero.
- Generator held-out access: zero and still prohibited.
- Gemma calls: zero.

DeepSeek's current official model table confirms the model alias, JSON and
non-thinking support, and the conservative prices used here:
<https://api-docs.deepseek.com/quick_start/pricing/>.

## Deterministic and operational results

- Completed attempts: 48/48 with no retry.
- Deterministic all-check passes: 46/48 (95.8%).
- Provider identity, fingerprint, citation identity, required-term, and
  forbidden-term checks: 48/48 each.
- Ambiguity slice: 4/6 all-check passes; every other six-case scenario slice:
  6/6.
- Input/output tokens: 13,654 / 1,287.
- Conservative cost: USD 0.00705918, below the USD 1 run stop.
- Median latency: 1.444 seconds.
- p95 latency: 2.115 seconds, below the 30-second floor.

Both deterministic failures returned `action: answer` where `clarify` was
required:

- `gqv1-dev-005` explained both meanings and then explicitly asked which one
  the student meant.
- `gqv1-dev-045` explained both meanings but did not ask the student to choose
  before answering.

The first response may be semantically clarifying despite its invalid action
field. The second is a substantive clarification-policy failure. This
interpretation is diagnostic until the frozen cross-model review completes.

## Next action and limits

Run the all-48-case local Qwen review frozen in
[`2026-08-14-generator-qualification-v2-cross-model-review-plan.md`](../04_experiments/2026-08-14-generator-qualification-v2-cross-model-review-plan.md).
Any deterministic failure, Qwen revise/uncertain decision, or disagreement
remains escalated. No result from that review is independent-human evidence,
and it cannot defer or satisfy the separate 41-case authoring audit.
