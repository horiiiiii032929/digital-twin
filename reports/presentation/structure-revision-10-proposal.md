# Presentation structure — Revision 10 proposal

Prepared: 7 September 2026. Status: proposed structure for review, not yet an approved replacement of Revision 9. The existing English script remains aligned with Revision 9 and must be revised after this structure is accepted. Video production is paused; no slide deck is being produced.

## Main change

The eight C4/UML diagrams describe the product and selected runtime behavior. They are not sufficient as the main presentation narrative: the owner also needs to see which designs were attempted, why results were disappointing, what was changed, and what evidence supports retaining the change.

Use the recurring explanatory order:

1. The concrete requirement or observed problem.
2. The design tried and its difference from the control.
3. The measured result and failure location.
4. The bounded interpretation, change and remaining limitation.

This is a speaking structure, not a new diagram notation. Use standard C4/UML diagrams for structure and behavior, ordinary tables for comparisons, and verbatim source excerpts for output failures.

## Proposed 22-slide main presentation

Times are editorial allocations, not measured delivery times. The target is approximately 33–35 minutes including a provisional three-minute demonstration and transitions. Rehearse against the actual English script before relying on the estimate.

| Slide | English title / purpose | Main evidence or visual | Revision 9 mapping |
| --- | --- | --- | --- |
| 1 | Instructor-Configurable Course Digital Twin | Title and one-sentence project scope | 1 |
| 2 | Delivery against the project brief | Requested outcome / implemented / verified / unresolved table | 2 |
| 3 | A course from onboarding to continuing support | Planned three-minute synthetic scenario; video remains paused and unfinished | 4, expanded |
| 4 | Instructor settings and observed teaching behaviour | Short setting-to-consumer table and saved F21 response; actual controls versus unvalidated preferences | 3 + 5 |
| 5 | System architecture and comparison boundaries | Existing C4 Container; identify the services whose implementations differ between studies | 6 |
| 6 | What the simulation executes and what it supplies | New UML Component view of runtime, simulator and evaluator; table of visible inputs, hidden state and measured outcomes | New explicit methodology slot |
| 7 | Why the first factual designs rejected answerable questions | Historical UML Activity variants plus Round 1 result table; shared coverage failure | 7 |
| 8 | Typed evidence targets helped; additional ranking did not | Selected control/candidate processing difference and same-study quality/latency table | 8 |
| 9 | Retrieval success did not establish answer completeness | Fresh factual result table and one verified failure example; distinguish retrieved evidence from fully supported answers | 9 |
| 10 | Planner alternatives and the reject-only failure | A/B/C/C+V design table; new UML Activity detail of C+V rejecting an otherwise usable selected action | 10 + 11 |
| 11 | Guarded replacement retains the baseline | New H UML Activity; fresh comparison results; state explicitly that model-specific added value is unisolated | 12 + 13 |
| 12 | Learner estimation and delivery timing | Selected estimator × timing rows; state simulated outcomes and unresolved validation | 15 |
| 13 | The default planner still receives a delivery proxy | New UML Activity for proxy construction; separate assessment-consumer explanation; no implied BKT integration | 16 |
| 14 | More structured wording still changed meaning incorrectly | Source / generated wording / exact defect / decision table; include only verified saved text | 17, wording focus |
| 15 | Goal completion used evidence from the wrong objective | Historical and corrected UML Activity guards; scope error explained using the recorded two-topic example | 18 |
| 16 | The correction fixed completion scope, not learning outcomes | Matched result table with history and autonomous-slice denominators kept separate | 19 |
| 17 | Current authority is checked when saving a turn | Existing tutoring UML Sequence; focus on generation-to-commit authority/revision change | 20, authority |
| 18 | A retry recognizes the saved in-app delivery | Existing recovery UML Sequence; stop between delivery commit and job-result commit | 20, recovery |
| 19 | The integrated trial ran, but its support remained generic | Historical integration results and a source-backed saved example if selected; separate this trial from the demo | 21 |
| 20 | Which evaluation claims remain valid? | Product failure / protocol invalidity / surviving evidence table; retain corrections explicitly | 22 |
| 21 | The next comparison follows the unresolved boundary | Control/candidate/fixed-components/acceptance-criteria table for the proposed adapter comparison | 23 + 24 |
| 22 | Deliverable, findings and remaining acceptance gaps | Return to the brief: implemented product, defensible engineering findings, unresolved teaching benefit | 24, conclusion |

A separate Questions page follows. Diagram count is not slide count. Do not insert all available diagrams merely because they have been made.

## Section timing

| Slides | Focus | Provisional time |
| --- | --- | --- |
| 1–6 | Product, demo and simulation boundary | 8:00 |
| 7–9 | Failed factual designs and retained limitations | 5:00 |
| 10–11 | Planner alternatives, rejection and guarded replacement | 4:00 |
| 12–14 | Learner input and instructional quality gaps | 4:30 |
| 15–18 | Scope correction, commit authority and recovery | 5:30 |
| 19–22 | Integration evidence, evaluation corrections and next decision | 5:30 |
| Transitions | Playback and page changes | 0:30–1:00 |
| Total | Main presentation | 33:00–33:30 |

