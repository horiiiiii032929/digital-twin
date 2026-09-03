# successor-architecture-policy-value-fold-004-001

- **Status:** `completed-go-deeper`
- **Decision:** Advance guarded policy-value fusion to fresh confirmation because it passed the safety gates, was non-inferior on preferred-action agreement, and established a positive paired utility improvement over A.
- **Cases:** 150 contexts / 600 cells.
- **Provider:** 121 calls, USD 0.050874.

## Results

| Condition | Valid action | Preferred action* | Mean utility | Mean regret |
| --- | ---: | ---: | ---: | ---: |
| `deterministic-workflow-a` | 100.0% | 70.7% | 0.7860 | 0.0057 |
| `governed-single-planner-b` | 100.0% | 47.3% | 0.7564 | 0.0353 |
| `hierarchical-model-based-c` | 100.0% | 76.0% | 0.7807 | 0.0109 |
| `guarded-policy-value-planner-v2` | 100.0% | 73.3% | 0.7880 | 0.0036 |

*Preferred-action agreement is a diagnostic. Deterministic event/action-envelope validity is the hard transition gate.*

This fresh method-successor result does not rewrite or rescore Fold 003 and cannot alone select the release architecture.
