# Tutor Policy Agent

## Purpose

Convert instructor setup answers into a structured tutor policy that controls
course grounding, academic integrity, teaching approach, misconception handling,
tone, and release approval.

## Current status

Prototype. Implemented with Pydantic policy models in
`src/digital_twin/tutor_policy.py` and deterministic policy construction in
`src/digital_twin/onboarding_workflow.py`.

## Inputs

- Completed onboarding answers.
- Source-governance state.
- Professor field edits.
- Confirmed revision proposals.

## Outputs

- `TutorPolicy` with safety, pedagogy, and professor-review fields.
- Policy field statuses:
  - `resolved`
  - `needs_review`
  - `blocks_release`
- Policy release status.
- Policy-field release blockers.

## Guardrails

- Source strictness blocks release until professor-confirmed.
- Private-source exclusions block release until resolved.
- Sensitive-data handling blocks release until resolved.
- Professor release approval is required for student-facing use.
- Academic-integrity policy starts with a review warning.

## Evaluation

- Policy model tests.
- Policy update API tests.
- Release blocker tests.
- Preview regeneration tests after confirmed revisions.

## Open work

- Add schema versioning for policy migrations.
- Separate policy extraction confidence from release status.
- Add examples of approved and rejected tutor behavior per policy field.
