# Generation model dialogue stability

**Refine; no model adoption.** All twelve predeclared dispatches ended on the frozen source snapshot. Every delivered response has now received assistant review. All three aliases fail the zero-critical/profile criteria. Every unfavorable result is retained, including incomplete histories; no output-selected retry or favorable early stop occurred.

## Design and provenance

Three explicit V10 generator aliases use the same schema, prompt and 3,000-token cap with Luna-low planning. Each has two main 48-context trials (schedule seeds 7801/7802) and two profile 24-condition trials. Separately executed V4 controls remain visible. Generator comparisons pair candidate outcomes by context and trial. There are 48 unique main contexts across four source clusters, not 96 independent learners. All inputs are exposed synthetic development material.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty `True`. Prospective manifest `reports/generated/generation-model-dialogue-stability-development-001/manifest.json`, SHA `2f26d09101736d2280bfe99738d00e7896ff8190fcc03b58521ebc45cd7e13a8`; plan SHA `4ad9a232b134761234be412877725f2110a01792ebb3284f4e142c392fadcb06`. All 187 source hashes remained unchanged. Finite bounds: 5,400 calls / USD 888, at most two runs concurrently.

## Complete accounting

| Alias | Packet | Trial | Delivered turns | Calls | Provider failures | Known cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| v10-luna-low | main | 1 | 168 | 216 | 0 | 0.1002196 |
| v10-luna-low | profile | 1 | 24 | 28 | 0 | 0.0098930 |
| v10-luna-medium | main | 1 | 168 | 216 | 0 | 0.1038124 |
| v10-luna-medium | profile | 1 | 24 | 28 | 0 | 0.0110866 |
| v10-sol-low | main | 1 | 168 | 216 | 0 | 0.7042690 |
| v10-sol-low | profile | 1 | 24 | 28 | 0 | 0.1428966 |
| v10-sol-low | main | 2 | 168 | 216 | 0 | 0.6920432 |
| v10-sol-low | profile | 2 | 24 | 28 | 0 | 0.1399390 |
| v10-luna-medium | main | 2 | 168 | 215 | 2 | 0.1031154 |
| v10-luna-medium | profile | 2 | 24 | 28 | 0 | 0.0110338 |
| v10-luna-low | main | 2 | 137 | 170 | 4 | 0.0773826 |
| v10-luna-low | profile | 2 | 24 | 28 | 0 | 0.0094162 |

Total: 1121 delivered turns, 1417 provider attempts, 6 failures. USD 2.1051074 is the reported known-cost subtotal; unknown usage prevents treating it as a complete bill. Luna-low main trial 2 stopped both arm ledgers after four timeout/unavailable failures, leaving 15 incomplete histories and 31 undelivered turns. Luna-medium main trial 2 retained two timeout failures with safe responses. Missing and guarded targets are not useful successes.

## Decision and limitations

Frozen gates remain at least 92/96 useful main targets, each trial's pedagogy floors and 12/12 appropriate explanatory moves, all 12 context-on style opportunities and six qualified contrasts, zero candidate-owned critical events, and positive definite gain versus Luna-low. Full reviews are attached without rewriting raw evidence. Earlier V10 failed confirmation and the 28-context ceiling/no-gain result remain unchanged. No new confirmation or private course packet was opened; no default/release changed.

Full repository verification overlapped this group; latency is not capacity evidence. Assistant review is not human instructor validation or measured learning gain.

[Prospective plan](../04_experiments/2026-09-06-generation-model-dialogue-stability-plan.md) · [Complete machine record](records/generation-model-dialogue-stability-development-001.json).

## Final semantic review

| Generator alias | Useful main targets | Useful context-on style | Verified candidate critical events |
|---|---:|---:|---:|
| v10-luna-low | 87/96 | 10/12 | 2 |
| v10-luna-medium | 95/96 | 11/12 | 1 |
| v10-sol-low | 96/96 | 11/12 | 1 |

No alias qualifies. Seven Luna-low candidate targets and eight V4 targets are absent; missing comparisons are reported separately and cannot count as observed wins. All 977 delivered main and 144 profile responses were reviewed. This is assistant, unblinded, author-aware review, not human validation.

[Aggregate review](generation-model-dialogue-stability-development-001-aggregate-assistant-review.md) · [Review details](generation-model-dialogue-stability-development-001-aggregate-assistant-review.json).
