# Issue 80 professor console redesign

Issue: [#80 Redesign professor review console UX/UI](https://github.com/horiiiiii032929/digital-twin/issues/80)

Date: 2026-08-18

Baseline: `2071c8b999621b9d567442ca492d6c372e23b1bd`

Candidate: `codex/redesign-professor-console`

Product-direction disposition: **Keep.** The repository owner selected Option B
and confirmed that the remaining product work should continue from this visual
and interaction model. Do not call this a professor-approval or human-usability
result.

## Decision question

Can the professor workflow feel like a coherent LLM product while keeping source
permissions, policy state, preview evidence, release blockers, and professor
authority explicit and preserving the existing onboarding API?

## Direction decision

The first implementation, **The Course Release Dossier**, was rejected after
rendered review because it looked like a research artifact rather than a product.
That rejection is retained as part of the design history.

Three LLM-workspace directions were then compared. The selected direction was
**Option B: Conversation + tool**. Its defining topology is a quiet setup-stage
sidebar, a natural interview workspace, a structured review tool at right, and a
compact blocker strip. The composition draws on familiar LLM-product patterns
without copying competitor branding or carrying invented mock capabilities into
the implementation.

## Implemented result

- Rebuilt the page as a compact application shell with Sources, Interview,
  Policy, Preview, and Approval navigation.
- Kept the real interview in the central conversation surface and mapped each
  existing review stage to the structured tool area.
- Preserved all controller operations and API contracts for source metadata,
  policy editing, preview decisions, revision proposals, and approval checks.
- Replaced report-like records and repeated cards with product-density rows,
  status controls, progressive disclosure, and one elevated composer.
- Kept structured policy JSON available through an explicit advanced editor
  while presenting a truthful human-readable summary by default.
- Added an Activity surface for blockers, recent evidence, and setup history.
- Kept the release strip and top status tied to the actual derived readiness;
  no invented model, upload-processing, integration, analytics, collaboration,
  or release capability was added.
- Applied the independent Impeccable finish review: release chrome remains fixed
  to the viewport, invalid structured JSON cannot be saved, failed create/send
  operations retain input, blocker summaries no longer imply incorrect links,
  message accessibility names preserve their content, source privacy copy is
  explicit, and coarse-pointer controls meet the 44-pixel target floor.

## Engineering evaluation

The principal flow was: app loads → professor completes all five interview
prompts → policy and evidence surfaces render → stage and Activity navigation
update → the policy status and advanced editor remain usable.

| Check | Result |
| --- | --- |
| Page identity and meaningful content | Pass: product identity, five-stage navigation, interview, structured tool, and release state render |
| Functional parity | Pass: all existing stages and controller actions remain wired |
| Interview flow | Pass: five answers generate the real draft policy and update stage states |
| Policy controls | Pass: field value, status, save, safe-default text, and structured JSON editor remain available |
| Browser runtime | Pass: no console warnings or errors during the checked flows |
| Desktop layout | Pass at 1280×720 with no page-level horizontal overflow |
| Tablet layout | Pass at 768×1024 with no page-level horizontal overflow |
| Mobile layout | Pass at 390×844; stage switching, source tool, release bar, and named controls remain usable with no page-level horizontal overflow |
| Accessibility smoke checks | Pass: no unnamed buttons, inputs, textareas, selects, or links in the inspected states; status is expressed in text as well as color |
| Product-direction review | Keep: repository owner selected the conversation-plus-tool workspace and authorized the next product slice |
| Human usability | Not run |
| Professor preference/approval | Pending |

The final `npm run check` passed all documentation and evaluation validators,
299 Python tests, 18 frontend tests, frontend lint, and the production build.
The command used preflight-only evaluation paths and made no external model call.
Detailed visual comparison and iteration evidence is in `design-qa.md`.

## Evidence and limitations

Local, ignored visual artifacts are stored under
`reports/generated/ui-redesign-issue-80/`. They include the selected Option B
reference, normalized comparison images, desktop implementation states, and a
mobile check. The candidate uses only synthetic demonstration data.

The approved concept contains invented example copy and controls such as a named
course, timestamps, attachments, bulk review, and adding arbitrary policy items.
Those composition-only elements were intentionally not implemented because the
current product does not support them. The implementation uses actual interview,
policy, blocker, preview, and approval data instead.

This result supports engineering correctness and a review-ready visual candidate
only. It does not establish faster task completion, lower error rate,
accessibility conformance, human usability, professor satisfaction, pedagogy,
learning outcomes, or production readiness.

## Decision and next boundary

Keep Option B as the product direction and close #80 when its implementation PR
merges. This decision accepts the conversation-plus-tool model for continued
prototype development; it does not substitute for professor review or a human
usability study. Continue the next bounded product slice under #8 without
changing the frozen retrieval, generator, policy, or research-evidence profile.

## Current visual authority

The repository-owner review later returned **Refine** for the product-wide UX.
Issue #84 supersedes Option B's horizontal/narrow-layout behavior with a shared
conversation-first rail and contextual inspector. The functional parity and QA
evidence in this record remain valid historical evidence; its screenshots are
no longer the current visual specification.
