# Complete diagram and visual-contract audit

Date: 6 September 2026. Scope: all six report figures, eight tables and four
numbered equations, their captions, narrative and implementation/evidence links.
No API, type or runtime behavior was modified; historical results were not rerun.

## Audit criteria

For each figure: define the reader's question, actor/process responsibility,
input and output, arrow semantics, state ownership, decision/exception paths,
transaction boundary, recovery behavior and deliberate omissions. Deepen a
figure where an omitted distinction changes the reader's technical understanding;
put supporting details in a figure-specific contract rather than crowd every box.
Tables require units, comparable conditions and a clear decision interpretation;
mathematical notation requires denominators and scoring provenance.

## Figure-by-figure findings and corrections

| Figure | Previous ambiguity | Correction and implementation basis |
| --- | --- | --- |
| 1 Course lifecycle | Linear boxes hid blocked publication and made check-in consent resemble ordinary dialogue | Numbered actor workflow, preflight revision branch, separate consent choice, membership/current-release boundary and review loop. `publication.py:create_draft_from_onboarding/run_preflight/publish`; `service.py:create_conversation`; course and preference models. |
| 2 Logical architecture | API, domain services and worker scheduling were grouped, hiding execution ownership | Separate routes, worker entry points and three service responsibilities; labelled repository/model exchanges. `services/api/app/factory.py`, `scripts/autonomous_tutoring_worker.py`, `scripts/run_ingestion_worker.py`. Boxes are logical responsibilities, not microservices. |
| 3 Response sequence | Missing evidence-selection and validation stages; atomic save appeared unconditional | Ten numbered stages, duplicate request identity, scope lookup, evidence gate, generation, claim/citation validation, expected state revision and commit result. `service.py:submit_message/_save_turn_with_retry`; `repository.py:save_turn`. Bounded recovery and denial paths are explicit in notes and figure contract. |
| 4 Autonomy activity | Delivery and job completion looked like one transaction; state snapshot/recovery obscure | Worker lease, service snapshot, graph decision, outreach effect and final job commit shown separately. `autonomy_service.py:_process_claimed/_deliver`, `autonomy_runtime.py:_build_graph`, `proactive.py`. Stable-key retry avoids duplicate delivery; not one distributed transaction. |
| 5 Publication sequence | Older collaboration diagram did not expose current preflight/commit/hook boundaries | New native sequence separates preflight feedback from explicit publish, then index preparation, repository transition and post-publish observer. `publication.py:run_preflight/publish/rollback/_require_publishable`; `repository.py:publish_release`. The previous Draw.io/PDF remains as a historical asset. |
| 6 Persistent records | Merged messages/citations and learner/goals/outcomes obscured identities and reference direction | Separate key-bearing records and labelled many-to-one references; optional opportunity-to-goal link; dashed evidence updates. `models.py:Conversation/Message/Citation`, `autonomy_models.py:AutonomousGoalV1/ProactiveOpportunityV1/AutonomousActionV1/AutonomousOutcomeV1`. This is not a full physical schema. |

The detailed English explanation for every figure is in
[diagram-contracts.tex](diagram-contracts.tex). Main captions define arrow
semantics and important boundaries; the appendix explains data, exceptions and
what each drawing cannot establish. Sequence notes describe alternative outcomes
without falsely claiming full UML `alt`/activation notation. Solid return arrows
are numbered collaboration messages; dashed vertical lines are lifelines.

## Tables and equations

| Visual | Audit result |
| --- | --- |
| Requirements | R1–R5 are explanatory requirements mapped to Q1–Q3, not a claim that the original project brief supplied these exact identifiers. |
| Teaching settings | Eight source fields remain accounted for; tone/depth share a row. Synthetic configurations are not the advisor's observed teaching style. |
| Recorded responses | F21/F03 remain different contexts; no causal profile comparison inferred. Proactive count is all 16 selected check-ins. |
| Design decisions | Contract-based architecture choices remain distinct from shared-arm comparisons. Final profile identity and OCR limitation are explicit. |
| Evaluation design | Four experiments retain different denominators and reference methods. Fresh inputs are not independent human authorship. |
| Failure mechanisms | Seven rows remain distinct studies; no pooled ranking or invented performance comparison. |
| Software tools | Dependency references identify implementation tools rather than evidence of educational performance. |
| SDLC traceability | Artifact-to-acceptance mapping remains retrospective; current quality gates remain open. |
| Four equations | Grounding/action rates, indexed evidence coverage, adequate/defective revision rates and paired simulator differences retain their scoring meanings and denominators. No metric was changed in this revision. |

## Substantive clarifications

Preflight's stored evaluation status expresses release readiness, not a pass on
academic grounding or teaching targets. Publication replacement is atomic in the
repository, whereas index preparation and the post-publication hook are separate.
Likewise, an autonomous delivery may be committed before the final job record;
idempotency supports recovery. The response sequence does not imply that every
LangGraph checkpoint shares the final turn transaction. Logical arrows must not
be read as additional network services or physical foreign keys.

## Verification

- Publication, governed-autonomy and checkpoint coordination: 66 tests passed.
- Student API and teaching-profile authority: 32 tests passed.
- Both groups emitted existing dependency deprecation warnings; no new provider
  evaluation was executed. These are targeted contract checks, not a full app audit.
- Six figure layouts rendered and inspected; the data diagram was reflowed into
  explicit rows after the first rendering became too wide to read.
- Main compilation, bibliography/labels, PDF text bounds and local links checked.
  The existing package verifier checks all 470 companion IDs and destinations.
- Main report: 24 pages (13 main/declaration, two references, nine appendix pages).
  The 324-page detailed trial companion remains unchanged.

Local authoring scripts, before/after manuscript, build/test logs and verification
results are in `reports/generated/diagram-contract-audit-20260906/`.
