# Schema 18 recovery verification

Fresh development output:
`reports/generated/schema18-foundation-development-20260906-001/result.json`.
The wrapper retains the original verifier's historical harness identifier but
uses a new run ID and exclusive directory. The result records current revision,
dirty state and harness hash. The parent registers this named result separately.

All 42 existing staging-foundation checks passed using a fresh temporary runtime.
Backup reported schema 18 and seven data files; clean restore passed. No Docker
container, existing listening port, private source or external model was used.
The verifier injects AnyHit and uses in-process TestClient requests; this is a
synthetic control recovery check, not the selected tutor or hosted deployment.
Its 100-request timing loop is not model-backed tutoring load qualification.

Additional repeatable contracts:

```sh
uv run pytest -q tests/services/test_schema18_product_recovery.py tests/services/test_runtime_backup.py tests/test_verify_deployable_foundation.py tests/api/test_text_ingestion_journey.py tests/test_tutoring_capacity_probe.py
```

24 tests passed. New recovery cases enqueue and complete reviewed `.txt` and
`.md` sources, close repositories, back up the runtime, restore into an empty
root, and verify source bytes/checksum, retained attestation, completed job chunks
and published release identity. A separate real-ASGI three-student/two-turn test
uses the tutoring POST probe and checks six cited replies and persisted turns.
It uses a deterministic test retriever and generation; its assertions are
transport/integration contracts, not educational quality or deployed capacity.

## Remaining G6 execution

1. Build the eventual candidate revision, retaining exact image/profile hashes
   and a fresh synthetic runtime; avoid modifying existing local services.
2. Run approved PDF/text ingestion and publication, real tutoring replies and
   cohort review through that deployment; record model identity and usage.
3. Quiesce ingestion and outgoing delivery before backup, then restore into a
   separate empty root. Check source/job/approval/profile state, previous turns,
   pending outreach and absence of duplicate delivery before resuming workers.
4. Provision distinct consented synthetic students and independent conversations;
   use `measure_tutoring_requests` for bounded concurrent actual tutoring POSTs.
   Record p50/p95, failure slices, actual calls/tokens/cost and independent answer
   quality. Cheap course-list GET timing cannot replace this measurement.
5. Inject provider failure and restart during a bounded journey, then verify
   recovery and compare with the retained control. Do not claim no downtime.

These future deployment/model-backed steps are not marked passed by this note.
No schema18 recovery defect was found; no runtime/core code changed in this pass.
