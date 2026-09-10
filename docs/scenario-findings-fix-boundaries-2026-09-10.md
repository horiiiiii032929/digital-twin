# Scenario findings: permitted fixes and decision boundaries

Date: 10 September 2026. Investigation ID: `scenario-investigation-003`.

The remaining findings are not all algorithm problems. Two local hook probes reproduce application loading defects that can be repaired without changing tutor decisions. Other findings concern the selected retrieval, refusal, assessment or publication behavior and must stay unchanged under the user's current instruction. This investigation makes no production changes and does not resume AWS.

## Authority and evidence

The governing boundary is the user's instruction: anything changing an app decision is not allowed. The latest presentation contract remains the 70-slide deck fingerprinted in [slide alignment](../reports/aws-pilot/slide-alignment-001.json) and the [slide-aligned plan](../research/04_experiments/2026-09-09-slide-aligned-code-fix-plan.md). Preserve model roles, prompts, audit gates and repair limits, current-message retrieval, selected assessment, approval requirements and disabled outreach. A small code edit can still violate this boundary; an issue need not require infrastructure redesign to be out of scope.

Reviewed the [lifecycle findings](../tests/manual/aws-pilot-lifecycle-001-results.md), [106-scenario coverage](../tests/manual/aws-pilot-lifecycle-001-coverage.md), [scenario plan](../tests/manual/aws-pilot-scenario-plan-2026-09-09.md), 84 recorded turns, subsequent slide-codefix reports and current implementation. New local exploratory evidence is recorded in [the investigation result](../research/05_evaluation/scenario-investigation-003-results.md).

## Confirmed additional coding defects

| ID | Evidence | Permitted repair | Required verification |
| --- | --- | --- | --- |
| H-001 | In `use-student-workspace.ts`, `sendContent` receives and stores the completed reply but awaits optional learner evidence before releasing `isSubmitting` and clearing the sent draft. A deferred evidence promise reproduced the locked composer after completion. | Complete the authoritative send UI independently of evidence refresh. Display evidence loading/failure separately. | Completed reply releases composer even when evidence stalls or fails; no duplicate send; exactly the original request ID; late evidence cannot overwrite a newer turn or another course/account. |
| H-002 | `loadConversation` receives saved messages but awaits citations/evidence before exposing them and ending loading. A deferred evidence promise reproduced hidden saved history. | Display successfully loaded history immediately and load auxiliary metadata independently. | History remains visible when optional reads stall/fail; citations remain associated with their messages; late responses cannot cross conversation/course/account boundaries. |

These are local hook reproductions, not a rendered-browser rerun or proof of the historical AWS hang's cause. The tests assert the observed defect; their two passes do not mean either bug is fixed. The current fetch wrappers also lack an explicit request deadline, but a blanket generation timeout or retry is not justified by these probes. Do not add automatic resubmission, new request IDs, provider calls, or change backend completion decisions. Use request/revision guards for optional reads, including successive reads within the same conversation.

## Disposition of every reported finding

| Finding | Current conclusion | What can be fixed | What must stay unchanged |
| --- | --- | --- | --- |
| B-001: context-only follow-ups fail retrieval | Active retrieval starts with the current message. Conversation retrieval exists but is deliberately disabled; generation can still receive persisted history. No new dropped-history integration defect established. | Repair transport if a specific lost-history/ID defect is demonstrated; preserve history rendering. | Do not enable contextual retrieval, rewrite queries or change evidence selection. |
| B-002: failed calls displayed zero usage / not-called | Earlier lifecycle repair is deployed. Additional audit-input accounting and schema diagnostic fixes are locally validated in slide-codefix-002, not deployed. | Keep accurate incurred usage and bounded diagnostics while preserving the same withheld answer. | Do not accept rejected content or change admission, calls, repair limits or validators. |
| B-003: CSRF preview in Data Systems | Legacy preview is fixed synthetic content, not a stale course selector. All three built-ins are CSRF; different custom prompts yield the same response. Acceptance participates in publication gating. | Clearly label synthetic examples and prerequisites; accurately distinguish the existing generated preview feature. | Do not replace the preview generator, auto-accept examples, remove gates or rewire publication. Course-specific replacement changes behavior even without infrastructure changes. |
| B-004: course selection lost across professor navigation | Earlier selection preservation repair deployed and tested. | Retain account/course validation and regressions. | No new selection policy needed. |
| B-005: autonomy Save enabled before publication | Earlier disabled-state/prerequisite explanation deployed and tested. | Keep UI consistent with the existing backend prerequisite. | Do not permit unpublished autonomy or enable workers. |
| B-006: 14/84 safely withheld replies | Later eight-turn run localized one malformed re-audit and one audit provider-schema failure. The exact rejected schema field from those prior calls is not recovered. | Keep diagnostics/accounting fixes; investigate a concrete serialization or transport defect if evidence establishes one. | Do not weaken validation, alter prompts/models, add retries or claim a proven timeout root cause. |
| B-007: self-check falsely refused | Executed interpreter probe: “I will write my own assignment” matches `write my` in `_DIRECT_SOLUTION`. V3 action router itself does not reject that prompt; the graph interpreter marks a direct solution request and source-traced constraints impose refusal. | Retain the failing example and explain the limitation. | Changing even this regex changes which requests are refused; defer under the user's decision freeze. |
| B-008: confusing key-column wording | Archived model reply is ambiguous; no evidence the UI altered it. | Fix rendering only if a text discrepancy is reproduced. | No prompt change, output rewriting or untested quality claim. |
| B-009: praise disagrees with learner counters | Active default assessment uses lexical overlap, not tutor praise. API returns stored belief; prior checks matched displayed counters. Optional source/model assessors are not the selected default. | Fix stale/failed evidence loading (H-001/H-002); describe counters accurately. | No assessment replacement, threshold change, score inferred from praise or altered learner state. |

