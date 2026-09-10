# Scenario local 008 coverage additions

See [results](../../research/05_evaluation/scenario-local-008-results.md) and [record](../../research/05_evaluation/records/scenario-local-008.json). This adds evidence to the original 106-case catalog; it does not replace the [run 006 disposition ledger](lifecycle-local-006-coverage.md) or revise its historical totals. Only the described branch is claimed.

| Scenario | New evidence / remaining limit |
| --- | --- |
| AUTH-10 | Valid session expiry reproduced stuck workspace; after C011, protected 401 returned to sign-in. Clean reload retest passed. First invalid fixture and HMR failures retained. |
| AUTH-12 | Separate headed professor/student browser contexts showed distinct identities. Student sign-out left professor authenticated after reload. |
| CHAT-07, DIALOG-01–03 | Exact complaint, why-only follow-up and broad takeaway chain executed. No-evidence/clarification/answer observed; weak context-only handling remains a limitation. |
| CHAT-12 | Paid pending-reply reload reproduced lost recovery state; C010 restored draft and manual same-ID recovery. Already-completed-on-reload and other-account cases also covered in hook tests. |
| CHAT-14 | Automation-supplied 8001-character draft rejected with 422, draft retained, no tutor write. Valid near-limit case still untested. |
| CHAT-15 | Multiline SQL plus café/学習 completed with a cited answer; later turn recovered after audit withholding. |
| DIALOG-04–05 | Browser Security HttpOnly explanation and CSRF follow-up completed with citations. |
| DIALOG-06, SOURCE-04 | Explicit Browser Security source request within Data Systems returned no-evidence and identified missing course material. |
| Privacy/adversarial boundary | Hidden-instruction/other-student request withheld by support-reference validation; no requested private content displayed. Not an exhaustive privacy or useful-response pass. |
| REC-03 | Offline-before-send retained draft; reconnect/manual retry completed. Paid reload interrupts a response transport but does not establish every mid-flight network failure branch. |
| REC-04 | Paid in-flight reload/manual recovery used original request; all ten new requests have exactly one persisted response. API/hook idempotency controls supplementary. |
| REC-09 | Independent roles exercised concurrently, but same-account concurrent-draft collision remains untested. |
| UI-02–04 | Mobile 390×844 screenshot inspected; Sources opened and Escape dismissed it; Shift+Enter inserted newline. Full focus/Enter/200% browser-zoom matrix incomplete. |
| UI-08 | Expected offline/auth errors and development HMR failures retained; no clean-console claim. CUA timeout and stale CLI refs classified as harness failures. |

No fresh source-upload/worker pipeline was repeated in 008. Earlier ingestion evidence remains valid only for its recorded cases. Fresh publication, publication revision, real delivered check-in/reply/dismiss/goal closure, pending API restart and AWS scheduling/hang verification were not completed. The existing disabled worker and publication requirements remain unchanged.
