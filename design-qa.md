# Design QA: professor LLM workspace

Final result: **passed**

Date: 2026-08-18

## Comparison setup

- Approved source: `reports/generated/ui-redesign-issue-80/llm-workspace-option-b.png`
- Source dimensions: 1672×941 pixels.
- Normalized source used for the direct comparison:
  `reports/generated/ui-redesign-issue-80/llm-workspace-option-b-1280x720.png`.
- Implementation evidence:
  `reports/generated/ui-redesign-issue-80/llm-workspace-implementation-configured-final.png`.
- Implementation frame: 1280×720 CSS pixels at device-pixel ratio 1.
- Compared state: completed five-question interview with the generated draft
  policy visible and both conversation and policy panes scrolled to their top.
- Focused responsive evidence:
  `reports/generated/ui-redesign-issue-80/llm-workspace-mobile-sources-390x844.png`.
- The visual artifacts above are intentionally ignored generated evidence; this
  document retains the durable findings and decisions.

The approved source was proportionally normalized to 1280×720 so the full-view
source and implementation could be inspected together at the same frame size.
The in-app browser was also checked at 768×1024 and 390×844.

## Full-view comparison

| Surface | Approved source | Implementation | Result |
| --- | --- | --- | --- |
| Shell topology | Compact app bar, stage sidebar, conversation, structured tool, blocker strip | Same five-region topology and reading order | Pass |
| Navigation | Five short stages, active iris state, explicit progress icons | Five real stages with active, complete, blocked, and waiting states | Pass |
| Conversation | Open transcript with restrained assistant/professor identity and a floating composer | Real onboarding transcript, suggested replies, named composer controls, and the same open visual treatment | Pass |
| Structured tool | Compact policy rows with editable guidance and status | Actual policy groups with editable values, status selectors, save actions, safe defaults, and progressive JSON disclosure | Pass |
| Release state | Concise draft status and persistent blocker strip | Actual derived draft/blocker count, two visible blocker summaries, and a next-action control | Pass |
| Visual language | White canvas, quiet gray shell, restrained iris, amber and green semantic states | Tokens, type, radii, borders, icons, and composer elevation follow the same language | Pass |
| Product truth | Composition-only sample content | No invented course, collaborator, upload-processing, integration, analytics, model, or publishing capability shipped | Pass |

## Focused behavior and accessibility checks

- The interview accepts suggested or typed answers and generates the real draft
  policy after the fifth response.
- Sources, Interview, Policy, Preview, and Approval navigation all replace or
  update the expected structured tool.
- Activity opens and closes the real blocker, evidence, and setup-history view.
- The desktop sidebar collapses to 72 pixels and restores to 240 pixels.
- The structured policy status selector retains the backend field state; the
  advanced JSON editor can be expanded without making raw JSON the default view.
- Desktop 1280×720, tablet 768×1024, and mobile 390×844 have no page-level
  horizontal overflow and no browser console warning or error.
- At 390×844 the stage route remains horizontally scrollable, the active tool is
  focused, the release strip reduces to blocker count plus Review, and all
  inspected controls have an accessible text name.
- Color is supplementary: state text or accessible labels carry the same meaning.

## Copy diff

The approved concept used invented content solely to communicate composition.
The implementation intentionally differs as follows:

| Concept copy/control | Implementation decision |
| --- | --- |
| Named course and student-goal examples | Omitted; no course identity is available in the current API |
| Message timestamps | Omitted; the current transcript has no timestamp field |
| Attachment, book, and extra AI-tool icons | Omitted; those capabilities are not implemented |
| Review all and add policy item | Omitted; no safe bulk-review or arbitrary-field API exists |
| Two illustrative blockers | Replaced with the actual derived blocker count and real blocker labels |
| Simplified seven-row policy | Replaced with the complete generated policy; structured JSON is summarized and remains editable through progressive disclosure |

## Iteration history

### Pass 1

- P1: Suggested replies overflowed the conversation pane at 1280 pixels.
  Fixed by using a responsive one/two-column grid.
- P1: The policy surface exposed three status buttons per field and allowed raw
  structured JSON to dominate the first viewport. Fixed with one named status
  selector, one Save action, and a collapsed advanced JSON editor.
- P1: The mobile Activity button had no accessible name. Fixed with an explicit
  `aria-label`.
- P1: The mobile blocker strip pushed its primary action off screen. Fixed by
  hiding secondary blocker detail below the small breakpoint and retaining a
  concise Review action.
- P1: An empty Sources panel displayed `clear` while the release model still
  required an approved source. Fixed by deriving `needs source` from the real
  source inventory.
- P2: Long research-oriented stage labels and state prose truncated in the
  sidebar. Fixed with product labels, short task descriptions, and state in the
  accessible label and icon.

### Pass 2

- The independent Impeccable finish reviewer found no P0 issue and identified
  additional P1/P2 hardening work. The app shell is now fixed to the dynamic
  viewport so the blocker strip and sidebar collapse control remain persistent
  after policy generation.
- Individual blocker summaries are no longer misleading links; the single next
  action retains the correctly derived destination.
- Message text no longer has an overriding generic `aria-label`.
- Chat, source, and custom-preview input is cleared only after a successful API
  operation.
- Invalid structured JSON now exposes an error and disables Save instead of
  silently retaining the old value.
- The app bar reports the actual Blocked/Draft/Approved state, success text was
  darkened to exceed 4.5:1 on its soft background, coarse-pointer controls have
  a 44-pixel minimum target, and the source picker explicitly states that file
  contents are not uploaded or parsed.

### Pass 3

- Rechecked the configured 1280×720 state. The document remains exactly one
  viewport high, the persistent blocker bar is visible, the app bar and policy
  agree on `Blocked`, no individual blocker is exposed as a button, and no
  generic message `aria-label` remains.
- Expanded the structured-policy editor, entered invalid JSON, and confirmed the
  inline error, `aria-invalid=true`, and disabled Save state before restoring the
  valid value.
- Recompared the normalized approved source and implementation. No remaining P0,
  P1, or P2 issue changed the selected product direction, obscured release
  meaning, broke a core interaction, or caused responsive overflow.

## Limitations

This is an engineering and visual-fidelity QA result, not a usability study or
accessibility-conformance audit. It does not establish professor satisfaction,
task-time improvement, pedagogy, or production readiness.

## Product-direction decision

The repository owner selected Option B and authorized continued product work
from this conversation-plus-tool pattern. The disposition for issue #80 is
**Keep**. Professor approval and human-usability evidence remain untested.