Legacy preview details: `src/digital_twin/onboarding/preview.py` defines a fixed source catalog and three CSRF cases. `release.py` requires accepted built-in and custom cases. The separate generated-preview path in `services/api/app/routers/publication.py` requires an owned session, approved policy and owned ingestion chunks. Simply redirecting approval to that path is not an equivalent UI repair.

False refusal details: `DeterministicTurnInterpreter` in `src/digital_twin/student/tutoring_graph.py` uses a phrase regex to set `direct_solution_request`; `_merge_action_constraints` translates that signal into refusal. This is a demonstrated decision-rule false positive, not an infrastructure bug. The active assessment in the same module uses the existing 0.45/0.20 overlap thresholds. Both remain frozen.

## Coverage still needing execution

The original ledger records 35 pass, 27 partial, 14 fail, 8 blocked and 22 not run out of 106 scenarios. Fourteen failed scenarios are not fourteen distinct defects, and are separate from the 14 failed generation turns. The 84-turn run is substantial longitudinal evidence but not complete feature certification.

| Group | Remaining verification / limitation |
| --- | --- |
| Chat interaction | Double-send, reload while pending, near-limit text; partial Enter/newline, multiline, draft and pending course-switch coverage. |
| Authentication | Remaining expiry/reset/revocation/back-navigation scenarios; do not infer browser passes from API tests. |
| Professor and publication | Ingestion retry/cancel, new publication, stale preview and release withdrawal paths; QA course publication was blocked by rejected legacy previews. |
| Sources | Injection and withdrawal lifecycle remain blocked/partial. Full source-text inspection is a feature gap, not proof that citations are incorrect. |
| Check-ins and governance | Delivery, kill-switch, consent and acknowledgement scenarios blocked by disabled worker configuration. Do not enable autonomous behavior to manufacture coverage. |
| Recovery | Disconnect, same-ID retry, failed auxiliary read, host restart/restore, concurrent sessions; run locally with controlled failures. |
| UI accessibility | Remaining keyboard, back/forward, zoom and network-error cases. |

Existing automated tests cover duplicate/concurrent IDs, persisted conversations, release withdrawal, session revocation, ingestion retry/cancel and backup checksums. They are useful safeguards, not substitutes for unexecuted browser lifecycles. Professor action handlers also await refresh work; that is a follow-up liveness hypothesis, not another reproduced defect. Running ingestion cancellation restrictions protect an in-progress write and should not be casually changed.

## Recommended order

1. Repair H-001 and H-002 with focused deferred/failing-read regressions and stale-response guards. Verify normal completion and recovery locally, then rendered-browser repeated-turn and reload scenarios.
2. Retain locally validated accounting/diagnostic changes; give the legacy preview truthful labels without changing acceptance or generation.
3. Complete remaining local lifecycle/recovery tests with synthetic provider failures; classify any newly reproduced plumbing bug before changing code.
4. Keep decision-rule, retrieval, assessment, model-quality and publication-design findings as documented limitations for the slides or a separately authorized evaluation. Do not silently fix them in this coding-only batch.

No application code was changed by this investigation. AWS was not resumed or modified. Existing locally validated changes are not claimed as deployed. This review cannot promise zero bugs or identify the historical infrastructure hang without its request-level evidence.

## Subsequent implementation

H-001/H-002 and synthetic-preview labeling are now fixed locally in [walkthrough-codefix-004](../research/05_evaluation/walkthrough-codefix-004-results.md). The investigation above remains the historical pre-fix assessment. No decision-rule limitation was silently resolved or deployed.
