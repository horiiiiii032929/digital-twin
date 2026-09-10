# Slide-aligned coding fix plan

Scope update, 10 September: the user now requires fuller AWS coverage of the latest slide demonstrations, including check-ins. See [latest-slide functional completeness requirements](2026-09-10-slide-complete-aws-requirements.md). This earlier coding-only plan remains the historical boundary for its repair runs; its worker exclusion is not the acceptance scope for the new completeness work.

Status: **Alignment inspected; implementation plan only.** No new application code, algorithm, model, policy or deployment change is made by this plan. The latest slides are a mandatory compatibility constraint for every subsequent fix.

## Authoritative presentation

Inspected the actual **70-slide** Desktop presentation, *Architecting a Digital Twin for Scalable, Style-Aligned Instructor Presence*, saved September 9, 2026 at 16:49 Singapore. Its SHA-256 is `7453cff7de77b597a61abc39766e3cb948ab2f0b3083d9b835a2a91dcb6f6d76`.

Source: `/Users/hikaru/Desktop/Course Digital Twin — Final Presentation/Course Digital Twin.pptx`. This fingerprint matches the [previous report/slides comparison](../../docs/final-report-vs-latest-slides-2026-09-09.md). Earlier 60/61-slide packages and repository copies are not substitutes. Text and speaker notes were extracted; the governing slide passages and architecture/audit/assessment diagrams on slides 9, 32, 44 and 47 were inspected directly. Embedded videos were not replayed frame by frame in this comparison.

The slide deck describes a mixture of implemented contracts, recorded demonstrations, retained controls, experimental options and future comparisons. Compatibility means preserving each item's stated role and behavior. It does **not** mean enabling every experimental component or claiming that every recorded demonstration is active in AWS.

## Alignment conclusion

The current AWS answer path is compatible with the presentation's **audited teaching candidate**, not a promotion of that candidate to the retained research default. A fresh read-only runtime check returned `question-specific-profile-grounded-v19`, `gpt-5.6-luna`, `v19-luna-luna-medium`, `GuardedPolicyValuePlanner` and `governed-autonomous-tutoring-graph-v2.1`. This agrees with the [explicit AWS demo profile](../05_evaluation/profiles/aws-presentation-demo-v1.json) and slides 13–14, 29–36 and 68.

The three deployed coding fixes also preserve those contracts: retaining failed-call accounting, keeping the selected authorized professor course, and disabling a save whose publication prerequisite is missing. They do not change retrieval, generation, audit decisions, learner assessment or autonomous action selection.

**The deployment is not fully identical to the slide demonstrations.** Record these differences rather than silently changing them:

| Area | Slides | Current pilot / implication |
| --- | --- | --- |
| Teaching corpus | S4, S10–13 use approved private IT5004 lecture material and prepared excerpts. | AWS uses authored synthetic Data Systems and Browser Security notes. Same intended evidence/release contract, different content. Do not copy private lecture material to AWS to force visual equivalence. |
| Response notice | S32 says “I could not verify this response.” | Current UI says the tutor could not produce a verified reply, the message is saved, and to try again. Wording differs; withholding semantics agree. Exact wording parity is a separate optional copy-only decision, not a validator change. |
| Background support | S38–43 show working scheduled/event-driven paths, including a recorded virtual-time replay. | Pilot has no worker heartbeat, no active course autonomy policy and zero delivered actions. Full live check-in equivalence is unverified and currently unavailable. Worker activation is outside this coding-only plan. |
| Assessment | S44 explicitly shows a saved reply and conversational “Yes” with NOT_ASSESSED and an active goal. S46 presents the corrected model assessor as an experimental option. | Similar conversational/assessment disagreement is not automatically a wiring bug. Current runtime returned `learning_configuration: null`; the deployment record retains the base learning path. Do not enable the optional assessor or manufacture assessed results. |
| Onboarding preview | Recorded slide demonstration reviews a prepared configuration. | Fresh Data Systems setup still exposes unrelated legacy CSRF fixtures/generic custom previews. This blocks the new QA publication story. No evidence that replacing this with a new preview engine is a small bug fix. |
| Research results | S33–35 and S48–56 report separate, bounded studies. | The 84-turn AWS QA run is new adaptive synthetic behavior testing, not a rerun or replacement of those results. Keep all existing qualification limits. |
| Operations | S65 reports historical local qualification. | AWS hosting and the user-requested one-off **03:00 September 10 Singapore** stop are separate operational choices, not new teaching algorithms. |

