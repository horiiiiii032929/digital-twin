# V15 integration map (prospective, read-only audit)

This map was prepared while the two112-control V15 component trials were running. No runtime implementation, selector, default, release profile, or result was changed by this audit. Integration remains conditional on both component gates. The helper's existence or the map is not evidence of efficacy.

## Smallest reversible change

Retain the V14 prompt and behavior. Add a narrow overridable assessment method to `ConditionalRevisionInstructionalGenerator` in `src/digital_twin/generation/conditional_revision.py`, whose default delegates to the existing `conditionally_revise_instructional_proposal`. Its existing `_request_proposal` calls that method at the current assessment site. In `src/digital_twin/generation/global_support_revision.py`, add a small subclass that sets implementation ID `question-specific-profile-grounded-v15`, version `v15-development`, and overrides only that method to call the existing `globally_assess_instructional_proposal`.

This reuses V14's draft validation, KEEP identity, repair schema, summed usage, failure accounting, composition and actual-provider trace. Do not replace V14's module constant, monkeypatch its helper, or override `_system_instruction`: that instruction drives the Luna draft, whereas V15 changes the Sol assessment. Current helper calls the same `question_specific_conditional_revision` task with the same public payload and schema, but a different system instruction. No task/schema fork is necessary.

## Configuration path

| Boundary | Exact integration point | Required behavior/check |
| --- | --- | --- |
| Selection | `src/digital_twin/evaluation/experimental_tutoring_candidate.py`: `GENERATION_VARIANTS`, `experimental_tutoring_configuration` | Add only explicit `v15-luna-sol-medium`; resolve version v15, include v15 in every inherited compact/authority/typed/evidence/factual/conditional flag set, add a global-support flag. Luna-low planner/draft, Sol-medium revision, cap3000; final role remains generation-if-kept-otherwise-revision. Never change existing variant defaults or selected release. |
| Restartable fixture runtime | `scripts/final_profile_longitudinal_runtime.py`: `build_final_profile_runtime_factory` signature and nested `open_app` | Accept/forward the new flag both initially and on reopen. Missing signature causes unexpected-keyword failure; omitted forwarding silently selects V14 after restart. |
| API graph | `services/api/app/factory.py`: `create_app` signature, initial flag guards, nested generator selection near conditional revision, `app.state.experimental_generation_configuration` | Require global-support flag to imply conditional revision (existing chain then requires factual/evidence/typed and excludes bounded revision). Choose V15 subclass only under explicit flag and prioritize V15 ID in reported candidate metadata. |
| Authenticated application | `services/api/app/experimental.py`: `build_experimental_app` | Already forwards all selected flags and checks actual generator ID against selector. Existing exact transport-role validation supports Sol-medium. Add alias contract coverage; no new fallback. |
| Worker | `scripts/autonomous_tutoring_worker.py`: `build_worker_app` | Uses explicit experimental app selector; no new dispatch branch should be needed. Test same selected identity after worker construction/restart. |
| Preview shadow | `services/api/app/factory.py`: signature-based `preview_parameters`; `services/api/app/generated_preview.py`: `attach_generated_preview`, `configuration`, nested `run` | New signature flag is captured automatically and forwarded to shadow factory. Test preview actually uses V15 and global assessment message, not just selection metadata. Existing60-call/USD9.60 cap and isolation remain. |

Generated preview's `prompt_sha256` currently hashes only `generator._system_instruction()` (draft prompt), so it alone cannot distinguish V14/V15 assessment. The artifact also binds the full source fingerprint and selection, which does distinguish them. Preserve those bindings; either explicitly label the draft hash or add an assessment-instruction hash if needed for readable provenance. Never claim the draft hash proves revision-prompt identity. Source fingerprint rejects on-disk runtime drift until restart.

## Provider and trace contract

