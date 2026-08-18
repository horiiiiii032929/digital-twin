# Issue 84 — Unified LLM workspace UX

## Outcome

Refine the professor and student routes into one conversation-first product
shell. The implementation keeps the real setup, release, recovery, and citation
behavior while removing the horizontal professor wizard and the permanently
open student citation column. The result is ready for human product-direction
review; it is not evidence of human usability or professor/student approval.

## Decision question

Can both role surfaces use familiar mature-LLM interaction conventions without
hiding professor governance, current-release binding, or exact citation lineage?

## Impeccable workflow and selected direction

The product truth, incumbent design system, both surface briefs, and live routes
were audited before implementation. Three coordinated desktop/mobile
composition boards were generated. Composition C was selected because it had
the strongest task clarity and did not imply server-side history, real identity,
analytics, model selection, web search, or file-content ingestion.

The accepted visual direction is recorded locally at
`reports/generated/ui-redesign-product-wide/composition-c-accepted.png`.
`apps/web/DESIGN.md`, its Impeccable sidecar, and both route briefs now make this
conversation-first layout the current authority.

## Implemented result

- Added a shared Course Digital Twin identity and a 216px quiet navigation rail.
- Kept the professor interview visible across Sources, Interview, Policy,
  Preview, Approval, and Activity; each structured surface now opens in a
  contextual inspector.
- Kept release status and blockers visible in both the course header and rail
  without a fixed bottom blocker strip.
- Made student citation context closed by default; selecting an inline marker
  opens the exact source and release lineage while preserving transcript
  position.
- Limited student navigation to the assigned course, New chat, and the one
  browser-local conversation; no unsupported history was added.
- Replaced mobile horizontal setup/course bars with keyboard-operable menu and
  bottom sheets, including Escape close, focus containment/return, a visible
  sheet affordance, and breakpoint-accurate action labels.
- Preserved all existing loading, empty, revoked, stale-release, failed-question,
  and workspace-recovery behavior.
- Hardened populated professor review: policy fields and preview cases are
  summary-first one-item queues, approval separates remaining and completed
  checks, all save/compare/audit/decision controls have item-specific accessible
  names, and stage changes reset the inspector scroll position.
- Added `?demo=supervisor`, backed by a deterministic API fixture containing
  synthetic interview answers and metadata only. It opens at Policy and makes
  the professor review flow inspectable without rebuilding five interview turns.

## Screen and state coverage

| Surface | States inspected |
| --- | --- |
| Professor desktop | Interview, Sources empty/blocker and synthetic approved metadata, Policy empty/populated queue, Preview empty/three-case queue/custom prompt/decision, Approval empty/populated/completed split, Activity/blockers/history, inspector close/reopen and stage scroll reset |
| Professor mobile | Conversation, setup navigation sheet, populated policy and preview inspectors, source inspector, blocker status, no horizontal overflow |
| Student desktop | Empty conversation, grounded answer, inline citation, citation inspector open/closed, New chat/current chat rail |
| Student mobile | Conversation, course navigation sheet, citation sheet, header status, composer |
| Shared behavior | Desktop 1536×1024, mobile 390×844, short 768×512 and 390×420 viewports, no page overflow, semantic names, disabled actions, focus-visible controls, and mobile-sheet-to-desktop transitions |

## Concept-to-render fidelity ledger

| Comparison point | Concept evidence | Render evidence | Resolution |
| --- | --- | --- | --- |
| Product topology | Quiet rail, dominant chat, optional inspector | Both routes use 216px rail, flexible transcript, 400px inspector | Matched |
| Professor workflow | Conversation remains behind every setup stage | All five stages and Activity open beside or over the same interview | Matched |
| Student evidence | Inline citation opens context without losing the answer | `[1]` opens desktop inspector or mobile sheet; closing restores width | Matched |
| Mobile response | Rail becomes menu; context becomes bottom sheet | 390×844 menu and focus-trapped sheets verified | Matched |
| Palette and depth | True white, cool gray shell, restrained iris, minimal elevation | Existing exact tokens retained; only composer/sheets are elevated | Matched |
| Typography and density | Workhorse sans, compact chrome, readable transcript | Geist Variable, 14–16px UI hierarchy, 65–75ch message measure | Matched |
| Copy | Synthetic course, setup stages, blockers, release and citation labels | API-backed copy and actual blocker/citation data used | Matched with truthful live content |
| Concept-only data | Longer conversations and illustrative source form | No fake course owner, timestamps, identity, history, or ingestion fields added | Intentional deviation |
| Primary action color | Saturated sample action in concept board | Near-black existing primary token | Intentional system-token preservation |

The above-the-fold copy diff found no unsupported product claims or controls.
Visible deviations are limited to real API content and the existing durable
primary-action token.

## Verification

- Built-in browser was attempted first; local page navigation and DOM evaluation
  timed out, so rendered QA used the Playwright CLI fallback.
- Browser flows verified professor stage switching, inspector open/close,
  student question submission, grounded answer, citation open/close, menu sheets,
  focus return, short-viewport composer access, and open-sheet breakpoint
  transitions without residual modal page blocking.
- Final native concept-size renders used 1536×1024; mobile used 390×844.
- The final repository-wide gate passed: 299 Python tests, 26 frontend tests,
  all 19 student-workflow checks, documentation and evaluation validators,
  lint, and the production build. It made no paid model call and read no private
  or held-out evaluation data.
- An independent Impeccable finish review first found focus-return,
  short-viewport, and open-mobile-sheet breakpoint defects. Each was reproduced,
  fixed, and retested; the post-fix verdict was `SHIP`.
- Final screenshots are local ignored artifacts under
  `reports/generated/ui-redesign-product-wide/`.
- The populated-state follow-up used the built-in browser at 1280×720 and
  390×844. It verified zero page/inspector horizontal overflow, field- and
  case-specific accessible names, a real preview decision, top-reset on stage
  change, and student citation source-version/release lineage with no console
  warnings or errors.

## Limitations and human review boundary

This pass establishes engineering behavior, responsive implementation, and
concept fidelity. It does not establish task-completion speed, error rate,
learnability, WCAG conformance, professor preference, student preference,
learning effectiveness, credentialed authentication, or production readiness.
The next valid product decision is a human `Keep` or `Refine` review of the two
routes; no review of all synthetic evaluation questions is required here.

## Rollback

Revert the issue #84 workspace-shell and documentation commit. The API,
controllers, source/policy/preview/approval components, student recovery logic,
frozen evaluation profiles, and shared API client remain the control. A rollback
restores the prior professor wizard and persistent student citation layout
without changing stored onboarding or conversation data.
