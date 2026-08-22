# Evidence-sufficiency v2 independent-review 004 build result

## Decision

**Go Deeper with the native OpenRouter transport; keep provider execution and
the decision dataset closed pending separate authorization.**

Review 004 replaces the opaque wrapper boundary exposed by invalid review 003
with OpenRouter's documented native chat-completions API. This is transport and
orchestration-readiness evidence only. No provider inference, private source,
held-out case, dataset freeze, candidate evaluation, or product selection
occurred.

## Bound implementation

- Implementation revision: `36e73592e75aed4b1db54d55beaff8f654d68885`
- Instrument: `evidence-sufficiency-v2-independent-review-004`
- Instrument SHA-256:
  `f06ccb89084501e9c90e9b88efeb563470a0f224a49a1f117f8540da6dae957c`
- Review-packet content SHA-256:
  `75fc54d28a708df7a36150f0519db6eb7429b6e625ebbde7feceecfa817f8fbd`
- Runner SHA-256:
  `b62203a3926635a0db922e9860dcf9f056cb1e098691c657c80d8173fe30b685`
- Network-free simulation SHA-256:
  `7f4b3b5042676b190cbbab1564d40ff659934774657fa4f879846f13720ca6c1`
- Private or held-out data read: zero
- Provider/model inference calls: zero

Historical instruments and invalid results 002 and 003 remain unchanged and
loadable.

## Official OpenRouter contract

The runner now calls `POST https://openrouter.ai/api/v1/chat/completions`
directly with a bearer credential, exact model slug, strict JSON Schema,
top-level provider routing, requested usage accounting, and
`X-OpenRouter-Metadata: enabled`. Routing remains restricted to first-party
Mistral, with fallback disabled and parameter support required.

The implementation follows OpenRouter's official
[quickstart](https://openrouter.ai/docs/quickstart),
[chat-completions API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request),
[structured-output](https://openrouter.ai/docs/guides/features/structured-outputs),
[provider-routing](https://openrouter.ai/docs/guides/routing/provider-selection),
and [router-metadata](https://openrouter.ai/docs/guides/features/router-metadata)
documentation. The wrapper used by review 003 remains available only for
historical compatibility.

## Failure observability

Every native failure preserves a sanitized HTTP status, OpenRouter error code
and message, request ID, generation ID, and router-attempt metadata when
provided. Credentials and unrestricted response content are never logged.
Network-free regression tests prove that an upstream 401 remains distinguishable
from a local wrapper exception and that no bulk batch can follow a failed
sensitivity call.

## Prospective boundary

- Reviewer: exact `mistralai/mistral-small-2603` through OpenRouter.
- Inputs: the unchanged synthetic-public 120-case draft only.
- Work: one sensitivity-first call, followed only on sensitivity success by at
  most 12 ten-case batches.
- Maximum: 13 calls, zero retries, USD 0.0702 reserved estimate, and USD 0.50
  emergency ceiling.
- State: `reviewer-bound-provider-unauthorized`; the instrument is not frozen,
  is absent from the bounded allowlist, and cannot execute.

## Verification

- Network-free simulation: 13/13 calls and 132/132 judgments completed.
- Simulated sensitivity: 6/6 clean controls and 6/6 defect controls handled as
  expected; all deterministic orchestration gates passed.
- Focused regressions cover the official request shape, sanitized native
  provider failures, strict schema, sensitivity stopping, malformed responses,
  provider/model identity and cost failures, atomic accounting,
  interruption/resume, binding drift, and exclusive output creation.
- Complete repository gate: 795 Python tests and 46 frontend tests passed,
  together with documentation checks, frontend lint, and production build.
- Repository correctness inventory: 488/488 audited; execution-freeze coverage:
  61/61 protected entrypoints.

## Clean live no-call preflight

At 2026-08-22 17:32 SGT, OpenRouter metadata still exposed the exact model and
an active first-party Mistral endpoint with a 262,144-token context window,
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
that changes only the three correlated locks, refresh official metadata, and
run review 004 once. Any provider, identity, sensitivity, or operational
failure must stop the bulk batches and remain registered. Dataset adjudication,
correction, freezing, candidate evaluation, component selection, and release
remain later gates.
