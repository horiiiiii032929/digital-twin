# Evaluation result: governed-full-autonomy-v2-1-actual-product-smoke-001

## Run identity

- Component: actual-product full-autonomy evaluation adapter
- Date: 2026-08-31
- Clean code revision: `75917cf589b3888d28511c040e58a8064655d1e8`
- Instrument SHA-256:
  `8949d5b9a8adc7e0c8e42bd71eb5391497e2f2406bd81461441d37c927fe7b01`
- Adapter SHA-256:
  `d80c8cbfa2e6a28c74f7e3304e4437347e5e53c1d7a93cfffbd4b2c61152034b`
- Ignored full-output SHA-256:
  `7e351515e95ac907faebbd7e55373a1851c51f13951b993748c17fd89fb2c3f8`
- Reproducible command:
  `npm run simulate:governed-autonomy-v2-1-actual-product-smoke`
- Provider boundary: network-free; zero calls, tokens, and cost
- Machine record:
  `research/05_evaluation/records/governed-full-autonomy-v2-1-actual-product-smoke-001.json`

## Decision question

Can the flow-independent autonomy contract drive and observe the real T0,
T1-v1, T1-v2 reactive, and T1-v2 autonomous product services before opening
the provider-backed evaluation?

## Method

Four synthetic-public cases exercised `StudentTutoringService`,
`GovernedAutonomyService`, `ProactiveOutreachService`, and
`SQLiteStudentRepository`. Public cases contained only events, scope, and time;
expected actions and invariants remained in separate gold objects.

All conditions executed a real student turn and a process restart. The
autonomous condition executed two confusion turns, advanced the durable clock
past the generated wake-up, restarted the repository, and processed the due
opportunity through the real worker and in-app delivery path. Deterministic
generation kept the run network-free.

## Result

- Four of four actual-service cases passed their frozen integration gates.
- Observable action matching, goal termination, pedagogical-transition, and
  restart consistency were all 100%.
- There were zero wrong-recipient, wrong-course/release, invalid-citation,
  consent, duplicate-delivery, unbounded-loop, or authority-mutation findings.
- T1-v2 autonomous produced one cited proactive in-app delivery after the due
  event, without a student message at delivery time and without duplication
  after restart.
- Provider calls, tokens, and cost were zero.

The T0 and T1-v1 controls safely returned no action because the current strict
atomic-claim validator rejected their deterministic answer. T1-v2 reactive and
autonomous returned grounded cited responses. This difference is not a product
quality comparison; it is a disclosed integration observation owned by the
open grounding decision in issue #153.

## Decision

Outcome: **Go Deeper**.

Select `StudentProductAutonomyAdapterV1` as the actual-product evaluation
bridge. It establishes that the flow-independent boundary can drive the real
services. Keep T1-v2.1 unselected and keep T0/T1-v1 as control and rollback
until #153 and the provider-backed #157 evaluation pass.

## Limitations

- Four synthetic cases establish wiring and fail-closed behavior, not product
  quality, professor fidelity, usability, or learning outcomes.
- The T0/T1-v1 no-action result is evidence of the unresolved grounding path,
  not evidence that those controls are pedagogically sufficient.
- Provider-backed exact per-call accounting is implemented but was not
  exercised here.
- The existing 820-case scripted timestamps do not match the product's 24-hour
  wake-up semantics. An actual-service timing/observer successor must preserve
  its public cases, gold, conditions, and gates before paid execution.
- Fresh grounding evidence, professor-profile reference, and external human
  evidence remain unopened or pending.