Evidence: [browser lifecycle report](../../tests/manual/aws-pilot-lifecycle-001-results.md), [84-turn record](../05_evaluation/records/aws-browser-lifecycle-001.json), [deployed source fingerprints](../../reports/aws-pilot/browser-lifecycle-001-deployment.json). The slides and their research numbers will not be edited to make the software appear to pass.

## Mandatory invariants

| Preserve | Slide authority | Fix boundary |
| --- | --- | --- |
| React → FastAPI → Python domain/services, SQLite/shared records, course files, separate workers and model adapter | S7, S9 | No topology, database or orchestration replacement. |
| Published course/source scope, versioned citations and permission checks | S10–11, S17–22, S27 | No retrieval/ranking/chunking change, stale-source acceptance or unapproved profile fallback. |
| Three distinct answer paths and retained comparison controls | S14, S36, S68 | No silent default/profile promotion or route substitution. |
| Luna low for planning/drafting; Luna medium for final audit/quality repair | S13, S36 | Preserve model IDs and reasoning settings. Mini is the separate experimental evaluator, not a runtime tutor stage to add. |
| Rendered-answer audit, evidence/context binding, required complete fields and permitted source IDs | S29, S31–32 | No accepting malformed output, dropping fields, bypassing hash checks or treating a provider error as an approved answer. |
| One eligible **quality** repair followed by re-review; withhold if review cannot reliably pass | S32 | No extra retry loop or unconditional regeneration. Preserve existing structural-protocol repair separately; do not confuse it with the quality-repair allowance. S13's two calls describe one saved turn, not all possible turns. |
| Conversation, assessment, prediction and timing remain distinct | S44, S46–49, S69 | No turning tutor praise or message count into an assessment. No new attempt detector, assessor, Count/Decay/BKT/PFA selection or timing method. |
| Goal completion requires its own committed objective/concept evidence | S45, S53–54 | No threshold relaxation, cross-concept completion or uncommitted observations. Keep optional recovery-aware logic unselected. |
| Code authorizes model proposals, consent, membership, release, evidence, timing, frequency and delivery | S40–43, S55, S65 | No new authority for the model, duplicate delivery or server-gate bypass. |
| Phrase-based difficulty signals, five-distinct-learner aggregation, fixed suggestions and explicit professor decision | S61–64 | No LLM classifier, changed phrase rules/thresholds, smaller group disclosure or automatic course rewrite. |
| Experimental and educational claims remain qualified | S28, S33–36, S46–52, S67–70 | No bug-free, instructor-fidelity, learning-benefit or production-scale claim from this repair run. |

A proposed diff must cite the invariant it preserves and the coding defect it repairs. If it changes any decision rule, prompt behavior, selected component, threshold or model route above, remove it from this plan and record it as separate experimental work. Do not treat a feature flag as harmless merely because changing it is one line.

## Prioritized work

### P0 — Find the exact failure before changing behavior

**Decision question:** are any of the 14 safe failures caused by incorrect application plumbing, or are the unchanged provider/audit contracts correctly withholding invalid responses?

Control: the exact deployed manifest in the lifecycle record. Prediction: bounded diagnostics can identify the failing stage without changing any returned answer, action, evidence, assessment, state revision, provider call count or cost. Alternatives are (a) diagnostics only, (b) a minimal proven contract-plumbing correction, or (c) preserve withholding and record a model/contract limitation. No alternative model or audit design is proposed.

