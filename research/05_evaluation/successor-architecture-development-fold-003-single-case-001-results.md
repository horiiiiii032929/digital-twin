# successor-architecture-development-fold-003-single-case-001

- **Status:** `completed-refine`
- **Decision:** no final architecture selected; continue only according to the frozen finite program.
- **Cases:** 150 paired contexts / 600 graph cells.
- **Provider:** 237 calls, USD 0.080101.
- **Provider completion:** 97.9%; safe fallback 100.0%.

## Architecture metrics

| Architecture | Acceptable move | Proactive precision | Unnecessary intervention |
| --- | ---: | ---: | ---: |
| `deterministic-workflow-a` | 70.7% | 63.3% | 0.0% |
| `governed-single-planner-b` | 44.0% | 31.3% | 0.0% |
| `hierarchical-model-based-c` | 74.0% | 70.4% | 0.0% |
| `hierarchical-model-based-c-plus-verifier` | 40.0% | 54.5% | 0.0% |

## Interpretation

Fold 003 is development evidence. It ranks the current candidates but cannot select the final architecture before a fresh method successor and cross-engine comparison. Architecture C ranked first but reached only 74.0% acceptable moves, while A reached 70.7%; B and C+V regressed materially. The five isolated planner failures all failed safely, but provider completion was 97.9%, below the frozen 99.5% gate.

Learner-state calibration is reported once as a shared diagnostic because this ablation holds the learner-state plane fixed. It is not counted as an architecture win.

## Finalization note

The original generated files were preserved by hash in the machine-readable record. Two reporting-only defects were corrected: the stale fold label and the embedded provider-ledger status, which was verified as `completed` in the terminal SQLite ledger. No metric, hard gate, ranking, or `Refine` decision changed.
