# Factual-QA v3 scale pilot 100 attempt 002 results

## Technical summary

The corrected paid pilot completed safely and produced a valid **Refine**
result. Attempt 002 improved deterministic validity from 4/100 to 93/100,
restored reviewer agreement to 97%, achieved 100% citation validity, and
executed all 20 independent mutation probes with 20/20 rejection. All 225 calls
returned from the exact expected models for USD 0.102517, with complete
token/latency/cost accounting and zero token-limit violations.

Five quality gates still failed. All five ambiguous cases violated the boundary
contract, one multi-source case bound a target claim to the wrong evidence, and
one no-evidence author response was malformed. Five pairs of generated questions
were exact duplicates. One independent review was malformed. The resulting
malformed-response rate was 2/223 bulk outcomes (0.897%), above the 0.5% gate.

## Run identity

- Result ID: `factual-qa-v3-scale-pilot-100-002`
- Execution revision: `1e2125b72ef0a47aa79155b35585f5c8f7b94823`, clean worktree
- Date: 2026-08-21
- Instrument SHA-256: `6dd41637cc001a6c038e23dbac77c4c83a2d1043a22d253b48c406e4b9330f6e`
- Blueprint SHA-256: `cd43954f51ceb559a2d95b57fd0b25d551c43c103d404bb5ce49bfbe33f5b2cb`
- Runner SHA-256: `fce54a086f313e2597beef8680941db08f80bb463fc7561caf67c90d4d5d082d`
- Ignored raw output: `reports/generated/factual-qa-v3-scale-pilot-100-002.json`, SHA-256 `6f792987a086af576063996183564afd2de870680434608f479650d0d804b3f2`
- Sanitized summary: [factual-qa-v3-scale-pilot-100-002-summary.json](judgments/factual-qa-v3-scale-pilot-100-002-summary.json)
- Priority cross-review: [factual-qa-v3-scale-pilot-100-002-priority-review-001.json](judgments/factual-qa-v3-scale-pilot-100-002-priority-review-001.json)
- Data boundary: deterministic synthetic-public only; zero private-data calls

## Results

| Metric | Result | Outcome |
| --- | ---: | --- |
| Provider responses | 225/225 | Pass operationally |
| External cost | USD 0.102517 | Pass operationally |
| Input / output tokens | 587,523 / 29,583 | Recorded |
| Token-limit violations | 0 | Pass operationally |
| P95 latency | 2.73 seconds | Diagnostic |
| Deterministic-valid cases | 93/100 | Fail; gate 95% |
| Citation validity | 85/85 answerable cases | Pass |
| Target-claim completeness | 84/85 answerable cases | Fail; 98.82% vs 99% |
| Boundary action accuracy | 11/15 | Fail; 73.33% vs 95% |
| Reviewer agreement | 97/100 | Pass |
| Mutation sensitivity | 20/20 | Pass |
| Unresolved disputes | 0/100 | Pass |
| Exact duplicate-question rate | 5/100 | Fail; zero allowed at this size |
| Malformed bulk outcomes | 2/223 | Fail; 0.897% vs 0.5% |
| Priority cross-review | 7 quarantines and 5 controls confirmed | Supports deterministic gate |

The 225 calls were 101 DeepSeek V4 Flash author/canary calls, 121 Mistral
Small 4 review/canary calls, and three bounded DeepSeek V4 Pro disputes. Exact
model identity remained stable. The three disputes correctly resolved two
Mistral false accepts and one malformed Mistral response.

## Cross-review findings

Codex independently inspected all 12 priority cases. Seven deterministic
quarantines were correct: five ambiguous-boundary violations, one wrong
multi-source claim/citation binding, and one malformed no-evidence author. Five
academic-integrity or valid multi-source controls were correctly retained.

Mistral's review of `fqa10k-c14-426` incorrectly claimed the selected claims and
citations were empty even though both were present. It also treated the null
authored case `fqa10k-c10-401` as a valid abstention. Deterministic controls and
DeepSeek disputes correctly rejected both, so these advisory errors did not
change the final decision.

## Decision and next gate

**Refine the pipeline; do not scale.** Keep the corrected shared contracts and
independent mutations, but move action, claim IDs, and citation lineage into a
deterministic assembler rather than asking the author model to reproduce them.
Use the model only for natural-language question/answer wording, deterministically
force empty claims/citations for boundary actions, quarantine malformed authors
without asking a reviewer to infer a missing case, and add an exact normalized
duplicate selection gate. Validate those changes network-free before any new
paid successor. Attempt 002 authorization is revoked; 1,000 and 10,000 remain
unauthorized.
