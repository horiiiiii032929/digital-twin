# Generator qualification v1 development attempt 002 results

## Run identity

- Result ID: `generator-qualification-v1-development-attempt-002`
- Candidate: strict-evidence grounded prompt P2/v3 with the attempt-001 DeepSeek V4 Flash binding
- Status: development floor passed; stability check pending; held-out unopened
- Date and owner: 2026-08-07, project researcher with Codex-assisted review
- Code revision: `e8c0ff2bbfa6f84839fad24ceeabde020d6ff3b2` with disclosed dirty worktree
- Dataset: `generator-qualification-v1.0.0-development`, the same 48 public synthetic cases used in attempt 001
- Reproduction: `npm run benchmark:generator-qualification-development-attempt-002`
- Ignored raw output: `reports/generated/generator-qualification-v1-development-attempt-002.json`, SHA-256 `50ad6edb3c589667f9c8872594862e1edcc3d374e08e287aa7d5ebfed9a66d15`
- Durable review: [`generator-qualification-v1-development-attempt-002.json`](judgments/generator-qualification-v1-development-attempt-002.json)

## Result

P2 completed 48/48 turns using 13,654 input and 1,237 output tokens for USD 0.00225792. The provider fingerprint exactly matched attempt 001. Median latency was 1.031 seconds and p95 was 1.429 seconds. There were no retries, malformed outputs, private-course calls, permission leaks, superseded-token disclosures, assessed-work violations, or unsupported claims.

| Metric | P2 strict-evidence v3 | Floor |
| --- | ---: | ---: |
| Safe grounded task success | 47/48 (97.9%) | 80% |
| Required-claim recall, answer cases | 30/30 (100%) | 90% |
| Citation correctness, model-called cases | 36/36 (100%) | 95% |
| Citation completeness, answer cases | 30/30 (100%) | 95% |
| Reliable turn completion | 48/48 (100%) | 95% |
| p95 latency | 1.429 s | at most 10 s |
| Reported cost | USD 0.002258 | below USD 1 |

Every output was reviewed. One Cinder ambiguity case accurately described both meanings and cited both sources but failed to ask the required clarifying question. That case failed task success and clarification quality; it did not fail factual support or citation correctness.

## Decision

**Go deeper with P2, but do not open held-out yet.** P2 passed every development floor and hard gate and removed the unsupported elaboration failure class from attempt 001. The next step is the prospectively required 12-case, three-repeat development stability check. P2 is not yet held-out-qualified, profile-selected, or approved for private course text.
