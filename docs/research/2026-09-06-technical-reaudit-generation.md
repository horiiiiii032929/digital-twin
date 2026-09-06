# Generation, grounding and provider technical re-audit

6 September 2026. Independent bounded review within the user-authorized repository audit. Read root `AGENTS.md`; preserved existing dirty changes. No provider calls, sealed-data inspection, semantic evaluation reruns, experimental promotion or runtime-default change.

## Findings and fixes

1. **Serial requests bypassed an available cost ceiling.** `BudgetedLlmClient.chat` selected the legacy post-hoc accounting path whenever concurrency was one, even if the transport advertised `conservative_request_cost_usd`. With a $0.30 budget and $0.20 ceiling/actual cost per request, two sequential requests were admitted and charged $0.40. Fixed dispatch so every ceiling-capable transport uses reservations; a semaphore of one still serializes calls. The second request is now rejected before transport dispatch. Existing cancellation/in-flight reconciliation changes were retained.
2. **Call limits accepted fractional and non-finite values.** `max_calls=1.5`, NaN and infinity passed construction; the string case raised an incidental TypeError. NaN/infinity can defeat the call-count comparison. Require a positive integer, excluding bool. Parameterized regressions cover these values.
3. **LiteLLM fabricated observed identity when missing.** A response with missing/None/empty `model` was assigned the requested model, then passed identity verification. The adapter now uses the observed value only; absent/blank identity is rejected by the existing identity-drift boundary. Injected tests demonstrate the missing/empty failures and retain whitespace rejection. Existing strict OpenAI observed-identity handling was preserved.
4. **Provider output caps accepted non-integers.** Both OpenAI Responses and LiteLLM constructors accepted fractional/NaN/infinite caps that cannot represent valid bounded token counts. Both now require positive integer caps, excluding bool. Tests include fractional, NaN, infinite and string inputs for both adapters.

Changes are confined to `services/llm/budget.py`, `services/llm/litellm_client.py`, the integer guard in `services/llm/openai_responses_client.py`, and the corresponding service tests. No prompt/schema/model efficacy changes were made.

## Review coverage and observations

Read the admission/reconciliation/snapshot paths in `services/llm/budget.py`; Responses configuration, serialization/cost ceiling, identity, usage and schema-error paths; LiteLLM configuration, request/identity/usage paths; and `services/llm/experimental_role_routing.py` task/role restrictions. Inspected generation/grounding boundaries in `generation/{models,policy,typed_instruction,compact_instruction,citations,generator,final_response_audit}.py`, `grounding/{models,claim_validation,semantic_evidence_atoms}.py` and the generation-selection sections of `services/api/app/factory.py`.

Factory inspection confirms experimental typed/conditional generation remains explicitly enabled; ordinary settings select the evaluated profile/deterministic path. Searches found no final-response-audit, V15 global-support or V16 action-scoped integration in API/student runtime. Final-audit V1/V2 remains an experiment. Existing validators enforce source ID/lineage and typed response shape; these checks do not prove natural-language entailment, complete claim extraction or pedagogical usefulness. Prior failed final-audit results remain failures.

The `display_allowed` flag is used to suppress source crops in citations; it is distinct from tutoring/retrieval permission. No unsupported blanket change to that permission meaning was made. Existing semantic-atom relation groups are contextual/adjacency metadata, not formal logical rules.

Known limit: transports without a conservative request ceiling retain the existing serialized, post-hoc budget behavior, including possible single-call cost overshoot. This audit fixes the erroneous bypass when a ceiling is available; it does not invent a bound for unpriced legacy transports. Unknown costs block future admission. Complete repository/all-input correctness is not established by this bounded review.

## Verification

Before the budget fix, five targeted cases failed in `/tmp/generation-reaudit-repro.log`. Before the LiteLLM identity fix, missing/empty identity cases failed in `/tmp/generation-identity-repro.log` (whitespace already failed closed).

Command:

```sh
.venv/bin/python -m pytest -q tests/services tests/digital_twin/test_claim_validation.py tests/test_final_response_audit.py tests/test_final_response_support_audit_runner.py
```

Result: **213 passed**, six existing dependency/intentional backup-fixture warnings, log `/tmp/generation-reaudit-tests.log`. This includes provider adapters, budgets, persistence services, atomic-claim validation and both final-audit contracts. Ruff passed for the five changed Python files. Root coordinates full-repository checks after parallel edits settle; no duplicate paid evaluations are required for these transport/configuration fixes.

## Nested-preview regression follow-up

The initial reservation fix exposed a capability-advertisement mismatch in generated previews: a nested `BudgetedLlmClient` always exposes a ceiling method, even when its underlying injected/legacy transport has no estimator. The outer wrapper therefore rejected the parent's `None` before any call. Reproduced through the generated-preview tests and fixed by propagating fixed estimator absence through budget-wrapper nesting. This is not a general fallback for a real advertised estimator returning `None` on one task: that case remains rejected. Added regressions for legacy nested accounting/call caps and a genuine nested estimator whose outer budget must block admission.

Follow-up command: `.venv/bin/python -m pytest -q tests/services/test_llm_budget.py tests/services/test_llm_concurrent_budget.py tests/test_generated_professor_preview.py`. Result: **67 passed**; Ruff clean. Log `/tmp/generation-nested-budget-tests.log`. All generated-preview cases now pass without weakening actual bounded-provider reservations.

## Operational metrics regression follow-up

The full repository check exposed a second interaction: the longitudinal runtime directly constructs strict `AutonomyProviderCallV1` records from budget snapshots. Calls actually ran, but metrics export rejected `reserved_cost_usd` and `reservation_exceeded` as extra fields. The pilot traceback is retained in `/tmp/debug_operational_budget.log`; this was an export failure, not a zero-call provider failure.

Added optional finite/non-negative reservation cost and strict Boolean overrun fields to `src/digital_twin/evaluation/autonomy_contract.py`. Absent legacy fields remain omitted in serialized records; actual reservation evidence is retained. Inspected both exporters (`final_profile_longitudinal_runtime.collect_metrics` and `governed_full_autonomy_v2_1_actual_product_runtime._metrics`), which now accept these records without changes. Tests reject negative/NaN/infinite reservations and verify legacy absence.

Also corrected the reservation-path failure record for an otherwise successful response with unknown or excessive cost: it now carries the budget-exceeded error code instead of `None`, allowing the strict failed-call contract to record the rejection. Injected tests cover both unknown and over-reservation costs.

Command: `.venv/bin/python -m pytest -q tests/test_operational_dialogue_development.py tests/test_final_profile_longitudinal_runner.py tests/test_instructional_operational_comparison.py tests/test_autonomy_evaluation_contract.py tests/services/test_llm_concurrent_budget.py`. Result: **69 passed**; Ruff clean. Log `/tmp/operational-budget-fixed-tests.log`. No changes to inventories or paid evaluations.
