# Browser lifecycle run 001

**Decision: keep the three bounded coding fixes; refine demo readiness.** The seven-persona core journey completed: 84 student turns, each with a persisted tutor outcome, over three compressed visits per learner. This is **not a bug-free or full-lifecycle sign-off**: 14/84 replies failed verification, and publication/delivery/revision branches remain blocked or unrun.

The user restricted this work to coding bugs. Infrastructure topology, selected model route, teaching-policy design, context-retrieval flag, outreach worker and midnight shutdown were left unchanged. The [106-case ledger](aws-pilot-lifecycle-001-coverage.md) records **35 pass, 27 partial, 14 fail, 8 blocked and 22 not run**. These are scenario dispositions, not percentages of all possible behavior.

## Run identity and evidence

- Run: `aws-browser-lifecycle-001`, September 9, 2026, Singapore. Browser walkthrough started 22:37; the core learner histories run approximately 22:53–23:31.
- Browser: Codex in-app computer use; desktop 1280×720 and temporary mobile 390×844. Mobile override reset; final browser session signed out.
- Site: [AWS pilot](https://d3cccbyk2qjxd6.cloudfront.net), `ap-southeast-1`, AWS profile `digital-twin`.
- Revision: `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, **dirty** working tree. Existing unrelated work was preserved. Exact five runtime source hashes, release-manifest hash and images are in the [deployment record](../../reports/aws-pilot/browser-lifecycle-001-deployment.json).
- Route: `audited-presentation-v1`, V19 Luna-low generation / Luna-medium final audit; current-message retrieval; proactive worker disabled.
- Course corpus: repository-authored synthetic Data Systems outline and notes; published `demo-pilot-v1-systems-release-1`. Supplemental Browser Security checks use that course's own approved release. No real student data or private professor material was supplied.
- Design: [scenario catalog](aws-pilot-scenario-plan-2026-09-09.md) and [connected lifecycle](aws-pilot-lifecycle-simulation-v1.md), written before execution. The 84-turn sample is the planned seven-persona × three-visit × four-turn minimum, not a statistical power calculation. No random seed or independent repeats; prompts adapted to actual replies.
- Durable evidence: [84 exact prompt/reply outcomes and metrics](../../research/05_evaluation/records/aws-browser-lifecycle-001.json), [machine-readable coverage](../../research/05_evaluation/records/aws-browser-lifecycle-001-coverage.json). Private browser snapshots, screenshots, raw persisted histories and interrupted-attempt records remain under `output/browser-qa/lifecycle-001/`.

## Coding defects fixed and deployed

| ID | Baseline defect | Bounded fix | Evidence after deployment |
| --- | --- | --- | --- |
| B-002 | A failed generated answer became a graph fallback with `not-called` and zero usage, hiding the actual model call. | Preserve the failed trace/usage while discarding all rejected answer text. Show an explicit recoverable verification-failure message. Retain a bounded final-audit reason. | Deterministic returned-failure regression passed. All 14 live safe failures retained a real model and nonzero usage; rejected content was not shown. Professor Activity reports operational failures with accounting. |
| B-004 | QA course → Twin setup → Course delivery silently selected the first course. | Keep selection in the account workspace and revalidate it against authorized courses. | Browser returned to the QA course after setup/delivery navigation. Regression checks selection continuity and fresh-account reset. |
| B-005 | An approved profile enabled autonomy Save with no published release; API rejected the action. | Disable Save and explain the publication prerequisite. Backend gate unchanged. | Browser showed the prerequisite message and disabled Save on the unpublished QA course. Positive/negative component cases passed. |

CDK deployment and SSM activation succeeded. Activation command: `15059364-ed1f-4d01-b780-3d61f1a1ef80`. Initial readiness polling briefly saw connection refusal while the container started, then succeeded. API image `a7b906a07f29b34b9ab610216a59bd72a6aae3454fb73f2f343b7c823afbb679`; web image `ea70c444a49f2ed33eab480164403842f163551da2fdaea95578f89a4a01f31d`.

Pre-fix backup SSM `0724914a-de4a-4734-a9c7-1237e66cbffb` verified schema 19 and ten data files at `/opt/digital-twin/backups/pre-lifecycle-codefix-001.zip`. No restore drill is claimed. The EventBridge stop was read back as enabled for **2026-09-10 00:00 Asia/Singapore**; its one-off schedule deletes itself after execution.

## Sustained learner outcomes

| Persona | Turns / visits | Answers | Guiding questions | Safe failures | Other outcomes |
| --- | --- | --- | --- | --- | --- |
| Engaged | 12 / 3 | 9 | 0 | 3 | Continued an earlier custom practice question after sign-out/sign-in |
| Fast | 12 / 3 | 9 | 1 | 2 | Solved a harder variation and distinguished source support from unspecified SQL errors |
| Slow | 12 / 3 | 9 | 1 | 2 | Progressed from Ari to Bo and Cam using individual lookup steps |
| High forgetting | 12 / 3 | 7 | 2 | 2 | One generic clarification; memory cue and recall attempt retained |
| Misconception-prone | 12 / 3 | 11 | 0 | 1 | Reintroduced and corrected shared foreign-key versus duplicate primary-key confusion |
| Answer-seeking | 12 / 3 | 6 | 0 | 1 | Four graded-work redirects and one generic clarification |
| Low receptivity | 12 / 3 | 9 | 0 | 3 | Consent remained off; voluntary return and short closing preference exercised |
| **Total** | **84 / 21** | **60** | **4** | **14** | **4 redirects, 2 clarifications** |

All 84 core student turns and their tutor outcomes were corroborated by read-only authenticated API history checks. Original user conversations were not appended to. One extra turn entered the fast learner's QA chat during a return-login mismatch; it is retained but excluded from the 84 core turns. A separate accidental keys question in Browser Security was also retained/excluded. Four final supplemental turns covered privacy/instruction-injection and a two-turn HttpOnly/Origin explanation; these are outside the core table.

Generation trace latency across the 84 outcomes: median **8.81 seconds**, maximum **41.73 seconds** (includes deterministic outcomes). Recorded generation usage totals **485,400 tokens**, approximately **$0.180544** for entries with known cost; six deterministic outcomes have no cost estimate. This is not a total API-request/provider-billing reconciliation: planner calls, browser overhead and other operations are not included. Interrupted browser waits also make a complete end-to-end latency distribution unavailable. No memory benchmark was performed.

The 14 verification failures are **16.7% of this one adaptive run**. These observations are correlated across histories, not independent benchmark trials. No general population rate, confidence claim, human learning gain, mastery claim or model comparison is justified. Action labels do not score semantic correctness; the full independent 0–2 teaching rubric was not completed, so no aggregate teaching-quality pass is claimed.

## Professor-to-learner lifecycle

Maya created `QA Browser lifecycle-001 — Data Systems`, uploaded the synthetic outline and notes, completed the five onboarding answers, reviewed source/policy fields, rejected an unrelated built-in preview, and inspected a custom preview. The explicitly labeled expected-behavior teaching-profile preview was reviewed and approved. A genuine generated course preview and release approval were not passed by pretending that unrelated CSRF examples were valid Data Systems teaching.

The QA course therefore remains **unpublished**. One low-receptivity synthetic learner was assigned twice; the UI retained one membership. The course remained absent from that learner's available courses. Empty Markdown was rejected with “Text sources must be nonempty and contain no binary controls.” A subsequent valid duplicate source upload succeeded as a third explicitly named upload, preserving the original two.

Because QA publication was blocked, the learner journeys used the existing approved Data Systems demo release. This is a documented substitution, not completion of the fresh-course release loop. On returning to the professor view, Learners displayed actual recorded evidence and a cohort insight: **10 participating learners**, **8 learners / 15 confusion signals** in the displayed window, linked to `systems-notes.md`. These counts include prior synthetic activity and are not just the seven new journeys. Existing published-course proposals were inspected, not accepted/dismissed or used to silently revise materials.

Check-in Inbox, Goals and Settings were exercised. Engaged opt-in persisted; low-receptivity consent remained off through reload. Professor eligibility reflected those states, inactive membership, and the missing active autonomy policy. Goals and delivered actions remained zero; no worker heartbeat was recorded. **No real check-in delivery, reply-in-chat, cancellation, source withdrawal, v2 release or complete goal closure is claimed.** These need an eligible QA lifecycle/worker or isolated test track. Enabling those would exceed the preserved live configuration.

## Chapter dispositions

| Chapter | Disposition | Evidence / boundary |
| --- | --- | --- |
| LIFE-01 | Complete | Maya created a persistent QA draft; Daniel's ownership list excludes it. |
| LIFE-02 | Partial | Two initial uploads plus explicit duplicate succeeded; empty upload rejected and recovery succeeded. Excluded-source and job-cancellation branches not completed. |
| LIFE-03 | Partial / blocked | Interview and expected-profile review exercised. Real course-specific generated-preview approval blocked by existing preview design. |
| LIFE-04 | Partial / blocked | One synthetic learner assigned idempotently; draft remains unavailable. Seven-person enrollment/publication/stale-check path not completed. |
| LIFE-05 | Executed with failures | All seven first visits completed on the existing published demo release, with failures retained. |
| LIFE-06 | Partial / blocked | Opt-in/opt-out and goal evidence views exercised. No approved active autonomy boundary/objective; goals/scheduling ineligible. |
| LIFE-07 | Blocked | No configured proactive worker; no actual delivery claimed. |
| LIFE-08 | Partial | All second visits resumed saved histories. No delivered check-ins exist for reply/read/dismiss branches. |
| LIFE-09 | Partial | Professor observed real participation-derived aggregate and evidence. Existing published-course proposals left unchanged. |
| LIFE-10 | Executed with failures | All seven third visits completed; 84 total core turns. No manufactured mastery or goal completion. |
| LIFE-11 | Blocked | Genuine QA publication prerequisite unresolved; no v2 release or source-withdrawal transition. |
| LIFE-12 | Partial / blocked | Low-receptivity opt-out retained and sign-out/reload checked. No eligible goals/delivery to close; isolated rollback/restore not run. |

## Remaining findings and scope boundaries

| ID | Finding | Classification / decision |
| --- | --- | --- |
| B-001 | Context-only follow-ups can get no-evidence or a generic clarification. | Existing current-message retrieval behavior. Context-retrieval candidate deferred by the user's coding-only constraint. |
| B-003 | Built-in onboarding previews teach CSRF in the Data Systems setup; custom preview is a generic policy placeholder. | Existing prototype preview design. Rejected, blocking fresh QA publication; no architecture/prompt replacement. |
| B-006 | 14 ordinary core turns were safely withheld. | Operational generation/audit outcome. All recorded reasons are `contract_or_provider_failure`; the exact provider/contract root cause is not proven. Do not label all as timeouts or silently weaken validation. |
| B-007 | An allowable closing self-check request mentioning the assignment still got a graded-work redirect. | Existing policy/router behavior. Recorded; no policy change. |
| B-008 | A guiding question ambiguously described Members.member_id 2 matching Teams.team_id 10; the learner corrected the columns next turn. | Model-generated teaching wording, not a proven code defect. Preserve as source/teaching failure evidence. |
| B-009 | Learner evidence can report incorrect/partial or unassessed observations despite correct-looking conversational feedback. | Assessment-quality limitation requiring its own comparison. Not a grade or proof of learning; assessment implementation unchanged. |

The coding-fix gates passed: safe failed text handling, preserved provenance, selection continuity, explicit prerequisite, and no observed authorization/persistence regression. The larger demo-readiness gate fails due to unresolved reply failures and incomplete lifecycle branches. This run selects **no new architecture, provider, model, algorithm or release profile**.

## Validation and retained unsuccessful attempts

- Backend: **60** targeted governed-autonomy/audited-generation/pilot tests passed; **109** API tests passed for student, outreach, text ingestion, authentication, publication and teaching authority.
- Frontend: **89 tests in 18 files** passed; production build and lint passed. Existing large-bundle warning remains.
- Infrastructure: **7 tests** passed. CDK diff was limited to deployment document/image references, with no topology or schedule change.
- `npm run check` was attempted but stopped in `check:docs` at two pre-existing missing Desktop presentation links in `docs/final-report-vs-latest-slides-2026-09-09.md`. Downstream checks in that command did not run; this is not an all-green repository check.
- Two test-authoring failures were fixed before passing: unsupported hook-harness `unmount`, and a regex matching CSS `disabled:` instead of the disabled attribute.
- Several computer-use waits timed out or reported detached elements while requests were still running. Fresh UI reads confirmed completion; no blind message resubmission. Browser autofill/form entry also caused a return-login mismatch, recovered with explicit select-all typing and visual email verification. API ownership checks confirmed separate account histories; this is not evidence of an application authorization leak.
- An initial supplemental API login without the required Origin header was rejected with 403. Repeating with the normal same-origin header succeeded. A stale browser-recorded conversation ID caused another 403; ownership-resolved API history reconciliation corrected the evidence mapping. Neither was counted as a product pass or data leak.
- Final captured browser console warning/error list was empty; intentional API validation failures and unavailable telemetry are not erased by that observation.

## Reproduction and evidence handling

Recompute the summary without sending messages or calling a model:

```sh
uv run python scripts/summarize_browser_lifecycle.py \
  --input output/browser-qa/lifecycle-001/api-histories.json \
  --metadata reports/aws-pilot/browser-lifecycle-001-deployment.json \
  --output research/05_evaluation/records/aws-browser-lifecycle-001.json
```

The private input is the authenticated read-only history snapshot. The summarizer selects the exact synthetic first-prompt anchors, requires twelve ordered student/tutor pairs per persona, excludes the extra return-login turn, and emits inspectable per-case text and metrics. It never generates additional evidence. Credentials remain in ignored local files and are excluded from reports, records and screenshots. The older private ledger is retained as `ledger-before-reconciliation.json`; corrected ownership mappings do not overwrite the failed-attempt history.
