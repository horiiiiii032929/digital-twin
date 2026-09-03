# Successor architecture fold 002 — invalid corrective attempt

The sole corrective execution is `invalid-execution`; fold 002 is closed
without an architecture selection.

- All 238 required provider calls completed successfully with exact Luna
  identity, zero retries, 111,283 input tokens, 48,693 output tokens, and
  USD 0.0806882.
- The reason-code boundary correction worked and did not recur.
- All 150 deterministic A cells were persisted. The first provider-backed B
  cell then failed because the isolated graph database contained LangGraph
  checkpoint tables but not the product `autonomous_model_calls_v2` migration.
- Hidden gold remained unopened; no paired metric was calculated.

This is a second harness defect, not a valid architecture-quality failure.
Authority is revoked, the partial output cannot be resumed, and no third
same-fold attempt is allowed. The database-initialization defect will be fixed
and regression-tested before a fresh, source-disjoint architecture round.
