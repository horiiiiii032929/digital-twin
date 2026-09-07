# Completion implementation audit

This records the scope of the September 6 correctness-inventory refresh.
Review covered the changed regions and new files, with the existing audit
retained for unchanged files. An audited development implementation is not a
claim that its model behaviour meets the project's quality gates.

## Reviewed groups

- Ingestion, publication and dashboard: permission-reviewed text/Markdown,
  source checksum propagation, schema-18 persistence, release/window-scoped
  active-learner counts, small-group suppression, and persistent instructor
  decisions. Review includes the UI's course-switch and autonomy-state fixes.
- Reactive and autonomous context: exact approved profile/course/hash binding,
  opt-in factory wiring, prompt-history actions, question-specific support
  proposals, explicit question and hint rendering, and unchanged application
  authority over policy, evidence and delivery. Semantic relevance, hint
  partiality and pedagogical progression remain measured limitations.
- Persistence: nonblocking SQLite transaction attempts yield to the asynchronous
  checkpointer; each retry rolls back and rechecks authority. Tests exercise a
  real held checkpoint commit, withdrawal, duplicate request convergence and a
  finite storage-busy outcome. Model generation is not repeated by storage retry.
- Provider transport and budgeting: one schema registry drives requests and
  validation; diagnostics omit rejected text. Bounded concurrency reserves
  conservative cost before dispatch and handles cancellation, unknown costs,
  mixed estimate availability and ceiling violations. Serial behaviour remains
  the default. The reservation relies on the bounded text-only request and the
  configured provider pricing/cap assumptions, not a guarantee of future bills.
- Evaluation runners: exclusive outputs, scoped execution guards, actual model
  identity and conservative run budgets, source/configuration hashes, raw
  response ledgers, and explicit distinctions between fake contracts,
  operational trials and pedagogical assessment. Known label/scorer limitations
  and unsuccessful runs remain recorded.

## Verification basis

The initial full Python run had 2,063 successful tests and two new-runner
execution-registry failures; those guards and registry entries were corrected.
Subsequent focused suites include 766 API/service/domain/concurrency tests,
56 frontend tests with lint/build, evaluator contracts, provider-envelope tests,
and live development evidence. These counts describe specific runs, not a sum
of unique independent cases. The final unified check is reported in
[completion status](../project-completion-status.md).

The additional
`tests/api/test_candidate_ingestion_composition.py` journey uses the actual
opt-in application factory, product upload, profile approval, release publication,
explicit course-model approval, cited tutoring and withdrawal. Its structured
provider is deterministic, so it verifies composition rather than model quality.

## Limits

The default selected release profile was not replaced. Source-contained text
can still be incomplete or pedagogically poor; the finite Luna/Terra comparison
does not justify a model upgrade. Concurrent ASGI route tests omit deployment
middleware and distributed infrastructure. Synthetic virtual-day experiments
do not establish real learning, authentic instructor fidelity or uptime.

The machine-readable correctness audit binds each refreshed file to its current
hash and group-specific review evidence. Future changes must invalidate that
binding rather than inheriting an earlier review automatically.

Final verification: `npm run check` exited 0, including 2,085 configured Python
tests, 56 frontend tests, validators, frontend lint and production build. Existing
historical-artifact exclusions remain unchanged. Detailed scope and non-fatal
warnings are recorded in the completion status; these test passes do not qualify
the model's teaching quality or the latency target.
