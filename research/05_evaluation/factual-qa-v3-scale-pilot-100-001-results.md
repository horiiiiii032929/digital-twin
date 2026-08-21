# Factual-QA v3 scale pilot 100 attempt 001 results

## Technical summary

The paid 100-case pilot completed safely but failed nine quality gates. All 226
provider calls returned from the expected models for USD 0.110512, with complete
token/latency/cost accounting and zero reported token-limit violations. The
operational controls therefore worked as intended.

The factual-QA method did not. Nine author responses were malformed and only
4/100 cases passed deterministic validity. Most parsed answers used citation
shapes that did not satisfy the frozen source-lineage contract. All 100 Mistral
review responses were unusable under the scale-run review contract (95 schema
validation failures and five JSON parse failures), despite qualification 006.
Only four valid cases remained, all academic-integrity boundaries, so no
answerable case was eligible for the planned mutation probes. This is a
prompt/schema and fixture-construction failure, not evidence for scaling.

## Run identity

- Result ID: `factual-qa-v3-scale-pilot-100-001`
- Execution revision: `0d60f861aa0d0099eb2d59d448b6c75f24420b1c`, clean worktree
- Date: 2026-08-21
- Instrument SHA-256: `7396fbf251f483d7107a10bc2d28aecac60c5c900e0da9bb542b844d631e5edd`
- Blueprint SHA-256: `cd43954f51ceb559a2d95b57fd0b25d551c43c103d404bb5ce49bfbe33f5b2cb`
- Runner SHA-256: `f013e737956c9c2b477f7e48c83b0694fdda05b4caee2eea6aa5405b02084afa`
- Ignored raw output: `reports/generated/factual-qa-v3-scale-pilot-100-001.json`, SHA-256 `f89d47e4f3b818ed65af8e92db43727e524b65ec4615c66ac506693e672547c1`
- Sanitized summary: [factual-qa-v3-scale-pilot-100-001-summary.json](judgments/factual-qa-v3-scale-pilot-100-001-summary.json)
- Priority cross-review: [factual-qa-v3-scale-pilot-100-001-priority-review-001.json](judgments/factual-qa-v3-scale-pilot-100-001-priority-review-001.json)
- Data boundary: deterministic synthetic-public only; zero private-data calls

## Results

| Metric | Result | Outcome |
| --- | ---: | --- |
| Provider responses | 226/226 | Pass operationally |
| External cost | USD 0.110512 | Pass operationally |
| Token-limit violations | 0 | Pass operationally |
| P95 latency | 3.52 seconds | Diagnostic |
| Valid authored cases | 4/100 | Fail |
| Malformed authors | 9/100 | Fail |
| Valid independent reviews | 0/100 | Fail |
| Reviewer mutation probes | 0/20 | Fail; no eligible answerable controls |
| Citation validity | 28.2% | Fail |
| Target-claim completeness | 0% | Fail |
| Boundary action accuracy | 33.3% | Fail |
| Exact duplicate-question rate | 8% | Fail |
| Priority cross-review | 12/12 quarantines confirmed | Supports deterministic gate |

DeepSeek V4 Pro completed 24 bounded disputes, but 19 accepted and five rejected
cases that had already failed deterministic controls. These advisory verdicts
cannot override source-lineage truth and do not rescue the result.

## Decision and next gate

**Refine the method.** Preserve attempt 001 and revoke its authorization. Build
a new successor that gives authoring and review models explicit, shared JSON
schemas with valid examples, validates each provider contract with representative
canaries, and creates mutation controls independently of generated-case success.
Do not rerun this instrument, select another reviewer, or authorize 1,000 or
10,000 cases until the corrected pipeline passes network-free and bounded
provider contract tests.
