# Revision Review Agent

## Purpose

Map professor feedback on previews or policy fields into a proposed policy
revision that the professor must explicitly confirm or discard.

## Current status

Prototype. Feedback classification is deterministic and supports academic
integrity, source/citation, and tone revisions.

## Inputs

- Professor post-generation chat feedback.
- Current rejected preview decisions.
- Current tutor policy.

## Outputs

- Pending revision proposal.
- Affected policy field IDs.
- Proposed policy value.
- Rationale.
- Regenerated preview evidence after confirmation.

## Guardrails

- Do not apply a revision without explicit professor confirmation.
- Preserve discarded revisions as non-applied decisions in session behavior.
- Reset affected preview decisions to pending after regeneration.
- Mark resolved rejected previews when a confirmed revision addresses them.

## Evaluation

- Revision proposal tests.
- Confirm/discard API tests.
- Policy version increment tests.
- Preview regeneration tests.

## Open work

- Add structured reason categories for rejection.
- Track revision history beyond the current in-memory session.
- Add conflict detection when feedback maps to multiple policy fields.
