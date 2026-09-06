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
| Autonomous orchestration | T0 (150), T1-v2 reactive (150), T1-v2 autonomous (370); no T1-v1 arm in this run | `governed-full-autonomy-v2-1-persona-confirmation-024`, 670 cases | Compare shared slices within confirmation 024; condition totals differ | T1-v2 autonomous selected; T0 retained as rollback |
| Multi-concept learner state | T1-v2 reactive versus autonomous | `governed-full-autonomy-v2-1-multi-concept-confirmation-025`, 72 fresh 30-day histories | Direct paired synthetic comparison | Implementation correction kept; predictive utility remains weak |
| Learner estimator/timing research | count, BKT, PFA × constant, conditional, value timing | `successor-learner-timing-simulation-001` | Direct within simulation only | BKT/value are future hypotheses, not release components |
| Visual retrieval v4 | text/OCR versus Jina v4 late interaction | historical 30-asset retrieval and 60-case product checkpoints | Direct inside each historical checkpoint | Retrieval improvement did not become product success; not selected |
| Visual retrieval v5 | text/OCR versus Jina v5 omni | `true-visual-omni-confirmation-002`, fresh 30 assets / 60 cases | Direct paired comparison | Jina v5 dropped; text/OCR fallback retained |
| Professor-profile behavior | C0–C2/C3 synthetic proxy conditions | proxy 002/003 and analysis correction | No complete valid C0–C3 estimate | `Refine`; workflow exists, fidelity remains unproven |
| Local operations | exact HTTPS journey, restart, restore, rollback, browser smoke | qualification 011 (43/43 machine checks; 51/51 container regressions) | Direct operational checks, not academic quality | Exact final profile with correctness fixes qualified at source d9ec1a8; qualification 010 retained as rollback |

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

## Development methods added on 2026-09-06: not selected release components

The historical selected composition above remains the comparison control. New
development evidence must not silently replace its profile or reuse qualification
011 as qualification of changed code.

| Development method | Comparison / instrument | Evidence and permitted use |
| --- | --- | --- |
| Question-specific/profile candidate | Authorized top-five BM25 admission followed by asynchronous source-span answerability and approved-profile rendering; compare unchanged incumbent. | [Live005](../../05_evaluation/cross-course-quality-development-001-live-005-results.md):44/44 provider responses accepted,39/44versus 28/44mechanical containment. Joint composition comparison, not single-component causal attribution or high-quality confirmation. |
| Conditional model response schema | Request/response task mapping, clarify-specific empty aspects, question-only focus requirements; nonempty supported aspects retained for answerable output. | Live 001/002/004 failures preserved; diagnostic 003 was only two known cases. Live 005 supports further engineering work, not retrospective repair of old results. |
| Independent G7 development oracle | Four fictional mini-courses, 44 public cases with separate gold; citation metadata/source containment and literal requirements. | [Audit](../../../docs/evaluation-quality-audit-2026-09-06.md) and [rubric](../../05_evaluation/cross-course-quality-assistant-review-rubric-v1.md). Mechanical pass is not semantic correctness; human review pending. |
| Operational timeout sidecar | Exact registered nonfactual template, empty citations/claims and explicit injected-timeout ledger link. | [Sidecar](../../05_evaluation/cross-course-quality-development-001-live-005-failure-diagnostic-001-results.md):4 candidate failures closed; original 39/44 unchanged. Incumbent fast paths did not exercise provider failure. |
| Reviewed text/Markdown ingestion | Same permission, preview, versioning/publication and withdrawal flow; schema18attestation defaults false. | [G3/G4 plan](../../04_experiments/2026-09-06-source-ingestion-and-dashboard-completion-plan.md). API/journey and recovery contracts, not automatic deidentification or raw-audio support. |
| Source-window cohort feedback | Count distinct active students in release/time window, retain privacy suppression, display source difficulty, record professor proposal review. | G3/G4 actual-dialogue tests; source grouping is not concept diagnosis and the denominator is not enrollment. |
| Candidate live continuity development | Actual Luna calls through the product runtime with finite ledger limits, synthetic consent changes, outreach, learner persistence and restart; per-history provider budget remains serial. | [Full 24-history / 30-day run](../../05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md): 654 actual calls, 643 complete / 11 output-limit failures; 484 tutor turns, 16 outreach deliveries, ten synthetic replies, 24 restarts and 48 consent changes. Source hashes unchanged; quality Refine. This completes the operational development run, not learning-effect or intervention-utility evaluation. Short predecessors remain historical wiring/progression evidence. |
| V2 finite progression and Terra comparator | Four synthetic histories / 16 fixed stimuli, 24 calls per model; only reactive planning/generation model identity changes. | [Luna v2](../../05_evaluation/final-profile-operational-dialogue-development-001-progression-live-001-results.md) and [Terra](../../05_evaluation/final-profile-operational-dialogue-development-001-progression-terra-live-001-results.md) both retain two safe graph failures and weak continuation. Costs USD 0.0113548 / USD 0.084888; Refine, no replacement or full Terra autonomy claim. Unblinded reused development cases and co-resident load limit comparison. |
| Schema18 recovery / load instrumentation | Retain AnyHit recovery control; separately compare actual shared-service ASGI serial provider budget against explicit bounded concurrency five on the same 25-student × four-turn workload. | [Schema18 result](../../05_evaluation/schema18-foundation-development-20260906-001-results.md), [serial 001](../../05_evaluation/final-profile-asgi-tutoring-concurrency-development-20260906-001-results.md) and [concurrent 002](../../05_evaluation/final-profile-asgi-tutoring-concurrency-development-20260906-002-results.md). Both load runs completed 100 POSTs / 150 real calls; provider overlap one versus five. Conservative in-flight cost reservations, cancellation accounting and unknown-capability controls are tested. Serial remains default; candidate five is explicit development opt-in, not hosted qualification or teaching-quality selection. |

