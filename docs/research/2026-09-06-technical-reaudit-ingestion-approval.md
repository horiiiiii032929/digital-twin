# Technical re-audit: ingestion and approval

The re-audit found and fixed six concrete correctness defects. These are implementation regressions and authority checks, not changes to evaluated tutoring prompts or claims of improved answer quality. Existing dirty work was preserved; no provider evaluation, deployment or sealed data was used.

| Defect reproduced before the fix | Correction | Regression evidence |
|---|---|---|
| `new_teaching_profile` merged caller values after authoritative course/version and accepted lifecycle fields; domain callers could set another course, version or withdrawal state. API draft schemas already excluded these fields. | Accept only the eight teaching-preference fields at the constructor boundary. | Three parameter cases reject course/version/lifecycle injection before saving. |
| Two SQLite connections read the same latest profile version, then one draft failed with an uncaught UNIQUE constraint error. | `create_teaching_profile_draft` acquires a SQLite write lock before allocating and saving the next version. | A barrier reproduces the former read/read/write race; both drafts now persist with distinct versions1/2. |
| Ingestion checked a second object-store read rather than the bytes handed to the parser. If the reads differed, the checked buffer and processed buffer were different. | Hash the already-read input bytes. | A changed read plus a matching subsequent store checksum is rejected before parser entry. |
| A stalled worker invocation and a newly recovered invocation reused the same worker name. The old invocation could fail the new running attempt. | Every `process_one` invocation uses a unique lease-owner token for claim, heartbeat and terminal writes. | Two overlapping attempts with an expired first lease and the same worker name: the stale failure leaves the new attempt running, and attempt2 succeeds. |
| A teaching profile could be withdrawn after release preflight but before publication. Publication still succeeded and withdrew the working predecessor. | `publish_release` acquires write serialization and rechecks course/hash and approved-or-superseded profile status before touching release states. Publication/rollback map authority errors to their normal domain/API error. | Withdrawal during index preparation rejects publication and preserves the previous published release. Superseded profiles remain permitted for immutable previously approved releases. |
| Teaching-profile authorization checked course ownership/membership but not account revocation or professor role. | Require an active professor account as well as active owner membership. Generated preview uses this same authorization boundary. | A revoked owner cannot create a profile. |

All eight new regression cases failed on the previous corresponding implementation before their fixes. The final scoped command is:

```sh
.venv/bin/pytest -q tests/test_ingestion_approval_reaudit.py tests/services/test_ingestion_jobs.py tests/test_generated_professor_preview.py tests/api/test_publication_api.py tests/api/test_text_ingestion_journey.py
```

Final result: **92 tests passed** in8.27seconds; Ruff checks passed for the changed Python files. Only existing PyMuPDF/SWIG deprecation warnings remain.

During integrated verification, twelve existing generated-preview tests exposed a nested-budget capability regression in the parallel provider audit: a wrapper advertised an estimator although its underlying serial client had none. The provider-audit author fixed capability propagation; the real-estimator `None` rejection remains strict. No teaching-profile or provider safety check was weakened to make these tests pass.

## Reviewed boundaries

Read `services/ingestion/jobs.py`, `services/persistence/ingestion_jobs.py`, publication API routes, `src/digital_twin/student/teaching_profile.py`, `src/digital_twin/student/generated_preview.py`, `services/api/app/generated_preview.py`, and the related profile/publication repository methods. Also traced API identity selection in `services/api/app/dependencies.py`, publication ownership checks and course-deletion locking in `services/operations/lifecycle.py`.

Ingestion idempotency, completed-job release ownership, source identity/chunk consistency, cancellation eligibility, lease expiry and bounded retry behavior were checked against existing tests. Course deletion already starts `BEGIN IMMEDIATE` and refuses running ingestion. Generated preview binds the displayed artifact to current profile, source/policy snapshot and configuration; approval rechecks those bindings, records an immutable review and does not rerun generation. Its shadow repository keeps preview learner messages separate from real learner data. Existing generated-preview tests exercise these paths with injected model responses.

Modified files: `services/ingestion/jobs.py`, `src/digital_twin/student/teaching_profile.py`, `src/digital_twin/student/publication.py`, `src/digital_twin/student/repository.py` (new draft allocator/protocol entry and publication transition only), and `tests/test_ingestion_approval_reaudit.py`. The root agent independently owns other edits to the shared repository and student turn authority. No code change was necessary in the ingestion repository, generated-preview helper or publication transport routes.

This is a targeted technical audit with deterministic regressions, not a proof that every concurrency interleaving or authorization path is bug-free. The direct ingestion-repository API still expects callers to use distinct lease-owner identities; the actual worker service now supplies them. No production load, real identity-provider or paid-model test was performed.

## Full-check integration follow-up

The first full repository check retained its failures in `/tmp/technical-reaudit-full-check.log` (2510 passed,19 failed). One withdrawn-profile test asserted the old exception wording rather than the authority contract. It now asserts `StudentWorkflowError.code == teaching_profile_unavailable`, zero provider calls, and unchanged persisted messages. The stronger earlier admission guard remains intact.

The responsiveness runner failures were strict operational-record validation errors after serial provider requests began recording real cost reservations. The provider-audit author added validated optional reservation fields to `AutonomyProviderCallV1`; no responsiveness data, gold, threshold or model behavior was changed. The targeted rerun covers both teaching-profile context and responsiveness runner suites. Original failed logs are retained at `/tmp/profile-reaudit-failures.txt` and `/tmp/responsiveness-reaudit-failures.txt`.

Targeted full-check follow-up result: **24 passed** in18.11seconds; Ruff passed for the revised test. No runtime authority checks were weakened.
