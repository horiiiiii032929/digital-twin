# Evaluation result: proactive-outreach-a1-development-001

## Run identity

- Component: proactive tutoring trigger
- Date: 2026-08-27
- Clean execution revision: `6a76585963ef5a5d5885d05d45d24e3d2a1614ca`
- Candidate: deterministic evidence-recovery A1, shadow mode
- Control: fixed no-autonomous-outreach policy
- Data: 20 synthetic cases and 12 mechanism checks
- Executed instrument SHA-256:
  `2029be99aaef07e6fba3bfa045fa27a4764d922f763b7768410ab62515025d7f`
- Ignored generated result:
  `reports/generated/proactive-outreach-a1-development-001.json`
- Generated result SHA-256:
  `438120cfd840cecdd811cbd06d7eb2ad5fac1edf47ec9318dfcc7693b55d6bfd`
- Boundary: local synthetic data only; zero network, provider, paid, private-data,
  real-student, or external-delivery operation

## Decision question

Can deterministic evidence recovery identify prior no-evidence questions that
became supportable after a new course release while preserving consent,
suppression, source lineage, idempotency, and channel-privacy boundaries?

## Method

The runner created one prior no-evidence student turn for each case, then
compared the prior release lineage with a current synthetic release. The A1
candidate searched only genuinely new source lineage and applied the frozen
BM25 plus lexical-coverage gate in shadow mode. Ten questions were deliberately
supportable and ten required no action because evidence was absent or unchanged,
consent or membership was inactive, the student was snoozed, or the question
was malformed or out of scope.

Twelve P0 checks separately exercised zero shadow side effects, zero provider
usage, active-mode fail-closed behavior, active idempotency, current-release
citation lineage, suppression rules, and a Discord request containing only a
generic notification and authenticated in-app deep link.

## Result

The clean execution completed as `completed-go-deeper`:

- 12/12 P0 mechanism and safety checks passed;
- 20/20 actions and 20/20 reasons matched the frozen labels;
- all 10 supported proposals used the expected current-release source lineage;
- the ten no-action cases created no trigger;
- shadow-mode persisted-trigger count was zero; and
- provider calls, tokens, cost, private-data reads, and external deliveries were
  all zero.

No candidate failure was classified. The fixed no-autonomous-outreach control
is safe by construction but misses all ten supported recovery opportunities.
The one-time network-free authorization was revoked after recording the result.

## Decision

- Outcome: **Go Deeper** to one separately frozen representative shadow
  confirmation.
- Keep professor-scheduled A0 outreach as the release control.
- Do not select or activate A1, automatic publication scanning, or Discord
  delivery from this development result.
- A valid confirmation failure requires a method-level decision rather than a
  prompt-tuning loop.

## Limitations and next gate

The twenty cases are synthetic development examples around one source topic;
they are not independent, held out, or representative of real course activity.
The run establishes deterministic mechanics and privacy boundaries, not message
usefulness, interruption burden, student learning, professor fidelity, delivery
reliability, or production latency.

Before release selection, a successor must use a stratified set of prior
no-evidence turns and genuinely changed course releases, keep A1 in shadow mode,
audit every proposed trigger and a seeded no-action sample, and preserve 100%
consent, lineage, suppression, duplicate-prevention, and privacy gates. Real
delivery or student participation requires its own approval.
