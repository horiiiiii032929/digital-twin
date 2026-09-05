# Final method catalog

Status: evidence input for report discussion; not report prose

## Comparability rule

Only methods run on the same frozen cases, source package, scoring code, and
decision gates are direct comparisons. Results from different datasets or
evaluation generations are retained as historical or diagnostic evidence and
must not be placed on one ranking axis.

| Method family | Compared alternatives | Strongest valid evidence | Comparability | Final use |
| --- | --- | --- | --- | --- |
| Fresh factual product | BM25 any-hit, BM25 question-targeted, BM25 dominance, Qwen question-targeted, Qwen dominance | `final-cross-method-factual-confirmation-001`, 1,000 fresh cases | Direct five-arm comparison | BM25 dominance selected as safest local fallback; absolute result is `Refine` |
| Known large factual regression | Selected winner versus any-hit control | `academic-factual-qa-open-10000-winner-regression-001`, 10,000 + 1,000 known cases | Direct within that run; known benchmark only | Negative engineering regression evidence; never retuned or rerun |
| Historical retrieval | term overlap, BM25, Qwen embeddings, hybrid, hybrid + reranking | retrieval development and held-out records | Direct only inside each historical run | Supporting development history; not interchangeable with the fresh product result |
| Autonomous orchestration | T0, T1-v1, T1-v2 reactive, T1-v2 autonomous | `governed-full-autonomy-v2-1-persona-confirmation-024`, 670 cases | Direct within confirmation 024 | T1-v2 autonomous selected; T0 retained as rollback |
| Multi-concept learner state | T1-v2 reactive versus autonomous | `governed-full-autonomy-v2-1-multi-concept-confirmation-025`, 72 fresh 30-day histories | Direct paired synthetic comparison | Implementation correction kept; predictive utility remains weak |
| Learner estimator/timing research | count, BKT, PFA × constant, conditional, value timing | `successor-learner-timing-simulation-001` | Direct within simulation only | BKT/value are future hypotheses, not release components |
| Visual retrieval v4 | text/OCR versus Jina v4 late interaction | historical 30-asset retrieval and 60-case product checkpoints | Direct inside each historical checkpoint | Retrieval improvement did not become product success; not selected |
| Visual retrieval v5 | text/OCR versus Jina v5 omni | `true-visual-omni-confirmation-002`, fresh 30 assets / 60 cases | Direct paired comparison | Jina v5 dropped; text/OCR fallback retained |
| Professor-profile behavior | C0–C2/C3 synthetic proxy conditions | proxy 002/003 and analysis correction | No complete valid C0–C3 estimate | `Refine`; workflow exists, fidelity remains unproven |
| Local operations | exact HTTPS journey, restart, restore, rollback, browser smoke | qualification 008 and final successor qualification | Direct operational checks, not academic quality | Requalify the final exact profile before tagging |

## Selected local composition

- Retriever: explicit `bm25-v1`.
- Evidence gate: `dominance-scoped-ambiguity-safe-v3`.
- Factual generator: deterministic evidence-set V2.
- Orchestration: governed T1-v2 with Luna H+E1 planning for complex actions.
- Policy and citations: deterministic server-owned authority.
- Visual path: text/OCR fallback; no Jina runtime.
- Rollback: deterministic T0.

Selection means “best measured safe local composition,” not “all academic
quality gates passed.”
