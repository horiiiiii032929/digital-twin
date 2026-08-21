# Factual-QA v3 reviewer qualification 006 results

## Technical summary

The focused strict-reviewer qualification passed every frozen gate. Mistral
Small 4 accepted all 24 deterministic clean controls and rejected all 24 paired
defects. Sensitivity was 100% for each missing-citation, truncated-citation,
paraphrased-citation, extra-supported-claim, invalid-claim, and invalid-source
slice. All 49 calls completed with no malformed or provider errors.

This qualifies the strict reviewer as an advisory quality-control component for
the design of the professor-requested 10,000-case dummy factual-QA pipeline. It
does not make model agreement ground truth and does not authorize the 10,000-case
execution. Deterministic source lineage remains authoritative.

## Run identity

- Result ID: `factual-qa-v3-reviewer-qualification-006`
- Execution revision: `15d0a83ed976b2e5e61a815afb153270a9ee7c76`, clean worktree
- Date: 2026-08-20
- Instrument SHA-256: `ece01bfcf163b6e498a1273f1de14f14c557aa8308f1eeadf50024412773ae85`
- Ignored raw output: `reports/generated/factual-qa-v3-reviewer-qualification-006.json`, SHA-256 `255b370397b3dfeb04b044868600c4c2966bd74a2cc959d04074b60e6ae647b1`
- Sanitized summary: [factual-qa-v3-reviewer-qualification-006-summary.json](judgments/factual-qa-v3-reviewer-qualification-006-summary.json)
- Data boundary: synthetic-public only; zero private-data calls
- Scale toward 10,000: unauthorized pending a separate frozen design and paid checkpoint

## Results

| Metric | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Provider calls | 49/49 responses | 49 maximum | Pass |
| Review completion | 48/48 | 100% | Pass |
| Clean specificity | 24/24 (100%) | at least 90% | Pass |
| Mutation sensitivity | 24/24 (100%) | at least 90% | Pass |
| Each mutation class | 4/4 (100%) | at least 75% | Pass |
| Malformed/provider errors | 0 | 0 maximum | Pass |
| Reviewer p95 latency | 2.99 seconds | at most 8 seconds | Pass |
| External cost | USD 0.012175 | at most USD 0.50 | Pass |
| Model identity | Exact no-fallback Mistral Small 4 | stable required | Pass |
| Private-data calls | 0 | 0 maximum | Pass |

The run completed in 16.04 seconds. Its prospective maximum reservation was USD
0.028569, below the USD 0.50 hard stop. Checkpoints were durably rewritten after
the canary and each eight-call batch.

## Decision and next gate

**Keep the strict reviewer for advisory scale-pipeline quality control.** Design
the 10,000-case dummy factual-QA pipeline with deterministic source truth,
multi-model comparison, deduplication, batch checkpoints, exact call/token/cost
accounting, and staged 100- and 1,000-case gates. Any paid scale execution still
requires a separate authorization. Real-source and autonomous Professor Digital
Twin evaluations remain separate later tracks.
