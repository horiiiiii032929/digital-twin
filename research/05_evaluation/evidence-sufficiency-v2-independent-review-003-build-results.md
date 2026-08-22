# Evidence-sufficiency v2 independent-review 003 build result

## Decision

**Go Deeper with the strict-schema successor; keep provider execution and the
decision dataset closed pending separate authorization.**

This checkpoint repairs the execution harness exposed by invalid attempt 002.
It is orchestration-readiness evidence only: no provider inference, private
source, held-out case, dataset freeze, candidate evaluation, or product
selection occurred.

## Bound implementation

- Implementation revision: `18f593822a16202974bb6c013e37f4ba4808e24d`
- Instrument: `evidence-sufficiency-v2-independent-review-003`
- Instrument SHA-256:
  `76eff8594df00bf2ea53de6317a36a028c8ef92edfd4eed3bfe8f7ff69eb4123`
- Review-packet content SHA-256:
  `90c177ae9dc158396af0e7be6bc393cc894b8f1b6cc278648682a86c9906215b`
- Runner SHA-256:
  `4131f87b10049312974ed54d7ea119070a9918c9c5144b85187ee563b31e42dc`
- Private or held-out data read: zero
- Provider/model inference calls: zero

Historical instrument and invalid result 002 remain unchanged and loadable.

## Prospective boundary

- Reviewer: exact `mistralai/mistral-small-2603` through OpenRouter, restricted
  to first-party Mistral routing with fallback disabled.
- Output: per-call `json_schema` response format with `strict: true`; endpoint
  routing requires every requested parameter. Response healing is disabled so
  a provider contract failure remains observable.
- Evidence preservation: malformed response content, parser detail, provider
  identity, token use, latency, and cost are checkpointed before stopping.
- Inputs: the exact synthetic-public 120-case packet only; no Academia Vault or
  private course material.
- Work: one sensitivity-first call, followed only on sensitivity success by at
  most 12 ten-case batches.
- Maximum: 13 calls, zero retries, USD 0.0702 reserved estimate, and USD 0.50
  emergency ceiling.
- State: `reviewer-bound-provider-unauthorized`; the instrument is not frozen,
  is absent from the bounded allowlist, and cannot execute.

OpenRouter documents that strict structured output is requested through
`response_format.type = json_schema`, that support is endpoint-specific, and
that `require_parameters: true` restricts routing to compatible endpoints:
[structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
and [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).

## Verification

- Network-free simulation: 13/13 calls and 132/132 judgments completed.
- Simulated sensitivity: 6/6 clean controls and 6/6 defect controls handled as
  expected; all deterministic orchestration gates passed.
- Focused regressions cover strict schema construction, historical 002
  compatibility, sensitivity stopping, malformed/provider/model-identity and
  cost failures, atomic accounting, interruption/resume, binding drift,
  metadata expiry, model/endpoint pricing and context drift, endpoint
  structured-output support, and exclusive output creation.
- Complete repository gate: 792 Python tests and 46 frontend tests passed,
  together with documentation checks, frontend lint, and production build.
- Repository correctness inventory: 487/487 audited; execution-freeze coverage:
  61/61 protected entrypoints.

## Clean live no-call preflight

At 2026-08-22 16:23 SGT, OpenRouter metadata reported the exact model and an
active first-party Mistral endpoint with a 262,144-token context window,
structured-output support, and prices of USD 0.15/M input and USD 0.60/M
output. The preflight found the credential present without emitting it, a clean
worktree, an unused output path, maximum planned input of 7,374 tokens, and no
provider metadata failures.

The status was `blocked-not-authorized` with exactly three intentional locks:

1. `provider-review-not-authorized`;
2. `instrument-not-frozen`;
3. `bounded-freeze-authorization-missing`.

## Next gate

If the researcher chooses to proceed, create a separate authorization commit
that changes only the three correlated locks, refresh live metadata, and run
review 003 once. Any sensitivity or operational failure must stop the bulk
batches and remain registered. Dataset adjudication, correction, freezing,
candidate evaluation, component selection, and release remain later gates.
