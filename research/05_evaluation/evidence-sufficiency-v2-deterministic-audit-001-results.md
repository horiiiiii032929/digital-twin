# Evaluation result: evidence-sufficiency-v2-deterministic-audit-001

## Run identity

- Component: evidence sufficiency decision data
- Status: completed correction, pending human confirmation
- Date and owner: 2026-08-24, Codex primary data-quality audit
- Code revision: `a1307c9`
- Working tree: clean before the one-time local write
- Reproduction: `npm run verify:evidence-sufficiency-v2-draft-002`
- Generated artifact: `drafts/evidence_sufficiency_v2_decision_draft_002.json`
- Predecessor: immutable draft 001 at content hash `7c43a919...`

## Decision context

The audit asked whether the 120-case draft was trustworthy enough to freeze for
candidate evaluation after model review 008 failed its sensitivity gate. Codex
inspected every question, action, claim, source, exact quote, course, version,
and abstention boundary. Deterministic validation remained authoritative; no
model review was substituted for ground truth.

## Data and scope

The synthetic-public dataset still contains 120 cases over 40 source versions:
80 answerable and 40 abstain cases across nine slices. It contains no private
course material. No provider, local-model, paid, held-out, or candidate call
occurred. The ten modality-tagged cases exercise evidence sufficiency over
derived text representations only; they do not evaluate raw visual extraction
or region grounding.

## Findings and corrections

| Check | Draft 001 | Draft 002 |
| --- | ---: | ---: |
| Structurally valid cases | 120/120 | 120/120 |
| Multi-evidence cases with two distinct active sources | 0/15 | 15/15 |
| Permission cases with the paired stale source exposed | 0/10 | 10/10 |
| High-risk slices represented in the 12-case packet | 4/7 | 7/7 |
| Exact normalized question duplicates | 0 | 0 |

No unsupported authoritative answer, incorrect exact quote, cross-course
lineage leak, active-version error, or non-empty abstention lineage was found.
Draft 001 remains unchanged. Draft 002 records the corrections under content
hash `ae367ed195a97e5144667f4936c799edcc64991a96ffbebeb505497ffc58c9df`.

## Validity and decision

- Historical model review 008 is preserved as reviewer-unreliable and supports
  no dataset conclusion.
- The full Codex audit is inspectable but is not independent human review.
- Outcome: **Refine**. The corrected draft passes every deterministic check but
  is not frozen or opened for candidate evaluation.
- Remaining input: confirm four policy/scope examples covering distinct-source
  completeness, derived-text multimodal scope, stale-version handling, and the
  ambiguous abstain/clarify boundary.

## Learning note

Schema-valid evidence is not automatically decision-valid evidence. A
multi-evidence benchmark must require distinct supporting units, and a version
isolation benchmark must expose the stale alternative it claims to test.