Final confirmation retains separate answerable, boundary, profile-dialogue and
longitudinal denominators. Prospective 400/200/200 counts need source-family and
dialogue-cluster uncertainty, independently reviewed mappings and explicit course
permissions. No new dataset here establishes real-professor fidelity or learning.

### Typed instructional candidate

The subsequent v5 experimental representation adds specific instructional
questions, learner-excerpt-linked feedback and explanatory steps. Steps refer to
already selected aspects and their exact source bindings. Its explicitly named
binding-only validator records semantic support as unverified, with zero
semantically verified claim count. It does not replace the selected release's
literal validator. See the [implementation plan](../../04_experiments/2026-09-06-evidence-linked-instructional-moves-plan.md)
and [comparison protocol](../../04_experiments/2026-09-06-meaningful-continuation-v4-v5-plan.md).
Implementation and contract tests alone do not establish a useful candidate;
registered live outcomes and the fixed semantic rubric govern that decision.

V6 additionally permits bounded imperative elicitation, feedback combined with a
next prompt, and explicit partial answers with unresolved-detail traces. It
retains only provenance admission for source-linked paraphrases. Its
[main result](../../05_evaluation/paired-pedagogy-development-001-v6-live-001-results.md)
passed the narrow development gate, but its
[boundary sidecar](../../05_evaluation/paired-pedagogy-development-001-boundary-v6-live-001-results.md)
failed; therefore it remains an experimental Refine candidate.

V7 added explicit request coverage but regressed through schema and rendering
failures. V8 uses a standalone compact schema: at most four explanation,
feedback or elicitation units, approved source IDs, and missing-detail notices.
The server resolves whole approved chunks into bindings; every generated unit
in an answer is declared, including optional questions. This is explicitly
structural association, with semantic support unverified. V8 passes the three
narrow development packets at39/48 (16/16 primary),8/8 and8/8, but six
explanatory-profile targets still choose the wrong teaching move. It remains
experimental and does not replace the selected release.

V9 gives approved profiles precedence by removing conflicting advisory planner
fields from generation input when a profile is present. V10 adds a typed union:
factual units require source IDs; elicitation units may omit them. Its provider
schema preserves the factual array minimum. Fresh-conversation clarification
also precedes empty-evidence termination, without changing historical conversation
routing. These remain opt-in through the shared experimental selector and the
credentialed staging ASGI factory. V10 development passes48/48,16/16 primary,
12/12 explanatory moves and both8/8 sidecars; confirmation and same-configuration
operations must be reported separately. Structural source association still does
not verify entailment, and no selected release default is changed.

The V10 confirmation subsequently failed semantic attribution and the profile
comparison failed an unsupported detection guarantee. Explicit generator-role
aliases vary Luna-low, Luna-medium or Sol-low while preserving Luna-low planning,
V10 schema/prompt and the 3,000-token cap. The actual API and worker builders use
the same selector; per-role ledgers preserve model, reasoning and costs, while
unknown usage stops admission. The28-case short diagnostic tied28/28 for all
three; a12-run dialogue/profile stability study found critical overstatements in
every alias. None replaces the retained release. See the
[stability review](../../05_evaluation/generation-model-dialogue-stability-development-001-aggregate-assistant-review.md).

V11 is a prospective instruction-only candidate for evidence strength: entity
ownership, implication direction, quantifiers and unsupported dependencies. It
retains the typed operation/schema and source-association limitations, with a
distinct prompt/implementation ID. Its implementation is not an entailment
verifier or a quality pass; the
[development plan](../../04_experiments/2026-09-06-evidence-strength-generation-plan.md)
defines the required content and integration evidence before selection.

## Current goal completion correction

| Method | Role | Evidence | Disposition |
| --- | --- | --- | --- |
| Exact objective-to-concept completion v2 | Goal lifecycle using committed scoped evidence | goal-completion-scope-development-001; goal-completion-scope-review-audit-001 | Keep experimental component correction; frozen whole-release requalification remains separate |
