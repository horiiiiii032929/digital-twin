# Root cause 007: why the walkthrough behaved unexpectedly

Decision: **Keep one additional diagnostic coding repair. Preserve current tutoring, assessment, publication and budget decisions.** This investigation traces the remaining lifecycle-local-006 findings to code and stored evidence; it does not certify all unexecuted browser scenarios.

The new defect was loss of the specific provider error before the final audit. The saved turn could say only `provider_or_schema_failure` even when the application already knew `budget-exceeded` or `timeout`. This is fixed locally. It does not make a withheld answer succeed, reopen the budget, change a prompt or activate check-ins.

Evidence: [plan](../04_experiments/2026-09-10-root-cause-007-plan.md), [machine record](records/root-cause-007.json), [original 80-turn browser result](lifecycle-local-006-results.md), [unchanged scenario ledger](../../tests/manual/lifecycle-local-006-coverage.md). Earlier failures are retained.

## What caused each observed behavior

| What the tester saw | Causal evidence | Conclusion and action |
| --- | --- | --- |
| Ordinary chat sometimes gives a generic withheld reply | Six audit responses failed hash-string schema validation; four had well-formed but mismatched binding values. Three quality repairs were rejected, one repair was unchanged, one audit timed out, and the next turn encountered the process guard. Exact turn IDs below. | Several distinct failures share one safe fallback. No hash-mapping/serialization defect reproduced in the control. Do not accept invalid audits or add retries. Specific pre-audit error loss was a coding defect and is repaired. |
| The app appears to hang, then responds late | A turn can include drafting, auditing and bounded repair/re-audit. Prior stored turn traces reached 46.7 seconds, while individual requests retain the existing 30-second timeout. Separately, citation fanout locally delayed sign-out and was reproduced/repaired in run 006. | Provider latency and browser connection starvation are different causes. Citation repair remains; provider limits unchanged. Historical AWS hang has not been diagnosed on AWS. |
| Every later attempt fails after one timeout even though spending looks low | `BudgetedLlmClient` retains unknown cost/reservation and sets `cost_reporting_failed`. Admission checks that flag before new calls. Recorded timeout was followed by that state at 198/250 calls, USD 0.210664 reported cost. | Intentional fail-closed accounting, not an exhausted USD 5 allowance. No restart/reset to evade it. New diagnostic distinguishes the rejection. A different recovery policy is a separate operational decision. |
| Tutor repeats basic questions despite correct-looking answers | Both draft and audit receive recent history. A new seven-turn selected-V19 control confirmed the latest ten messages, exact role translation and context/rendered hashes; no history disappearance was reproduced. The application attempt flag is assessment-derived, not inferred from conversational praise; the current prompt/model may still repeat checks. | Repetition is an observed teaching-quality limitation. A ten-message window also limits older context. Changing history length, attempt inputs, prompts or teaching selection changes behavior; deferred. Not every repeated answer's internal cause can be established from a saved response. |
| Many observations, few assessments, high uncertainty | Recomputed the current deterministic interpreter, concept selection and assessment rules on all 80 stored inputs: every stored attempt flag and outcome matched. 61 were not recognized as attempts; 19 were. Final observation outcomes: 65 not-assessed, 12 incorrect, 2 partial, 1 correct. | No stored-data/transport discrepancy found. These are lexical rules, not a semantic grading system. Some natural-language answers do not match attempt cues, some concept matches tie, and word overlap may disagree with the tutor's praise. Do not change the scorer or manufacture mastery. |
| A correct assessment exists but progress does not advance on a failed turn | The atomic commit boundary keeps prior belief when the turn fails validation. Of 64 non-withheld turns, stored outcomes were 54 not-assessed, 8 incorrect and 2 partial. The sole correct observation was in a withheld turn, so it did not become committed correct evidence. | Required separation between provisional observation and committed progress. Retain it; do not count failed delivery as accepted learning evidence. |
| Seven learners but no professor insight | Eight signals occupy four topic/signal groups with distinct-learner counts 1, 1, 4 and 1. The maximum is four, below the five-person threshold. The aggregate groups actual signals, not enrollments or total course participants. | Expected suppression. C008 previously fixed the explanation only. No threshold reduction or synthetic proposal insertion. |
| Fresh professor previews discuss CSRF after Data Systems documents are uploaded | `onboarding/preview.py` contains fixed Sprint 1 CSRF examples. Custom previews use policy boilerplate. That path is not generated from uploaded course chunks; actual generated teaching previews are a separate gated path. | A real prototype limitation, not evidence the upload was lost or the wrong course was selected. Replacing the preview engine changes the workflow/content. Unsuitable previews stayed rejected, so positive publication was not established. |
| No goals or delivered check-ins | Preserved runtime has proactive worker disabled, no active autonomy policy, no eligible goals/triggers/deliveries in this fixture. Student consent alone cannot create an eligible autonomous action. Ingestion and proactive workers have different jobs. | Expected current configuration. Do not activate a worker or invent deliveries to claim lifecycle completion. Existing API/domain tests are supplementary only. |
| Internal source label “S1” appears in an explanation | Generation uses bounded evidence aliases `S1`, etc.; the model copied one into prose at turn 26. Citation mapping remained server-owned and inspected source claims remained separate. | Model prose artifact, not proof of failed citation mapping. No postprocessing that changes the audited rendered answer. |
| “Write my” can trigger a refusal too broadly | Existing phrase-based routing/intent rules match that phrase. Refusal and permitted-hint recovery were seen; the historical false positive remains documented. | Existing decision boundary. Refining the classifier changes policy behavior and needs separate evaluation. |
| Bad PDF stays failed after Retry | Empty/invalid header files were rejected; a header-valid but structurally broken PDF reached parsing and failed again on the same bytes. | Correct failure/retry behavior for the synthetic broken file; no parsing success should be fabricated. |
| Rate limits appear during fast browser testing | Configured login/authenticated-request limits were crossed. The eleventh bad login returned a limit message; login later recovered. Professor partial reads recovered with manual retry. | Expected configured throttling. No limit increase. Earlier citation concurrency repair reduces primary-operation contention, but is not an exemption from rate limits. |
| Draft disappears on course switch / professor reload starts at first course | Explicit frontend reset/default-selection behavior. No misdirected write was observed. | Usability limitation, not silently repaired as an algorithm defect. Persistence redesign is not part of this patch. |

