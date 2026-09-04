# Revision Review Agent

## Purpose

Map professor feedback on previews or policy fields into a proposed policy
revision that the professor must explicitly confirm or discard.

## Current status

Implemented. Feedback classification is deterministic and supports academic
integrity, source/citation, tone, depth, examples, misconception handling, and
outreach-policy revisions. Decisions and conflicts persist across restarts.

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
- Preserve discarded and superseded revisions as immutable non-applied records.
- Require explicit field selection when feedback matches multiple categories.
- Reject stale and duplicate confirmation against the base policy version.
- Reset affected preview decisions to pending after regeneration.
- Mark resolved rejected previews when a confirmed revision addresses them.

## Evaluation

- Revision proposal tests.
- Confirm/discard API tests.
- Policy version increment tests.
- Preview regeneration tests.
- Restart, concurrent update, stale confirmation, and duplicate-submit tests.

## Open work

- Real-professor review of the proposed category vocabulary and workflow.
- Representative usability evidence for conflict resolution and history views.
