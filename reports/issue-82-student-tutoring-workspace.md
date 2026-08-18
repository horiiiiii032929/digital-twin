# Issue 82 student tutoring workspace

Issue: [#82 Build student tutoring workspace](https://github.com/horiiiiii032929/digital-twin/issues/82)

Date: 2026-08-18

Baseline: merged Option B professor workspace at `a5806f52a236bd1c52e7c6bc9585d46e9c652718`

Candidate: `codex/student-tutoring-workspace`

Product-direction disposition: **Pending review.** The candidate is ready for
repository-owner review. Engineering checks do not establish professor
approval, student usability, learning effectiveness, or production readiness.

## Decision question

Can the existing synthetic student/publication core become a coherent,
responsive student tutoring product surface while preserving course isolation,
release binding, citation lineage, retry safety, and the selected Grounded AI
Workspace direction?

## Control and candidate

The control was the API-only student workflow: 19 synthetic acceptance checks
covered authorization, persistence, grounding, publication replacement,
withdrawal, rollback, fallback, and stale-release denial, but no student web
interface existed.

The candidate adds a separate `/student` workspace and typed client/controller
boundary. It deliberately does not change retrieval, generation, policy,
publication, database, or evaluation-profile selection.

## Implemented result

- Added a quiet one-course rail, focused tutoring conversation, grounded answer
  markers, and a desktop citation inspector.
- Added a compact mobile course strip and citation bottom sheet while preserving
  conversation-first document order.
- Restores release-bound conversations and citation details from the API after
  reload. Browser storage holds only versioned course and conversation IDs.
- Uses stable per-draft request IDs. A failed send preserves text and retries
  the same idempotent request instead of risking a duplicate turn.
- Separates ordinary transport recovery from withdrawn/replaced-release
  recovery. Starting the current release keeps the student's unsent draft.
- Preserves source title, locator, source version, and current-release lineage
  in the citation surface.
- Keeps the professor route isolated from student controller initialization and
  adds reciprocal navigation between the two local product surfaces.
- Adds a synthetic seed command and network-free frontend tests for the API
  client, conversation index, and request-ID fallback.

## Engineering evaluation

| Check | Result |
| --- | --- |
| Successful tutoring flow | Pass: question, grounded answer, and citation lineage render from the real local API |
| Conversation persistence | Pass: question, answer, and citations restore after browser reload |
| Idempotent retry | Pass: an aborted request retains the draft; `Try again` succeeds with the pending request ID |
| In-flight context safety | Pass: course and New chat controls are disabled during a delayed response, and operation guards reject a result or error after a context change |
| Release withdrawal/restoration recovery | Pass: a withdrawn release produces an explicit recovery state, retains the draft while no current release exists, and starts a current-release conversation after restoration |
| Workspace recovery | Pass: conversation-opening failure is labelled separately from a failed question and `Retry course` restores the workspace |
| Empty and revoked states | Pass: an empty assigned-course response and structured revoked-account denial render distinct truthful states |
| API acceptance boundary | Pass: all 19 synthetic student/publication checks remain green |
| Desktop layout | Pass at 1440×900 with a 240px course rail, flexible conversation, 420px citation panel, and no page-level horizontal overflow |
| Tablet layout | Pass at 768×1024 with no page-level horizontal overflow or unnamed controls |
| Mobile layout | Pass at 390×844 with no page-level horizontal overflow, no unnamed controls, 44px coarse-pointer targets, and a citation dialog sheet with focus entry, Escape close, and trigger-focus restoration |
| Browser runtime | Pass in normal flows with no observed warnings or errors; one expected console error was produced only during the intentional network-abort check |
| Human usability | Not run |
| Professor or student approval | Not established |

The final `npm run check` passed 299 Python tests, 26 frontend tests, all 19
student/publication workflow checks, documentation and evaluation validators,
technical-freeze validation, frontend lint, and the production build. The
preflight-only evaluation paths made no external model call and read no private
or held-out data.

The independent Impeccable finish review initially returned `HOLD` for an
in-flight conversation race, incomplete modal keyboard behavior, ambiguous
workspace-error copy, and an overstated replacement-evidence label. Those
findings and the subsequent desktop hidden-dialog risk were corrected. The
post-fix review returned `SHIP` with no remaining actionable findings and low
risk for this bounded prototype.

## Concept-to-implementation fidelity ledger

| Comparison point | Outcome |
| --- | --- |
| Product topology | Preserved: course context, primary conversation, and citation evidence have the same desktop hierarchy |
| Visual system | Preserved: Geist/system typography, neutral shell, white canvas, iris focus, compact borders, and restrained elevation extend the accepted professor direction |
| Course navigation | Preserved with truthful scope: one assigned synthetic course and current-browser conversation reference; no invented global history or course search |
| Conversation | Preserved: assistant/student rhythm, readable line length, one elevated composer, and grounded citation markers |
| Citation evidence | Preserved: title, page locator, source version, and release lineage appear on desktop and in the mobile sheet |
| Responsive behavior | Preserved: desktop side panel becomes a focused bottom sheet; course context condenses above the conversation |
| Intentional copy deviation | The API's truthful `Based on approved course evidence:` prefix remains; concept-only abbreviated copy was not substituted |
| Intentional control deviation | Empty composer send remains visibly disabled; the concept's always-blue illustrative control was not implemented as fake readiness |
| Intentional data deviation | No timestamps, attachments, model picker, generated history, or unsupported course-management controls were invented |

## Evidence and limitations

Local, ignored concept and implementation screenshots are stored under
`reports/generated/ui-redesign-issue-82-student-workspace/`. Desktop and mobile
implementation renders were compared directly with their generated design
references during the final QA pass.

The candidate uses a synthetic `X-Account-ID` fixture and deterministic grounded
generator. It lacks credentialed authentication, server-side conversation
listing/search/delete, cross-device history, complete course/source
administration, schema migration, backup/restore, multi-process concurrency,
capacity evidence, formal accessibility conformance, and human usability data.

## Decision boundary

The candidate is ready for a `Keep` or `Refine` product-direction review. A
`Keep` would accept this student workspace for the prototype demo only. It must
not be interpreted as a model-selection change, professor validation, student
approval, accessibility certification, learning-outcome evidence, or a
production release decision.