## Why hash failures were not bypassed

The server makes a snapshot containing the exact proposal, rendered reply and public evidence/context. It computes SHA-256 bindings and supplies the values to the auditor. The auditor must echo them. The response is validated first for schema and then for exact binding/entry coverage. The schema adapter deliberately sends a portable shape schema and retains stricter pattern/semantic validation locally. A structured JSON response can therefore still fail the local hash pattern or binding check.

The repeated offline control exercised the real selected V19 generator path with injected valid audit output and Unicode text. It passed seven turns, including the ten-message history boundary. Existing invalid-binding/schema, repaired-output, unknown-usage and identity controls also passed: valid output stays valid; invalid output stays withheld. This supports correct plumbing for those cases. It is **not** proof that a provider can never return an unexpected payload, nor does it prove the precise character error in a historical response. Raw historical audit output/quality verdict detail was not retained in the bounded persisted trace. Exact semantic reasons for the three rejected repairs cannot be reconstructed from a generic `repair_rejected` reason.

Historical failed turn classification:

- Hash pattern/schema: 10, 33, 62, 66, 70, 78.
- Audit binding mismatch: 5, 11, 20, 42.
- Rejected quality repair: 2, 49, 60.
- Unchanged quality repair: 58.
- Audit timeout: 79.
- Subsequent budget guard: 80, confirmed through the recorded process metrics rather than its previously generic trace.

A proposal to reduce these failures must evaluate the model/protocol and preserve exact answer/evidence binding. Replacing model-echoed values with server values after a mismatched review would conceal the failure and violate the current slide contract; it was not done.

## The additional coding repair: C009

File: [audited_instruction.py](../../src/digital_twin/generation/audited_instruction.py). Errors during final audit already carried bounded diagnostic codes. Errors before that branch fell through the generic compact-proposal failure path, dropping an available typed provider code. Consequently the known turn-80 guard rejection looked like an unspecified provider/schema failure.

The non-audit `LlmError` branch now appends `generation_failure=<allowlisted code>` using the existing bounded classifier. No raw exception messages, private values, arbitrary stage names or model response text are exposed. Existing final-audit diagnostics stay unchanged. Returned content, action, usage, citations, provider provenance and request/call behavior are unchanged.

Five deterministic failing baselines are retained in `output/browser-qa/root-cause-007/diagnostics-before.log`. They cover budget, timeout, unavailable, schema-validation and an arbitrary/private stage. The post-fix test compares the complete answer object against the pre-fix control except diagnostic text, compares exact request payloads and counts, and checks private sentinel exclusion. A separate graph test verifies the new budget code survives persistence with one saved student/reply pair and no extra generation attempt.

This repairs observability, **not the underlying provider failure or recovery design**. No new response/status API or database migration was added; the existing trace field holds the bounded code.

## Configuration and verification

Revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty workspace. The authoritative Desktop deck was rehashed and still equals `7453cff7de77b597a61abc39766e3cb948ab2f0b3083d9b835a2a91dcb6f6d76`. The selected AWS presentation profile is unchanged. Of 328 tracked decision/control file hashes, 327 are identical; the sole change is the documented diagnostic branch in `audited_instruction.py`. Model roles, prompt strings, task routing, evidence/assessment algorithms, source selection, publication and budget gates remain unchanged. This is a diagnostics exception to the file fingerprint, not a component promotion.

All work in this run was offline/read-only evidence inspection or injected-client testing: **zero paid model calls, zero AWS operations, no deployment, no API restart to evade the old budget guard.** The previous browser record supplies actual-use evidence; no new browser lifecycle pass is claimed for the offline controls.

| Check | Result |
| --- | --- |
| Initial diagnostic reproductions | 5 failed as expected before fix; preserved |
| Final diagnostics/context/audit/generator/repair/source-state suite | 107 passed |
| Budget/transport/governed autonomy/goal/API/runtime configuration suite | 158 passed |
| Onboarding/publication/proactive outreach API suite | 35 passed |
| Stored-observation replay | 80/80 attempt flags and assessment outcomes match current rules |
| Seven-turn context/binding control | Passed with deterministic injected clients; not measured model quality |
| Diff whitespace check | Passed |

Total final test invocations above: **300 passing tests**, with existing SWIG deprecation warnings. An initial lifecycle-test command used nonexistent `test_proactive_api.py` and collected no tests; the corrected `test_proactive_outreach_api.py` command passed. Both logs remain. The full repository lint/build/check was not rerun for this Python-only diagnostic patch; run 006's frontend/build results and unrelated documentation-link failure remain as previously reported.

No dataset, split, rubric, scoring threshold or historical evaluation result was edited. The 80-turn replay tests reproducibility of existing rules, not whether those rules correctly assess learning. No research quality or learning-effectiveness promotion follows from these controls.

## Remaining uncertainty

The application is not certified bug-free. Exact historical raw auditor mistakes, the semantic cause of each repetitive response, positive fresh-course publication, real check-in delivery and closure, the original AWS hang, concurrent independent browser sessions and the other unexecuted scenario branches remain unverified. Fixes to the three reproduced application defects across runs 006/007 are locally validated; they do not turn those gaps into passes.