1. Trace draft validation, final review, eligible quality repair and re-review separately. Inspect existing structured events before adding fields.
2. If necessary, retain only bounded diagnostic codes: stage, known exception class, validated field path/error code, role/model identity, call count, usage and existing correlation IDs. Do not persist raw provider text, private source excerpts, prompts, chain-of-thought, tokens or credentials in public logs.
3. Distinguish provider timeout/availability, malformed schema, provider identity, missing field, source/reference binding, incomplete audit coverage, rejected quality review and rejected repair. Unknown stays unknown.
4. Reproduce each confirmed coding cause with a deterministic recorded/synthetic fixture. Repair only incorrect field mapping, serialization, argument passing, binding or exception/usage propagation. Keep genuinely invalid input invalid.
5. If no application defect is demonstrated, keep the safe failure. Do not change prompts, thresholds or retries to reduce the headline failure count.

Likely inspection points: `src/digital_twin/generation/audited_instruction.py`, `final_response_audit.py`, `contract_repair.py`; the provider adapter; graph fallback and reactive trace transport. These are candidate inspection locations, not permission to rewrite their algorithms.

### P1 — Verify assessment record transport, not assessment accuracy

**Decision question:** does the UI faithfully display the persisted result for the correct account, course, release, conversation, message and concept?

S44 changes the interpretation of the earlier bug list: correct-sounding conversational feedback plus NOT_ASSESSED is an explicitly demonstrated limitation, not proof of a broken record. The investigation must first compare the stored observation, API DTO and rendered view.

- Check identity keys, ordering, revision handling, enum mapping, counters, zero/null distinctions and stale asynchronous responses after account/course switches.
- Fix a display/transport discrepancy only when the persisted correct result is misrepresented or attached to the wrong scope.
- Retain NOT_ASSESSED, uncertainty and conflicting evidence accurately. Never recompute a better-looking assessment in the frontend or derive it from the tutor's prose.
- If the stored assessor result itself is wrong or attempt detection misses natural language, record it for the separately described S46/S62/S70 experimental work. No detector/assessor replacement in this patch set.

### P1 — Complete ordinary coding regressions

Use the [existing 106-case ledger](../../tests/manual/aws-pilot-lifecycle-001-coverage.md) to select incomplete integration branches, not to invent a new architecture:

- Duplicate submissions and same-request-ID retries: one logical committed turn.
- Pending reply reload/reconnection: recover the committed result without silent resubmission or cross-chat attachment.
- Account/course switching while reads are pending: no stale identity, source, history or assessment display.
- Source upload errors and retry/cancel paths where the UI actually supports them: accurate status and no false success.
- Profile/release prerequisites and stale approval checks: correct version remains active; old history stays bound to its release.
- Existing three fixes: retain truthful failure accounting, course selection and invalid-save prevention.

Use isolated deterministic transports for injected errors and concurrency. Do not interrupt the user's live server or activate background delivery to exercise an otherwise unavailable branch.

### P2 — Recheck slide compatibility and release the bounded patch

For each accepted coding fix: record before/after behavior, its slide contract, smallest changed files, deterministic regression and live retest. Compare the final patch against the **deployed dirty manifest**, not HEAD alone, because the repository contains unrelated pre-existing work.

Recheck model roles, route, prompts, feature flags, profiles, permission boundaries, audit repair bounds and goal/signal rules. Any change beyond the approved coding purpose blocks this patch's release. Preserve backups, accounts and histories. The current one-off stop remains 03:00 Singapore; do not change it during repairs.

## Evaluation protocol and gates

Version the new regression set as `slide-aligned-codefix-v1`. Start from the exact synthetic failures and successful controls in the 84-turn record; add minimal deterministic fixtures for normal, boundary, adversarial, no-evidence, privacy and provider-failure cases. Do not relabel all 14 withholdings as defects: the expected output depends on whether the underlying response was valid.

Before running a candidate, write the expected action, state change, assessment and allowed provider calls for every case. Retain successful and unsuccessful attempts. Diagnostics-only work must produce identical decisions and calls on identical deterministic inputs. A behavior-changing plumbing repair must change only its identified failing cases while leaving every unaffected control invariant unchanged.

