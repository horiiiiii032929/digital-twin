# Explicit experimental worker composition

Prospective design, 2026-09-06, before executable changes. Decision question: does an explicitly selected experimental API have a worker using the same algorithm, role models, reasoning and cap? The current worker always calls the incumbent create_app; therefore API-only selection is insufficient for a usable autonomous composition.

Keep no-selector create_app unchanged. When APP_EXPERIMENTAL_TUTORING_CANDIDATE is explicitly nonempty, call the shared build_experimental_app(settings, candidate, serve_web=False). Do not duplicate selector flags or model mappings. Existing staging/worker-enabled guards remain. Unknown selectors and conflicting settings fail before processing jobs. Expose/inspect the same experimental configuration as the API; this is a local process configuration, not a persisted global deployment lock. API and worker must receive the same environment and database configuration; budgets are per process, not a shared global cap.

Tests before use: default path retained; invalid selector/settings fail closed; real builder binds implementation/model roles exactly; _process_once processes an actual persisted due job under the selected configuration and retains actual output/records; serve_web is false; no indefinite polling in tests. No algorithm, policy or queue scheduling change. Injected transports give repeatable zero-network evidence. Any later provider QA is separately bounded to --once with a finite due-job batch after candidate acceptance.

Document explicit same-selector startup commands and retain the original worker command. Success is configuration and persisted-job integration, not factual correctness, intervention utility or background-worker global-budget qualification.

## Implemented contract checks

The worker and operational reply-audit tests passed with the freeze validator (20 tests). The persisted-job test opens the selected real application on a pre-seeded SQLite database, invokes `_process_once`, verifies the selected planner is called and that the job leaves pending with an action record. Its injected planner behavior is not a live delivery or semantic-quality claim. Additional actual provider-construction checks for all three role aliases caught Sol's inactive-release constructor restriction before network dispatch; the model-comparison owner is addressing explicit experimental admission while retaining release defaults. Final alias tests must pass before a source freeze.

The reporting correction applies prospectively to `audit_history_output`: only `proactive-reply` rows count as outreach replies, and their top-level delivered IDs must exist in delivered outreach records. Tests distinguish reactive replies and reject missing/dangling outreach links. The previously recorded V10 raw summary and source snapshot remain unchanged; its durable result retains the derived two-link correction.