Allow additional reading time if the failure excerpts need it; target 33–35 minutes. With 5–7 minutes of questions, the total is approximately 38–42 minutes. If the original 40-minute overall cap is enforced, use the lower main-talk target and rehearse the cutoff. Do not fill time by adding generic background or redundant diagram pages.

## Missing assets, in production priority order

| ID | Standard form | Intended content | Main slide |
| --- | --- | --- | --- |
| D09 | UML Activity, separately framed historical variants | Lexical/any-hit, hierarchical/coverage, and plan-observe factual paths. Initial/final nodes and guarded answer/abstain decisions. Emphasize the same coverage defect in the two complex paths without inventing a new notation. | 7; detail supporting 8–9 |
| D10 | UML Activity | C selection followed by a reject-only verifier. Rejected output terminates as no action; it does not automatically obtain a replacement action. | 10 |
| D11 | UML Activity | H: evidence readiness, permitted proposal, analytic-best agreement and minimum gain; failed replacement conditions retain A, while no authorized evidence gives no action. | 11 |
| D12 | UML Activity | Delivered goal actions and supporting identifiers become planner fields. Show the implemented calculations and the absence of a required student-answer step. Keep the independent assessment/completion path separate. | 13 |
| D13 | UML Activity, before/after diagrams with explicit historical/corrected scope | Broad learner evidence versus exact objective and committed target-concept evidence in completion. Put regression counts in a separate table. | 15 |
| D14 | UML Component | Evaluation harness: runtime under test, simulated student, scheduler/virtual clock, evaluator and hidden-state store. Document actual dependencies and allowed interfaces per named study, not one invented universal pipeline. | 6 |

D14 is important for explaining the relationship to a classroom. It must distinguish the operational dialogue trial from the separate learner/timing simulator. Their different mechanisms cannot be combined into a diagram that claims one experiment measured everything. Use a compact comparison table on slide 6 and a detailed diagram for each study in backup if one diagram becomes misleading.

A new C4 Component diagram is optional if the container view cannot expose the comparison boundary clearly; it must not replace a behavioral explanation with structural arrows. A standard diagram is needed only when it answers a concrete question better than a table or saved example.

## Failure material to prepare

| Failure / limitation | What must be available | What not to claim |
| --- | --- | --- |
| Whole-question coverage | Historical path and the same Round 1 result table | Hierarchy or event sourcing is inherently ineffective |
| Extra section ranking | Same-study quality and latency comparison | All ranking methods have no value |
| Reject-only verifier | Valid candidate selection and the subsequent rejection branch, supported by audit | Every rejection was wrong, or that verification itself is useless |
| Default planner proxy | Code-backed field construction, including the delivery-count example | This proxy alone caused every generic check-in |
| Instructional wording | Exact verified source/draft/response excerpts and the semantic error | An invented plausible error presented as a recorded output |
| Cross-objective completion | Recorded scope defect, corrected guards and matched regression | Correct software status proves student mastery |
| Evaluation invalidity | Specific protocol violation and the claim it invalidates | A broken evaluation protocol is the product's failure mechanism |
| Generic integrated support | Saved response or source-backed finding from the historical integration | Synthetic utility or operational completion demonstrates classroom benefit |

Failure examples are selected to explain the mechanism, not to estimate population error rates from a hand-picked sample.

## Use of the eight existing standard diagrams

| Existing asset | Placement |
| --- | --- |
| C4 Context | Backup, or a small introduction aid only if slide 2 needs system scope |
| C4 Container | Main slide 5 |
| UML course activity | Backup; useful when discussing onboarding without replaying the video |
| UML domain classes | Backup for course/release scope and persistence questions |
| UML publication sequence | Backup for approval, transaction and rollback questions |
| UML tutoring sequence | Main slide 17 |
| UML goal state machine | Backup for exact lifecycle semantics; a state machine alone does not explain the historical evidence-scope bug |
| UML recovery sequence | Main slide 18 |

## Material moved to backup

- Full onboarding fields and publication steps.
- Complete domain model and goal-state details.
- Model allocation / cost comparison from Revision 9 slide 14.
- Full estimator × timing grid and simulator corrections.
- Detailed vision comparisons; keep the factual conclusion available rather than deleting the evidence.
- All planner formulas, full folds and confirmation tables.
- Full evaluation correction and source index.
- Analytic-only ablation design, not yet tested in the cited comparisons.

## Evidence and editorial constraints

Sources and numeric qualifications remain those in [Revision 9](presentation-structure.md) and the [design comparison ledger](design-comparisons.md). The diagram standard remains the [C4/UML set](diagrams/standard/README.md). The provisional demo scope remains the [full-flow direction](full-flow-video-direction.md), with production paused.

No new studies, failure examples or performance results have been created for this proposal. Preserve same-study comparisons, denominators, historical/current/proposed labels and valid versus invalid evidence. When accepted, update the English script, visual plan and defence notes together; do not present the old 5,044-word timing estimate as a measurement of this new structure.

