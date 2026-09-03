# successor-architecture-engine-comparison-006-001

- **Status:** `completed-keep`
- **Decision:** Select E1 for whole-system confirmation under the preregistered factorial rule.
- **Cases:** 300 contexts / 1200 cells.
- **Provider:** 1,444 calls; 1,442 completed, two E2 generator calls failed and used the frozen deterministic fallback; USD 1.266516.

## Results

| Allocation | Planner | Generator | Preferred action* | Utility | Valid wording | Est. p95 latency |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `e1` | `gpt-5.6-luna` | `gpt-5.6-luna` | 74.7% | 0.7935 | 100.0% | 9618 ms |
| `e2` | `gpt-5.6-terra` | `gpt-5.6-luna` | 75.0% | 0.7938 | 100.0% | 9448 ms |
| `e3` | `gpt-5.6-luna` | `gpt-5.4-mini-2026-03-17` | 74.7% | 0.7935 | 100.0% | 8323 ms |
| `e4` | `gpt-5.6-terra` | `gpt-5.4-mini-2026-03-17` | 75.0% | 0.7938 | 100.0% | 8208 ms |

*Preferred-action agreement is diagnostic; deterministic authority and source-lineage checks are authoritative.*

The pooled Terra-minus-Luna planner utility effect was `+0.000354` (95% CI
`0.000000–0.001062`), so it did not meet the preregistered positive-lower-bound
rule. The pooled GPT-5.4 Mini-minus-Luna valid-strategy effect was `+0.00417`
(95% CI `0.00000–0.01042`) and likewise did not meet that rule. E2 also missed
the 99.5% allocation-level generator completion gate at 238/240. E1 therefore
provides the simplest and least expensive eligible allocation for the next
whole-system confirmation; this is not a release selection.

## Post-run audit

`SE6-6` found that 1,200/1,200 sanitized graph traces used a wall-clock
`started_at` and virtual-clock `completed_at`, producing reversed trace times.
Neither timestamp entered scoring, gold, model output, provider accounting, or
the allocation rule, so the component result remains valid with this disclosed
limitation. The shared `AgentTraceV2` contract now rejects reversed or
timezone-naive timestamps, and both reactive and autonomous graphs use their
injected event/job clock for the full trace. No historical response or metric
was changed and the finding is closed before whole-system confirmation.

This factorial comparison selects an engine allocation for whole-system confirmation. It does not establish real student learning, professor fidelity, or release readiness.
