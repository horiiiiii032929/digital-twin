# Conditional revision and generated-preview integration audit

The root assistant reviewed the changed integration after the delegated code
reviews and retained their limitations. This is a software audit, not independent
semantic or professor validation. V14 remains unselected. The first two medium
component trials pass their fixed rubric, but integrated quality is pending.

Reviewed boundaries: explicit role/model/effort/cap routing, immutable source and
prompt snapshots, conditional keep/repair accounting and fail-closed composition,
profile-to-published-release authority, generated artifact ownership and hashes,
source permissions, isolated preview persistence, transactional approval,
withdrawal cancellation, saved review APIs and frontend async state.

Two additional defects were fixed: the role transport validator rejected the
preregistered medium revision configuration, and approval read mutable profile
status before acquiring the cross-connection writer lock. The lock now prevents
an intervening withdrawal from being overwritten by a stale draft. A frontend
late-list race now preserves freshly created artifacts and reviewed states.

Verification retained under
`reports/generated/conditional-revision-preview-verification-20260906/`:
- Broad invocation:159 passes and10 failures, all from sandbox denial of ps.
- HTTPS file retry with local process/socket access:12 passes.
- First explicit medium integration:four failures at the low-only validator.
- Corrected medium generation/paired/restart/HTTPS contracts:four passes.
- Final preview, role, component-control and authority regressions:73 passes.
- Two-connection concurrent-withdrawal regression:three passes.
- Actual owned ingestion-to-preview-review API:three passes.
- Frontend tests after late-list fix:64 passes.

Injected responses exercise runtime and API plumbing; they do not prove model
quality. Raw synthetic live component results are registered separately. Whole
npm check, live browser qualification, course transfer and longitudinal quality
remain pending. No selected profile, default deployment or professor rating was
changed. The following exact file hashes are recorded by the correctness audit;
existing historical audits remain intact.

- `apps/web/src/components/professor/generated-preview-review.ts`
- `apps/web/src/components/professor/generated-teaching-preview.test.tsx`
- `apps/web/src/components/professor/generated-teaching-preview.tsx`
- `apps/web/src/components/professor/professor-autonomy-panel.tsx`
- `apps/web/src/components/professor/professor-delivery-workspace.tsx`
- `apps/web/src/lib/api/professor.test.ts`
- `apps/web/src/lib/api/professor.ts`
- `apps/web/src/lib/api/types.ts`
- `scripts/final_profile_longitudinal_runtime.py`
- `scripts/run_authenticated_loopback_load_development.py`
- `scripts/run_factual_revision_controls.py`
- `scripts/run_generation_role_model_comparison.py`
- `scripts/run_instructional_operational_comparison.py`
- `scripts/run_paired_pedagogy_development.py`
- `scripts/run_teaching_profile_responsiveness_development.py`
- `services/api/app/factory.py`
- `services/api/app/generated_preview.py`
- `services/api/app/routers/publication.py`
- `services/llm/experimental_role_routing.py`
- `services/llm/openai_responses_client.py`
- `src/digital_twin/evaluation/experimental_tutoring_candidate.py`
- `src/digital_twin/generation/conditional_revision.py`
- `src/digital_twin/student/generated_preview.py`
- `src/digital_twin/student/migrations.py`
- `src/digital_twin/student/proactive.py`
- `src/digital_twin/student/repository.py`
- `src/digital_twin/student/teaching_profile.py`
- `src/digital_twin/student/teaching_profile_context.py`
- `tests/test_authenticated_loopback_load_development.py`
- `tests/test_conditional_revision_generation.py`
- `tests/test_factual_revision_controls.py`
- `tests/test_generated_professor_preview.py`
- `tests/test_generation_role_model_comparison.py`
- `tests/test_instructional_operational_comparison.py`
- `tests/test_paired_pedagogy_development.py`
- `tests/test_teaching_profile_context_candidate.py`
- `tests/test_teaching_profile_responsiveness_runner.py`

## Source–oracle follow-up verification

The full check ended with2424 Python tests passing and two failures: the newly
introduced dataset builder lacked the repository freeze guard/registry entry.
Both were corrected; ten oracle/registry tests then passed. All112 paired injected
histories on the new48-case v3 and8-case necessity packets completed in the
unchanged isolated V14-medium runtime. This is transport/packet validation only.

A subsequent V15-only global support helper shares conditional revision contracts
through an optional instruction parameter; V14's default system text is unchanged.
Root and a separate assistant code reviewer traced the new instructions through
the actual provider request, verified medium/3000/112-call bounds, source snapshot
coverage and unchanged fail-closed handling. Thirty-eight shared tests and nineteen
isolated helper/runner tests passed. The new helper is not integrated into product
orchestration. Its semantic effect remains subject to preregistered live controls.

The second full check retained2432 passing Python tests and one stale exact
allowlist expectation (`main-oracle-alignment-001` had been explicitly registered
for dataset generation only). The expectation now names that exact authorization
and asserts its limited operation;14 related freeze/oracle tests pass. The failed
full-command log remains `reports/generated/conditional-revision-preview-verification-20260906/npm-check-after-oracle-support.log`.
Do not describe either failed full command as a clean all-checks pass. Frontend
checks are completed separately after the Python command's early stop.
