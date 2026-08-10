# Generator qualification v1 held-out 001 results

## Run identity

- Result ID: `generator-qualification-v1-heldout-001`
- Candidate: strict-evidence grounded prompt P2/v3 with DeepSeek V4 Flash non-thinking
- Status: completed and kept for the experimental profile
- Authorization: researcher authorized the one-time run on 2026-08-07
- Code revision: `e8c0ff2bbfa6f84839fad24ceeabde020d6ff3b2` with disclosed dirty worktree
- Dataset: `generator-qualification-v1.0.0-heldout`, 104 hash-sealed public synthetic cases, 13 per scenario
- Reproduction: `npm run benchmark:generator-qualification-heldout`; rerun is prohibited
- Ignored raw output: `reports/generated/generator-qualification-v1-heldout-001.json`, SHA-256 `7edee02f54b989c82811f2b1f61f950e5c07f4f629e850e352a2cb7676642946`
- Durable reviews: [`generator-qualification-v1-heldout-001-first-review.json`](judgments/generator-qualification-v1-heldout-001-first-review.json) and [`generator-qualification-v1-heldout-001-second-review.json`](judgments/generator-qualification-v1-heldout-001-second-review.json)

## Operational result

All 104 attempts completed and passed deterministic checks. The provider returned the same fingerprint used in development and stability. Usage was 29,610 input and 2,689 output tokens for USD 0.00489832. Median latency was 1.293 seconds and p95 was 1.715 seconds. There were no retries, malformed outputs, private-course calls, permission leaks, superseded-token disclosures, or assessed-work violations.

| Metric | P2 held-out | Floor |
| --- | ---: | ---: |
| Safe grounded task success | 104/104 (100%) | 80% |
| Required-claim recall, answer cases | 65/65 (100%) | 90% |
| Citation correctness, model-called cases | 78/78 (100%) | 95% |
| Citation completeness, answer cases | 65/65 (100%) | 95% |
| Reliable turn completion | 104/104 (100%) | 95% |
| p95 latency | 1.715 s | at most 10 s |
| Reported cost | USD 0.004898 | below USD 2 |

The first review inspected every output and found no unsupported claim or
action failure. A separate second pass reviewed the frozen 20-case stratified
answer sample, 30.8% of the 65 answer cases, and passed 20/20 for required-claim
recall, support precision, citation correctness, and citation completeness.
There were no disagreements. This was a second Codex pass explicitly delegated
by the researcher, not an independent human review.

## Decision

**Keep P2 and the exact DeepSeek binding in the experimental profile.** Every
prospective development, stability, held-out, operational, citation, policy,
and cost gate passed. The deterministic generator remains the rollback. This
does not establish independent human judgment, professor fidelity, real-course
quality, learning outcomes, production capacity, or permission to bypass the
broader professor-fidelity publication boundary.
