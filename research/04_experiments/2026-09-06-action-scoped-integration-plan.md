# Conditional V16 integration and first diagnostic gates

## Authorization condition and decision

This is a prospective implementation plan, not an integration or provider run.
Start only after the fixed-candidate fresh comparison satisfies every gate in
[the fresh assessment plan](2026-09-06-fresh-assessment-generalization-plan.md):
V16 at least54/56 adequate and54/56 flawed, each family at least26/28,
zero criticals, complete known usage, unchanged snapshots, and paired useful total
not below V14-medium. Record that decision before implementation. The earlier
V16 reused-data second-trial failure remains Refine; a new study does not relabel
that result. If the fresh gate fails, do not execute this plan.

Question: does the frozen component selection retain its behavior when it judges
actual Luna drafts with the real tutoring payload, policy, persistence and role
transport? Prediction: instruction/partial drafts receive global support checking,
while other draft actions retain V14 assessment without losing required corrections.
Controls are unchanged V14-medium for integration regression and concurrently run
V4 for the two first live diagnostic packets. This is not a new prompt experiment.

## Exact candidate and propagation

Introduce only the explicit alias `v16-luna-sol-medium`, implementation ID
`question-specific-profile-grounded-v16`, with a default-false
`instructional_action_scoped_support_enabled` flag. Require conditional and
factual revision plus their compact/typed/profile/evidence prerequisites; reject
incompatible bounded-revision or incomplete flag combinations rather than silently
constructing another generator. Existing aliases, flags, default values and the
selected `student-tutor-r1-local-final-v1.json` remain unchanged.

Reuse the audited helper in
`/tmp/digital-twin-action-scoped-20260906/src/digital_twin/generation/action_scoped_support.py`
byte-for-byte, with both existing assessment prompts unchanged. Validate the draft
as `TypedInstructionProposal`; instruction and partial select exact V15 global
assessment, and question, clarify, no_evidence, private and graded select exact
V14 conditional assessment. No text/profile/gold matching. Draft action selects
an assessment, never a replacement-action ceiling. A wrong question/refusal can
still become an instruction; an inappropriate instruction can become an initial
question. Neither branch gives semantic certification.

Add a small assessment method to the shared conditional generator whose default
calls the current V14 helper. A separately named V16 subclass overrides only that
method and its implementation/version identity. Preserve draft generation,
pre-assessment composition, typed validation, combined usage, final-response
composition and fail-closed handling. KEEP retains the original raw draft bytes
and Luna final-provider identity; REPAIR returns the typed replacement with Sol
identity. Avoid copying the entire request/exception implementation into a second
class. Compare V14 messages and responses before/after this interface extraction.

Propagate through these inspected entrypoints:

- `src/digital_twin/evaluation/experimental_tutoring_candidate.py`: explicit alias,
  all inherited V14 prerequisites, new flag, final-response role and configuration.
- `services/api/app/factory.py`: parameter validation, exact generator selection,
  experimental candidate metadata and source-bound generated-preview configuration.
  Generated-preview shadow construction copies public factory parameters by
  signature introspection; test that the new flag actually survives this copy.
- `scripts/final_profile_longitudinal_runtime.py`: explicit default-false parameter
  forwarded on initial construction and the captured restart factory.
- `scripts/run_generation_role_model_comparison.py`: allowed version and expected
  V16 ID. `run_paired_pedagogy_development.py`: role variant and revision-variant
  membership, three-role bounds, observed generator checks and CLI choice.
- `scripts/run_instructional_operational_comparison.py`: allowed role variant,
  restart identity checks and existing three-role accounting.
- `scripts/run_authenticated_loopback_load_development.py`: both generation and
  serving configurations, candidate whitelist/CLI and three-role bounds; preserve
  its existing explicit session/authentication path.
- `scripts/run_teaching_profile_responsiveness_development.py`: dynamic alias
  selection through `GENERATION_VARIANTS`; verify the existing three-role150-call
  contract recognizes V16 instead of falling through to the100-call branch.

`services/llm/experimental_role_routing.py` already routes
`question_specific_conditional_revision` to revision. Keep that task/schema and
validate the actual transport binding rather than introduce another task name.
Generation and planner remain `gpt-5.6-luna`, reasoning low, cap3000. Revision is
`gpt-5.6-sol`, reasoning medium, cap3000. The API payload must actually contain
those values. A configuration label alone is insufficient. Update experiment-only
README commands, execution inventory/audit and source snapshots before dispatch;
do not select a release, deploy, or claim professor approval.

## Contract checks before paid diagnostics

Retain the component's seven-action selection and original-prompt tests. Add actual
runtime checks that exercise both branches, including an instructional false claim,
a safe initial question, a misleading answer-bearing question, a mistaken refusal
that becomes an explanation, and an instruction that becomes a protected question.
Verify selected system-message bytes at the actual Responses transport boundary,
unchanged public payload, exactly one draft and one assessment per normal call,
combined tokens/cost, raw KEEP bytes, REPAIR identity, and no discarded draft or
assessment diagnosis exposed in delivered student content.

