# Final claim–evidence matrix

Status: evidence input for report discussion; not report prose

| Prospective claim | Evidence | Final status | Permitted wording boundary |
| --- | --- | --- | --- |
| A governed autonomous tutor was implemented | 670-case confirmation 024, 72-case confirmation 025, exact HTTPS qualification | Supported if final qualification passes | May claim bounded event-driven autonomy, finite loops, persisted goals, proactive in-app action, restart, and rollback under synthetic conditions |
| The system is safe against unsupported autonomous actions | Confirmation 024 reported zero unauthorized actions, scope errors, invalid citation lineage, duplicates, or unbounded loops | Supported for the evaluated synthetic conditions | Do not generalize to all real-world courses or adversaries |
| The selected factual method is high quality | Fresh 1,000-case best arm reached 63.25% fully grounded success and 96.0% boundary accuracy | Not supported | Describe a safety-oriented local fallback and a valid `Refine` result |
| The system has representative visual understanding | Jina v5 reached 16/30 versus text/OCR 26/30; control also had one wrong-region citation | Not supported | State that text/OCR fallback is retained and visual reasoning remains future work |
| The system matches the real professor | C0–C3 proxy 003 produced 45/48 non-empty responses and stopped before review; earlier proxies were invalid or Refine | Not supported | May claim a professor-profile workflow exists, not fidelity |
| The system improves real student learning | Synthetic learner state showed +0.0324 final hidden-mastery proxy, but AUROC was 0.466 and 32.9% of interventions were wasted | Not supported | Report synthetic diagnostic behavior only; no real learning claim |
| The system is usable by representative students | Automated browser and workflow checks only | Not supported | May claim functional local workflows and basic responsive/accessibility smoke |
| The exact local product is operable | HTTPS journey, restart, clean restore, rollback, and browser smoke | Pending final qualification 009 | May claim a qualified local research demo after the exact final profile passes |

## Terminal interpretations

### Professor-profile proxy

The terminal decision is `Refine`. Missing/empty outputs are treated as a
quality-contract failure rather than a transport excuse, and no profile uplift
is calculated. A synthetic profile may be used to demonstrate workflow, but it
is not a fidelity reference.

### Simulated learner state

The terminal decision is split: Keep the corrected multi-concept bookkeeping
and autonomous safety controls; Go Deeper on prediction and intervention
utility. The learner simulator is useful for regression testing, but cannot
substitute for real learning-outcome evidence.
