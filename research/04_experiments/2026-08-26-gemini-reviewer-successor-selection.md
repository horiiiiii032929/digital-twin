# Gemini reviewer successor selection

Status: **Prospective default; build and paid execution unauthorized**

Verified at: `2026-08-26T05:00:28Z`

Owner issue: [#127](https://github.com/horiiiiii032929/digital-twin/issues/127)

## Decision question

Which inexpensive model and transport should replace Mistral Small 4 after two
independent first-batch operational failures, while retaining reviewer-family
diversity and an auditable structured-output contract?

## Recommendation

Use OpenRouter `google/gemini-3.7-flash`, exact documented revision
`google/gemini-3.7-flash-20260813`, as the prospective third-family reviewer.
Pin a Google-operated endpoint, require every request parameter, prohibit
cross-vendor fallback, and record the returned provider/model identity. Keep
DeepSeek V4 Pro as the other provider reviewer and reuse the immutable 40/40
Codex calibration votes.

This selection is prospective. It does not authorize a canary, calibration,
200-case panel, visual run, product run, or later academic tranche.

## Current external evidence

The live OpenRouter registry reported:

- Gemini 3.7 Flash: 1,048,576-token context, 65,536-token maximum completion,
  structured outputs, and current model-level prices of USD 0.375/M input and
  USD 1.875/M output tokens.
- The public model page reported 100% three-day uptime and 99.90% three-day
  availability. The Google AI Studio endpoint reported 99.9768% uptime over
  its live 30-minute window when checked; this short-window observation is
  operational context, not a durable quality claim.
- Gemini 3.6 Flash supports the same relevant parameters but costs USD 0.75/M
  input and USD 3.75/M output. It is retained only as a fallback candidate.
- Qwen3.7 Plus is cheaper and operationally available, but repository
  qualification 007 already rejected it on the frozen quality gates. It must
  not be silently reused because its public uptime is favorable.
- Kimi K2.5 has several viable endpoints but no project-specific reviewer
  calibration, and structured-output support differs by endpoint. It remains a
  backup research candidate, not the default.

The Gemini 3.7 prices are currently promotional and may change. Every paid
preflight must refresh model, endpoint, pricing, parameter, routing, and
retention metadata within 24 hours and recompute the reservation.

## Transport correction

The two Mistral failures do not prove poor reviewer quality because neither run
accepted a provider vote. The immediate HTTP 400 in attempt 002 is consistent
with a request-contract rejection. The exact rejected field is unknown because
the durable sanitized error intentionally excludes unrestricted provider text.

Google documents support for a subset of JSON Schema. The current reviewer
schema includes `uniqueItems`, which is not listed in that supported subset.
Therefore schema incompatibility is a plausible cause, not a confirmed cause.
The successor must:

1. remove unsupported provider-side constraints such as `uniqueItems`;
2. retain only the documented structured-output subset in the request;
3. validate exact IDs, field sets, uniqueness, coverage, claims, citations, and
   semantic invariants deterministically after parsing;
4. use the first four-control batch as the no-retry transport canary;
5. fail closed on HTTP error, identity drift, malformed JSON, schema drift,
   incomplete usage/cost accounting, or an unmet calibration gate.

This changes only the reviewer transport and model binding. It does not change
the deterministic truth, cases, controls, gates, or product method.

## Cost bound

At the current model-level prices and the frozen maximum of 8,192 input plus
3,072 output tokens per call:

- Gemini maximum reservation is USD 0.008832 per call;
- ten Gemini calibration batches reserve USD 0.08832;
- ten DeepSeek calibration batches retain their existing USD 0.229786 maximum;
- total 40-control provider calibration reservation is approximately USD
  0.318106 before any pricing change.

A later complete calibration-plus-200-case panel would reserve approximately
USD 1.91 at current prices. This is informational only. The emergency stop and
reservation must be recomputed after the mandatory live metadata refresh.

## Evidence and claim boundary

The completed 10,000-row result in issue #110 remains engineering-scale
evidence. It does not become an academically independent 10,000-case product
evaluation by changing the reviewer. The academic progression remains valid
reviewer calibration, leakage-free 200-case product confirmation, and a later
600-case cluster-independent tranche. Any genuine 10,000-case end-to-end
product evaluation would require its own independently justified sampling and
execution protocol after these gates pass.

## Sources

- [OpenRouter Gemini 3.7 Flash model page](https://openrouter.ai/google/gemini-3.7-flash)
- [OpenRouter live model registry](https://openrouter.ai/api/v1/models)
- [OpenRouter Gemini 3.7 endpoint registry](https://openrouter.ai/api/v1/models/google/gemini-3.7-flash/endpoints)
- [OpenRouter structured-output documentation](https://openrouter.ai/docs/guides/features/structured-outputs)
- [OpenRouter provider-routing documentation](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Google Gemini structured-output documentation](https://ai.google.dev/gemini-api/docs/structured-output)
- [Repository Qwen qualification 007 result](../05_evaluation/factual-qa-v3-reviewer-qualification-007-results.md)
- [Invalid Mistral attempt 002](../05_evaluation/academic-factual-qa-confirmation-002-calibration-attempt-002-invalid-results.md)
