# Evaluation result: deployable-product-foundation-v7-post-correctness-requalification-001

## Run identity

- Component: post-correctness deployment workflow and current-tree package
- Date: 2026-08-21
- Clean implementation revision: `f553be5f9fa6288514e091b3f9e062e7e1afdbda`
- Candidate: `a1-single-node-staging-v7-post-correctness`
- Control: historical V5 local/container package
- Data: synthetic accounts, one course, one generated PDF, one release,
  conversation, answer, citation crop, backup, and restored state
- Boundary: no private or held-out data; zero model/provider calls; USD 0
- Generated in-process result:
  `reports/generated/deployable-product-foundation-v7-post-correctness-requalification-001/result.json`
- Generated result SHA-256:
  `1500c5cdc75c32337cf9cfb56cf0a5a7d068c048d7e32e23e5a52210b6565655`

## Decision question

Does the repository-corrected code still complete the credentialed
professor-to-student release workflow and recovery boundaries, and can it
replace suspended V6 as the current-tree deployment checkpoint?

V5 remains the historical container control. V7 must use the current
onboarding and publication contracts: bind setup to the course before final
review, resolve policy before preview acceptance, give professor approval last,
and create staging releases only from server-owned completed ingestion jobs.

## Findings and corrections

The first current-tree run returned `Refine` after only 10 recorded checks. The
runner hid the exception stage and still followed three superseded product
contracts. Review found and corrected:

1. unresolved knowledge-source policy was submitted as resolved;
2. preview decisions were made before policy/checklist changes that correctly
   invalidated them;
3. the onboarding session was approved before course binding, which correctly
   revoked the approval;
4. browser-returned chunks were submitted to staging instead of server-owned
   ingestion job IDs; and
5. exception records omitted the failed stage and safe diagnostic code.

The production safeguards were retained. Both in-process and HTTPS verifiers
now follow the product workflow instead of bypassing it, and the complete
in-process journey is part of the normal test suite.

## In-process result

The clean V7 run passed 42/42 gates:

- credentialed administrator, professor, and student sessions;
- professor course creation, student assignment, course-bound setup, policy
  approval, source upload, idempotency, worker completion, and lineage;
- deterministic preflight, publication, student isolation, persistent
  conversation, grounded answer, original-region citation, and crop access;
- restart durability, checksum-valid schema-v8 backup/restore, and A0 demo
  rollback;
- 100/100 capacity requests with zero errors;
- API p50/p95 of 2.717/3.073 ms against the 750 ms local gate;
- 52.342 ms queue-to-ingestion completion;
- 326,090,752 bytes peak RSS against the 4 GiB envelope; and
- zero provider calls and USD 0 external cost.

Focused release regressions passed 68/68, the complete repository gate passed
after adding the 42-gate test to the suite, the 463-file correctness inventory
is complete, and Python/JavaScript dependency audits report zero known
vulnerabilities.

## Container leg

The current image build is **not claimed**. Docker Desktop was initially
stopped, then reported Engine 28.5.1 after startup. The isolated
`digital-twin-v7` build made no progress while resolving the pinned Docker Hub
and GHCR base-image metadata. Host HTTPS probes reached both registries, but a
direct pinned Docker pull also stalled. A bounded Docker restart did not return
a healthy engine. The attempts were stopped without starting containers,
creating V7 runtime volumes, or changing existing state.

Historical V5 image and live-HTTPS evidence remains valid only for its frozen
revision. It is not promoted to current V7 evidence. Current V7 image build,
live HTTPS, restart, clean restore, and original-volume rollback remain open.

## Decision

- Outcome: **Go Deeper** for the current in-process package.
- Keep the four verifier corrections and make the 42-gate journey a permanent
  regression.
- Supersede the broad V6 correctness-audit suspension with a V7 current-tree
  freeze that explicitly withholds container and release claims.
- Do not claim a hosted release candidate until the current images build and
  pass live HTTPS/recovery on localhost and then on the selected public host.

## Limitations and next gate

This is synthetic single-process evidence on one development machine. It does
not establish current container compatibility, trusted public TLS, target-host
restore, real-source multimodal quality, Professor Digital Twin fidelity,
human usability, learning outcomes, or an SLA. Retry the isolated container
qualification after Docker registry/runtime health is restored; any failure is
registered against the V7 container successor rather than hidden.