Cover malformed wrappers, inconsistent action/move, unknown provider identity,
unknown usage, provider error, invalid draft and source-binding/composer failure.
No case may fall back to an unchecked draft. Test cross-role stop on unknown cost,
all-ledger call/cost limits, snapshot mutation detection and privacy/gold exclusion.
Test factory invalid flags, unchanged V14/default configuration, persistent restart,
all listed runner selectors, generated preview shadow identity, profile response
contracts and the authenticated local route using injected transport. These tests
verify integration, not semantic accuracy. Run the required repository checks after
implementation; preserve environmental failures and any bounded retries explicitly.

## First live stage: exact inspected budgets

Use unchanged packets:

- Necessary-condition8:
  `research/05_evaluation/datasets/necessary-condition-development-v1.json`, SHA256
  `0662fd06ff71d1b6842b6263b9471129e67168800f3b3a011b2babfc9e0482b6`.
- Procedure/constraint16:
  `reports/generated/procedure-constraint-contrast-development-v1/packet.json`, SHA256
  `59bfcbac34ddb3c94418c42224a68dd41f456ddb5774e86d7b58358ede1520dd`.

Both have one student turn per context. No sealed material or sealed builder is
needed. Run V16 versus V4 with the actual persistent paired runner, one repetition,
its unchanged default schedule seed7801 and four-history semaphore. Execute the
necessary8 run first; if it fails, stop before the contrast16 run. If necessary8
passes, execute contrast16 once. Do not retry outcomes or average the two gates.

| Packet | Delivered turns, both arms | Whole-run call cap | Whole-run USD cap | V16 arm cap | Each V16 role cap | V4 arm cap |
|---|---:|---:|---:|---:|---:|---:|
| Necessary8 | 16 | 120 | 19.20 | 60 / USD9.60 | 20 / USD3.20 | 60 / USD9.60 |
| Contrast16 | 32 | 240 | 38.40 | 120 / USD19.20 | 40 / USD6.40 | 120 / USD19.20 |
| Maximum across both | 48 | 360 | 57.60 | 180 / USD28.80 | 60 / USD9.60 | 180 / USD28.80 |

These are conservative ceilings, not expected usage or claimed costs. They follow
actual `run_paired_pedagogy_development.run`: divide whole-run limits equally
between V4 and candidate; `create_recorded_generation_roles` divides the candidate
half equally across planner, generation and revision. Each candidate role reserves
USD0.16 per call, whereas the V4 recorded client reserves USD0.025. Keep the
whole-run caps above rather than pretend V4 consumes the full USD0.16 reservation.
There are two Luna roles plus one Sol revision role, not a two-role total.

The paired runner's conservative check is `2 × N × 5` calls (80 for N8,160 for N16)
and `2 × N <= floor(floor(maximum_calls/2)/3)` for each candidate role. The proposed
120/240 caps satisfy the stronger role-partition check (16<=20 and32<=40).
Single-turn generation may not need a planner call, but do not remove its finite
allocation or assume every future trajectory omits planning. The40-call local
per-history guard remains nested inside global/role bounds, not an extra allowance.

Prospective commands after gate approval, implementation and snapshot freeze:

```sh
.venv/bin/python -m scripts.run_paired_pedagogy_development --live --candidate v16-luna-sol-medium --packet research/05_evaluation/datasets/necessary-condition-development-v1.json --output-dir reports/generated/paired-pedagogy-development-001-v16-necessary-live-001 --repetitions 1 --maximum-calls 120 --maximum-cost-usd 19.20 --input-provenance research/04_experiments/2026-09-06-action-scoped-integration-plan.md
.venv/bin/python -m scripts.run_paired_pedagogy_development --live --candidate v16-luna-sol-medium --packet reports/generated/procedure-constraint-contrast-development-v1/packet.json --output-dir reports/generated/paired-pedagogy-development-001-v16-procedure-contrast-live-001 --repetitions 1 --maximum-calls 240 --maximum-cost-usd 38.40 --input-provenance research/04_experiments/2026-09-06-action-scoped-integration-plan.md
```

Commands are sequential decision stages, not a command batch to launch before
review. Load credentials in process only; preserve store=false and existing
provider configuration without claiming zero retention. Archive exact code dirty
state, helper/prompt/model/profile hashes, packet bytes, plan and all per-case
outputs. Reject a composition mismatch or changed source/input snapshot.

## Acceptance and subsequent scope

Require8/8 and16/16 candidate useful targets, respectively, zero criticals across
all actual delivered candidate content, complete histories and known usage.
Review source entailment, event/implication direction, direct application of complete
procedures and inappropriate hedging from actual text. A provider KEEP, valid JSON,
resolved citation or successful HTTP response is not a quality label. Grade V4 too;
report paired gains/losses, per-family errors, uncertainty, tokens, cost and latency.
Uncertain cases are unqualified in the fixed denominator. Record every run whether
pass, fail, inconclusive or invalid. Failure means Refine/Drop and no later suites.

A pass permits a separately bounded proposal for short28, profile12, corrected
main two-trial and boundary/mixed checks; it does not authorize skipping them or
opening sealed confirmation immediately. Preserve the old Dahlia limitation.
Permitted-course transfer,400/200/200 breadth,24 longitudinal histories and actual
browser qualification remain separate. No instructor fidelity, student learning,
production qualification or unlimited autonomous operation is established by this
integration stage.
