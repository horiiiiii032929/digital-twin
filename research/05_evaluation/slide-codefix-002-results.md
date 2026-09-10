# Evaluation result: slide-codefix-002

## Run identity

- Component: audit input failure accounting and schema diagnostic transport.
- Status: completed local validation; not deployed at user request.
- Date/owner: 10 September 2026 Singapore time, Codex with user authorization.
- Revision: `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty; exact source hashes
  are in the [machine record](records/slide-codefix-002.json).
- Environment: locked Python dependencies through uv; synthetic provider transports.
- Artifacts: `output/browser-qa/slide-codefix-002/`.
- Predecessor: [slide-codefix-001](slide-codefix-001-results.md).

Reproduce the exact audit control comparison with the retained deployed source:

```sh
uv run python -m scripts.verify_slide_codefix --control infra/cdk/cdk.out/asset.47bdf176a935ba44e6d33c0417079155fd5e41be75259c79942573db8793aa92/src/digital_twin/generation/final_response_audit.py --output output/slide-codefix-002-comparison.json --run-id slide-codefix-002 --dataset decision-preserving-codefix-v1
uv run pytest -q tests/test_audited_instruction_generation.py tests/test_final_response_audit.py tests/test_contract_repair_generation.py tests/services/test_openai_responses_client.py tests/digital_twin/test_governed_autonomy.py tests/api/test_pilot_app.py
uv run pytest -q tests/api tests/services
uv run pytest -q tests/digital_twin
npm --workspace apps/web test
```

## Decision context

The user prohibits changes to app decisions. The
[prospective plan](../04_experiments/2026-09-10-decision-preserving-codefix-plan.md)
therefore allows only accounting/diagnostic repairs. Control is the deployed dirty
manifest, retained before staging. Prediction: same action, text, citations, provider
requests and call limits; only already-incurred usage and bounded error metadata
are repaired. Alternatives are retaining missing metadata or passing sanitized
metadata through the existing exception path. No algorithmic replacement is proposed.

## Data and sample size

`decision-preserving-codefix-v1` uses the existing 18 synthetic audit cases plus
new regressions for failed history preparation, schema field transport, privacy,
invalid diagnostic structures and bounded lengths. Fixtures are defined in
`tests/test_final_response_audit.py` and `tests/test_audited_instruction_generation.py`.
The machine record retains all 18 per-case control comparisons. Test inputs contain
synthetic private sentinels, never real learner/source data. These are deterministic
contract tests without training or held-out splits, stochastic seeds or semantic
judges. Sample size covers the identified branches; it is not a reliability estimate.

## Exact configuration

Exactly two runtime files changed: `audited_instruction.py` and
`final_response_audit.py`. The first retains completed draft usage when audit-input
preparation raises the same ValueError previously classified as malformed output.
The error remains a malformed-response failure with the same public message.
The second records up to four canonical schema locations/error types, each with at
most six path components. Only declared field names, bounded indexes and known error
categories are allowed. Unknown names become `_`; raw inputs and exception prose
are excluded. The public trace revalidates these canonical identifiers.

The 70-slide contract, all prompts, model roles/reasoning, schemas/validators,
audit/repair limits, release profiles, state transitions, assessment and outreach
rules remain unchanged. No provider calls were added, and no provider budget was
reset for testing. The metadata correction does not alter the provider client's
existing accounting or admission decisions.

## Aggregate results

| Check | Result | Gate |
| --- | --- | --- |
| Original audit controls | 18/18 exact prior outputs, requests, call counts and usage | Pass |
| Focused components/provider/governed runtime | 145 passed | Pass |
| All API/service tests | 327 passed | Pass |
| All domain tests | 612 passed | Pass |
| Frontend tests | 89 passed in 18 files | Pass |
| Infrastructure checks through npm check | 7 passed | Pass |
| Repository-wide npm check | Stops at existing two presentation links | Blocked |

The focused suite overlaps the broader suites; do not sum these rows as unique
coverage. The earlier narrower API run also passed 114 tests. No frontend source
changed; prior lint/build results remain applicable, and frontend tests were rerun.

## Slice results

| Slice | Expected and observed |
| --- | --- |
| Invalid audit history after draft | One provider call; same safe failure text/action/no citations; 20 injected tokens and $0.0001 preserved. |
| Local schema errors | Known field paths preserved; unknown field names hidden. |
| Provider schema errors | Existing transport locations survive into final failure trace; invalid output still withheld. |
| Privacy/bounds | Private sentinels omitted; oversized/invalid metadata rejected or bounded. |
| Normal/repair/rejection controls | All 18 original decisions and calls unchanged. |

## Hard gates

Unvalidated output remains withheld. The accounting fixture has the exact same
failure message and action before/after, and still makes one draft call with no audit
or repair call. The schema propagation fixture still fails after two calls, retaining
27 injected tokens without double counting. Successful and rejected audit controls
match the deployed implementation exactly. No application decision-changing patch
was accepted. Source hashes are recorded for later deployment verification.

## Operational results

Real provider calls/tokens/cost for this run: zero. Test usage is injected, not billed.
The focused suite completed in 6.09 seconds, broad API/services in 18.44 seconds,
domain in 14.20 seconds, frontend in 0.809 seconds. Per-case comparison latency is
in the machine record; no latency improvement or memory performance claim is made.
A local test invocation exited 120 with an empty log while disk space was low.
Unused Docker build cache older than an hour was reduced with a 5 GB retention target,
reclaiming 2.893 GB of reproducible cache; tests then ran successfully. No runtime
images, application volumes or backups were deleted by this cleanup.

## Failures and surprises

1. Before repair, the targeted accounting regression failed: 0 saved tokens rather
   than the 20 from the completed draft. This is a reproduced integration/accounting
   bug in the invalid-history path; it is not established as the cause of prior live
   provider failures. `before-accounting.log` retains the failure.
2. The first combined run had 144 passes and one test failure because the new test
   incorrectly assumed Pydantic's error ordering. Both correct fields were present.
   The assertion was corrected to compare the set; runtime code was unchanged.
   `component-tests.log` and `component-tests-final.log` preserve both attempts.
3. `npm run check` still rejects the two pre-existing absolute Desktop presentation
   links. The actual files were previously inspected; this is not proof they are
   missing. Later stages of that command do not run after the link failure.
4. The prior live provider schema failures remain unresolved. This local run does
   not manufacture a live rejected field or change validation to accept bad output.

## Validity review

No real provider quality claims or sealed comparisons are made. Synthetic controls
check code behavior only. The erroneous ordering assertion is documented and corrected;
no unfavorable runtime result was discarded. The final local result is valid for its
bounded metadata scope. The user redirected deployment/live work to local testing.

## Decision

Keep the two coding fixes locally; no profile change. Retain the deployed version
until the user requests AWS resumption. Same fallback, same app decisions.
See [the AWS pause record](../../reports/aws-pilot/pause-2026-09-10.md): EC2 is stopped,
automatic starts are disabled, and network deletion is a separate pending choice.

## Limitations and follow-up

This does not prove live model reliability or every lifecycle scenario. No new browser
session or real provider run was required for these backend metadata changes; the
previous live evidence remains authoritative for its own run. When cloud work resumes,
inspect the bounded schema field diagnostics before proposing any further coding fix.
Do not change prompts, validators or model decisions to lower failure counts.

## Learning notes

A rejected answer and a lost accounting record are different defects. Keeping the
same rejection while preserving incurred usage fixes bookkeeping without changing
what the tutor decides. Bounded schema paths make the next investigation more precise
without retaining private model text.
