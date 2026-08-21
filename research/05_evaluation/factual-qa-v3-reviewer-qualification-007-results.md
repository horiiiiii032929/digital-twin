# Factual-QA v3 reviewer qualification 007 results

## Technical summary

Hosted Qwen3.7 Plus failed six of nine frozen gates and is not selected as the
independent reviewer. Forty-one of 48 review responses were contract-valid.
Among valid responses, clean specificity was 75.0% and mutation sensitivity was
83.3%; seven responses were malformed. P95 latency was 42.46 seconds.

The route also returned up to 2,172 billed output tokens despite the requested
650-token cap. Consequently, measured cost reached USD 0.128239 and failed the
USD 0.10 gate even though the pre-run reservation was USD 0.061042. This is an
operational cost-enforcement defect to fix before any paid scale run.

## Run identity

- Result ID: `factual-qa-v3-reviewer-qualification-007`
- Execution revision: `9c97761d2863b0c3cbaccd86b789c101835a3e4a`, clean worktree
- Date: 2026-08-21
- Instrument SHA-256: `99899c7becda464d601927c6cd93f8cb6e636d3ec30ea686a2d38ee05156aa9f`
- Ignored raw output: `reports/generated/factual-qa-v3-reviewer-qualification-007.json`, SHA-256 `c57e8ed6e825eae6be16bd5c5d42b5c88d4f02f9a66195115847038b5c833b75`
- Sanitized summary: [factual-qa-v3-reviewer-qualification-007-summary.json](judgments/factual-qa-v3-reviewer-qualification-007-summary.json)
- Data boundary: synthetic-public only; zero private-data calls
- Scale toward 10,000: unauthorized

## Results

| Metric | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Provider calls | 49/49 responses | 49 maximum | Pass |
| Review completion | 41/48 (85.4%) | 100% | Fail |
| Clean specificity | 75.0% | at least 90% | Fail |
| Mutation sensitivity | 83.3% | at least 90% | Fail |
| Each mutation class | 75.0%--100% | at least 75% | Pass |
| Malformed/provider errors | 7 | 0 maximum | Fail |
| Reviewer p95 latency | 42.46 seconds | at most 8 seconds | Fail |
| External cost | USD 0.128239 | at most USD 0.10 | Fail |
| Model identity | Exact no-fallback Qwen3.7 Plus | stable required | Pass |
| Private-data calls | 0 | 0 maximum | Pass |

The run completed in 249.62 seconds. The provider exceeded the requested output
cap, so the prospective maximum reservation was not a true hard bound. No raw
response content or private data is included in the committed evidence.

## Decision and next gate

**Drop Qwen3.7 Plus for this reviewer role and retain qualified Mistral Small
4.** Revoke the one-time 007 authorization. Before separately authorizing the
100-case stage, correct the cost-control assumption, verify the correction with
network-free failure tests, and re-run the full repository gate. This result
does not authorize automatic promotion or any 100-, 1,000-, or 10,000-case run.
