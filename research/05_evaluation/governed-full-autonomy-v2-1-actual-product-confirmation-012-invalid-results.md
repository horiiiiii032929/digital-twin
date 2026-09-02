# Governed full-autonomy V2.1 confirmation 012 — invalid execution

## Outcome

`invalid-execution`. All 820 fresh, source-disjoint actual-product responses were durably persisted, but aggregate scoring failed before a quality decision with `ZeroDivisionError`.

## Root cause

The scorer identified long-horizon and proactive cases through legacy case-ID prefixes. The release confirmation intentionally renamed every case with a `release-fresh-` prefix, so the scorer selected zero proactive cases and divided by zero. Product execution, provider transport, hidden-gold ordering, and response persistence were not the cause.

## Accounting

- Responses: 820/820
- Provider calls: 1,555
- Input/output tokens: 837,195 / 180,334
- Reported cost: USD 3.838398
- Hidden gold: opened only after all 820 responses were durable

## Decision

Preserve this invalid result. Apply one scorer-only correction that classifies proactive cases from the stable public event contract (`practice-outcome`), requires exactly 220 such cases during simulation, and rescores the immutable responses without another provider call. Cases, responses, models, prompts, product behavior, and hard gates remain unchanged.
