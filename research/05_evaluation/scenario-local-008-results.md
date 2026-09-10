# Scenario local 008: paid browser recovery follow-up

Run: 10 September 2026, Singapore. **Keep the two reproduced frontend recovery repairs. Full professor-to-check-in readiness is still incomplete.** No deployment, AWS operation, algorithm change or approval bypass occurred.

[Plan](../04_experiments/2026-09-10-scenario-local-008-plan.md) · [machine record](records/scenario-local-008.json) · [coverage additions](../../tests/manual/scenario-local-008-coverage.md) · [combined test summary](../../docs/application-test-summary-2026-09-10.md).

## Configuration and method

The user explicitly authorized paid calls. This was a new isolated synthetic fixture and single API process, not a reset of run 006's failed accounting guard. Runtime identity was compared against the archived AWS configuration: audited-presentation-v1, v19-luna-luna-medium, question-specific-profile-grounded-v19, Luna low planning/drafting and medium audit/repair, existing 3000-token caps, governed graph v2.1, dominance-scoped-ambiguity-safe-v3 evidence gate. Learning configuration remains null and the proactive worker remains disabled. The authoritative 70-slide deck SHA-256 remains `7453cff7de77b597a61abc39766e3cb948ab2f0b3083d9b835a2a91dcb6f6d76`.

Code revision and dirty state are in the machine record. This inherits substantial earlier uncommitted work. All 328 frozen controls match run 007's final state; its two added diagnostic/context test files also match (330 checked paths). This batch changes frontend recovery and documentation, without changing backend request fields, schema, retrieval, prompts, assessment, release selection or evaluation thresholds.

A fresh demo-pilot-v1/seven-personas-v1 fixture supplied synthetic approved Data Systems and Browser Security notes. Fourteen seeded starter messages were excluded. Eight initial targeted turns were extended by a cross-course request and a disconnected-send recovery. These ten adaptive, correlated examples are an operational regression sample, not a statistically representative teaching-quality evaluation. No quality benchmark split, rubric or historical result was altered.

The first nine turns used the in-app browser. The CUA tool then repeatedly timed out, including read-only calls. The final turn used a headed Playwright browser, with a separate professor context. Neither API-only checks nor seeded published controls establish successful fresh-course publication.

## Reproduced coding defects and repairs

### C010: interrupted sends lost their recovery state on reload

Before the repair, reloading during a paid response left an empty conversation while the server later committed both messages. The UI did not recover until another reload. Three desired-behavior hook regressions failed before implementation.

The frontend now stores only the pending request in tab-local session storage, keyed by account and conversation. A reload restores the unsatisfied draft and offers manual Try again with the original request ID. If saved history already contains the linked reply, it clears the marker. It never automatically starts another tutoring request. Completed sends clear the marker; blocked storage does not prevent ordinary sends. Outreach reply association is retained without changing its permissions or payload.

The error heading is now “The reply was not confirmed,” which accurately covers an uncertain server outcome. A paid in-flight reload retest restored the draft; manual recovery displayed the completed reply. Database reconciliation found one student message and one linked response for that request, not duplicate writes. A separate offline-before-send test retained the draft and recovered after reconnection.

### C011: expired sessions left users stuck in the protected workspace

With a valid local session-expiry fixture, a protected request returned 401 but the student remained on a failing Retry course screen. One new auth regression failed before implementation.

Protected API reads now report session expiry to the auth controller, returning the UI to sign-in with an explanation. Authentication revisions reject late 401 responses from an earlier identity/session. Login/password errors and authorization 403 responses do not spuriously expire the workspace. Clean-reload browser retesting showed the intended sign-in recovery. Targeted tests cover shared professor/admin requests, student requests and stale responses.

## Browser observations

Ten new requests produced six answers, two no-evidence responses, one clarification and one withheld safe-graph-failure. All ten request IDs are unique and each has exactly one linked response. These counts describe actions, not rubric passes.

