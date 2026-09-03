# Successor architecture engine comparison 006 post-run audit

- **Status:** `completed-keep`
- **Finding:** `SE6-6`, closed.
- **Decision:** preserve the E1 component result and fix the shared trace clock before whole-system confirmation.

The independent ledger recheck confirmed 1,200 unique allocation/case cells,
two recorded generator fallback cells, no planner failures, and unchanged
provider accounting. It also found that all 1,200 sanitized graph traces mixed
the process wall clock for `started_at` with the injected virtual clock for
`completed_at`, so completion appeared to precede start.

The timestamps were not inputs to policy utility, allocation hard gates,
response validation, provider accounting, or hidden gold. The E1 selection is
therefore retained as component evidence with the limitation disclosed. The
root cause is closed prospectively: both graph implementations now use one
injected job/event clock, and `AgentTraceV2` rejects invalid, timezone-naive,
or reversed timestamps. Historical provider outputs, responses, metrics, and
the decision remain unchanged.