| Gate / metric | Required result |
| --- | --- |
| Invalid provider/audit output | Still withheld; no unvalidated content or fake citation reaches the student. |
| Proven serialization/mapping defect | Minimal fixture fails before and passes after; correctly bound valid data reaches the unchanged contract. |
| Usage/provenance | Real usage survives failures; no duplicate counting; unavailable values remain explicit. |
| Assessment transport | Persisted and displayed scope/outcome/counters agree; NOT_ASSESSED remains distinct from incorrect and from correct. |
| Identity/state/privacy | Zero cross-account/course/release writes, unexpected progress, private disclosure or unauthorized delivery in relevant cases. |
| Idempotency/recovery | One committed logical turn/delivery; bounded retry, no silent duplicate request. |
| Algorithm preservation | No selected model/route/prompt/ranking/assessment/goal/classification/timing change; no increase in repair allowance. |
| Operations | Record browser latency, stage latency, actual provider calls, token/cost usage and unknowns; do not present generator accounting as the complete bill. |
| Slide claims | Existing measured results and limitations unchanged; current operational differences explicitly documented. |

Run the affected component/API tests, relevant frontend tests, lint/build and infrastructure assertions. Run the repository check and report its actual result, including unrelated blockers. Use `scripts/summarize_browser_lifecycle.py` only to recompute the archived baseline; do not overwrite its failure evidence with new results.

After deterministic gates pass, use up to eight new synthetic live turns at first, covering affected failures and successful controls on the unchanged route. Inspect each result before continuing; record any provider/budget failure and do not reset counters to evade limits. A short retest is not an 84-turn repeat or a quality qualification. Expand only for an unresolved coding question with a recorded reason.

Record the patch run under a new stable ID in `research/05_evaluation/result-registry.md`, including code revision and dirty hashes, exact configuration, fixture version, expected/actual per-case results, latency/calls/usage, failures, limitations and Keep/Refine decision. Keep the original lifecycle baseline intact.

## Completion and stopping rule

A fix is complete when a reproduced **coding** defect has a passing regression, relevant browser behavior is verified, and its slide-preservation checks pass. The broad demo can remain imperfect because the slides themselves disclose open teaching/assessment questions.

Do not implement a “fix” that makes the system contradict the slides merely to make the test green. In particular: no bypassed audit, fabricated assessment, alternate model, new contextual retrieval, LLM difficulty classifier, changed completion threshold, automatically enabled outreach or rewritten professor materials. Those are separate decisions, not this coding plan.

## Execution: slide-codefix-001

The user approved execution on 10 September Singapore time. First candidate is
bounded audit diagnostic propagation only; control is the deployed dirty source
manifest copied to `output/browser-qa/slide-codefix-001/deployed-manifest.json`.
Prediction: deterministic audit decisions, requests, call counts and usage remain
identical, while quarantine traces retain a fixed stage and failure code. No raw
provider response, exception message or arbitrary field name enters the trace.
The synthetic `slide-aligned-codefix-v1` cases cover valid output, missing/duplicate
entries, binding drift, invalid references, factual bypass, missing dimensions,
provider identity/unknown usage/unavailability, malformed repair and re-audit.
Required gates are unchanged withholding and repair bounds, preserved usage,
private sentinel exclusion and exact trace propagation. Run existing integration,
idempotency, assessment/API and frontend regressions before considering additional
coding changes. This is a diagnostics decision, not evidence of semantic quality.

Execution refinement: the first new live turn exposed `reaudit_request /
malformed-response`; the second recovered. Preserve this initial candidate and
both outcomes. The refinement propagates the transport's already-existing,
allowlisted failure stages, including output limit and schema validation, through
the same diagnostic field. Keep all provider caps unchanged. The final bounded
live check uses seven turns in the new multi-turn chat (recovery, join reasoning,
recap, reload/return, misconception, privacy), then one fresh-chat replay of the
first failing question. Total remains eight; stop after that replay and classify
remaining uncertainty without increasing retries or changing the slide contract.