- The original complaint/“why ?”/broad-key-takeaway chain still produced no-evidence, clarification and an answer respectively. Context-only questions remain awkward under the preserved design.
- Multiline SQL with Unicode completed and rendered after a withheld turn, demonstrating recovery to a later useful reply.
- The HttpOnly-to-CSRF follow-up continued the same course discussion with citations.
- Asking Data Systems to use Browser Security notes produced a no-evidence response identifying the course boundary.
- A request to expose hidden instructions or another student's conversation was withheld after `audit_validation / support_references`. No requested private content appeared. Withholding is correct; this does not demonstrate a useful conversational response or exhaustive privacy coverage.
- Automation supplied an 8001-character draft; the API rejected it with 422 and retained the draft, without generation. This does not claim ordinary typing bypasses the HTML length limit. A valid near-limit request remains untested.
- Independent professor/student browser contexts retained distinct identities; student sign-out did not transfer its identity to the professor context.
- Mobile 390×844 chat, composer and Sources panel were inspected. Escape dismissed Sources and Shift+Enter inserted a newline. The full keyboard/focus/Enter and 200% zoom matrix is still incomplete.

## Verification and costs

- Frontend: 116 tests across 20 files passed, including pending storage, reload recovery, session expiry and stale-auth regressions.
- Relevant API auth/student/governed tests: 115 passed, with five existing SWIG deprecation warnings. Earlier targeted idempotency checks also passed; overlapping counts are not summed.
- Frontend lint and production build passed. The existing approximately 550 kB bundle warning remains.
- `git diff --check` passed.
- Provider accounting: 20 completed calls, zero failed provider calls, 48,899 tokens, reported USD0.0189028, zero unknown-cost calls, no cost-reporting failure, peak concurrency one. A successful provider call can still yield an application-level audit rejection. Existing process limits remained 250 calls/USD5/concurrency5; no reset or automatic retry was added.
- Full `npm run check` is **not green**. Two preexisting external Desktop Markdown-link blockers were converted to literal path references, preserving presentation claims. The check now passes documentation verification and stops at execution-freeze coverage: `scripts/build_professor_evidence.py` and `scripts/finalize_professor_evidence.py` lack the expected guard. This separate packaging/validator issue was not bypassed, and downstream stages are not claimed to pass.

## Failed attempts and evidence limits

Retained local evidence lives under ignored `output/browser-qa/scenario-local-008/`; browser fallback artifacts are under `output/playwright/scenario-local-008/`. The durable machine record contains sanitized questions/responses, configuration and accounting, not passwords or provider keys.

Key evidence: `pending-before-reload.txt`, `completed-but-not-visible.txt`, `recovery-before.log`, `paid-pending-recovery.txt`, `manual-recovery-result.txt`, `session-expired-valid-before.txt`, `auth-before.log`, `session-expired-clean-retest.txt`, `sql-unicode.txt`, `security-followup.txt`, `cross-course.txt`, `metrics-final.json`, and the final test logs.

The first expiry injection used a timestamp earlier than session creation, causing fixture-validation 500; it was corrected before reproducing the actual 401 defect. Mid-edit React hot reload retained an old auth subscription and later produced a hook-order failure; clean page reload recovered. These failed development observations are retained and are not clean-build production reproductions. CUA timeouts and a stale Playwright element reference also interrupted testing; neither establishes an application defect. Offline network/auth errors mean this was not a clean-console run.

Fresh professor upload-to-publication, revision publication, actual delivered check-in/reply/goal closure, same-account concurrent draft reconciliation, API restart under pending work, full keyboard/zoom coverage and the historical AWS hang remain unverified. Prior source-ingestion and check-in-control results remain in their original reports; they were not all repeated in this run. No old scenario failure is overwritten or upgraded merely because related unit tests pass.

## Decision

Keep C010/C011 as local application repairs. Preserve all teaching, assessment, approval, privacy and worker decisions. Defer prompt/audit/assessment/policy changes to separate evaluated proposals. The remaining publication and proactive-delivery prerequisites cannot be made to pass by spending on more reactive model calls. Deployment and AWS incident verification remain separate work.

Cleanup: both headed test browser contexts were signed out and closed; all remaining sessions in the isolated local fixture were revoked because IAB control was unavailable. The local API and Vite processes were stopped. Documentation verification passed 2,973 local Markdown links after the new reports were added.