`services/llm/experimental_role_routing.py::ExperimentalGenerationRoleRouter.role_for_task` already maps the shared conditional task to revision, and its constructor permits Luna-low plus Sol-medium. `services/llm/openai_responses_client.py::_output_type` and `_schema` already use `ConditionalRevisionDecision` and preserve factual-unit `source_ids` minimum length for that task. No provider/schema changes are required if the task remains shared. Verify actual request input contains `GLOBAL_INSTRUCTION`, reasoning is medium, and KEEP output trace says Luna while REPAIR says Sol. The wrapper's assessment verdict is not semantic certification. `ConditionalRevisionInstructionalGenerator._compose` already derives disposition from the validated provider identity and records combined usage; inherited failure behavior must preserve draft-only versus combined failure usage.

The existing pre-assessment `super()._compose` can reject an invalid draft before Sol receives it. Preserve that behavior for this bounded prompt comparison and report safe validation refusals; altering it would be another candidate change requiring separate evaluation. Also retain one assessment request, no success-selected retries and fail-closed unknown usage/identity behavior.

## Runners and recorded evidence

- `scripts/run_generation_role_model_comparison.py`: add alias to `AVAILABLE_VERSIONS`, explicit V15 `EXPECTED_IDS`, and archive the V15 plan. Role-count and five-call conservative planning already inspect selected roles.
- `scripts/run_paired_pedagogy_development.py`: add alias to `ROLE_VARIANTS` (derived expected ID then becomes V15), and to `revision_variant` so1200-call/USD192 ceilings, three-role partition and five-call-per-turn envelope apply. Archive V15 plan. Both initial and restarted generator-ID checks already exist.
- `scripts/run_instructional_operational_comparison.py`: add alias to `ROLE_VARIANTS`, archive V15 plan. It derives role count from selection; underlying `scripts/run_operational_dialogue_development.py::run_history` forwards runtime flags.
- `scripts/run_authenticated_loopback_load_development.py`: add alias to validation set, CLI choices, and both three-role budget membership tests (1200/USD192). Its injected conditional-task fixture can remain shared.
- `scripts/run_teaching_profile_responsiveness_development.py`: selection is dynamic and revision budgets already require150calls/USD24–30. Archive V15 plan and extend alias test coverage. Shared conditional task remains in revision profile-binding inspection.
- `scripts/recorded_generation_roles.py::create_recorded_generation_roles` already creates exact configured transports and partitions finite budgets across three roles; no new branch needed. Each role retains its own actual request ledger.

Do not reuse old runtime freezes as if V15 were byte-identical. Produce a new isolated source/configuration/prompt snapshot and retain V14 controls. Narrow historical V14 successes do not become V15 integrated qualification. Inspect runtime hashes and exact request ledgers rather than trusting a declared alias. Freeze/audit authorization instruments and README must record added files/commands where applicable; no new external-run permission is implied by this map.

## Tests before any integrated provider dispatch

Extend `tests/test_global_support_revision.py` from helper contracts to generator KEEP and REPAIR, V15 ID/trace, combined usage, unsupported response/unknown identity/usage failures, and exact global assessment prompt. Keep `tests/test_conditional_revision_generation.py` as an unchanged-control regression, especially exact V14 instruction and KEEP byte identity. Add selector and invalid flag-chain assertions.

Extend alias parameterization/assertions in `tests/test_generation_role_model_comparison.py`, `tests/test_paired_pedagogy_development.py`, `tests/test_instructional_operational_comparison.py`, `tests/test_authenticated_loopback_load_development.py`, `tests/test_teaching_profile_responsiveness_runner.py`, `tests/test_generated_professor_preview.py`, and worker composition coverage. Update hard-coded revision-alias budget sets and KEEP-final-provider sets in tests; otherwise correct V15 selection can fail for stale V14-only expectations. Verify injected actual API, saved preview/review, reopened repository, publication/withdrawal boundaries and trace lineage. Existing task mocks need no new schema but should assert V15's distinct assessment prompt when that alias is selected.

After passing component gates and implementing this bounded integration, run component/control regressions, all affected runner/API tests, repository required checks, and new frozen integrated development gates. Browser, independent confirmation, permitted course transfer and full evaluation remain separate qualification work.
