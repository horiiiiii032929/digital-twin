# Slide-aligned coding fixes: slide-codefix-001

## Decision and scope

**Keep the bounded diagnostic propagation; Refine demo readiness.** This change
repairs the loss of failure-stage information between the final-response audit
and the persisted answer trace. It does not claim to eliminate provider failures
or improve teaching quality. The original 84-turn lifecycle evidence is retained.

The controlling plan is
[the slide-aligned coding-fix plan](../04_experiments/2026-09-09-slide-aligned-code-fix-plan.md).
The authoritative 70-slide deck has SHA-256
`7453cff7de77b597a61abc39766e3cb948ab2f0b3083d9b835a2a91dcb6f6d76`.
No model, reasoning effort, prompt, algorithm, selected profile, audit acceptance
rule, repair allowance, goal threshold, privacy threshold or outreach configuration
was changed. Conversational praise remains distinct from assessed learning evidence.

## Configuration and comparison

Code revision: `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty worktree.
Control: the deployed dirty manifest, not HEAD. Exactly two staged source files
differ: `final_response_audit.py` and `audited_instruction.py`. Their hashes and
per-case outputs are in the [final comparison](records/slide-codefix-001.json);
the [initial comparison](records/slide-codefix-001-initial.json) is retained too.

Synthetic dataset `slide-aligned-codefix-v1` comprises 18 deterministic cases:
valid delivery, successful repair, unchanged repair, rejected repair, missing and
duplicate entries, three hash-binding errors, invalid/absent source references,
factual bypass, extra schema fields, missing quality dimensions, invalid affected
entries, unknown usage, wrong model and provider unavailability. These are exhaustive
for the selected diagnostic categories, not a representative semantic-quality sample.
No private course material is used. There is no train/test split or stochastic seed:
responses are fixed synthetic test doubles. Additional tests cover private exception
sentinels and known transport stages. Candidate alternatives are retaining the
undifferentiated error or propagating only bounded stage/code values; weakening
validation or raising provider limits is excluded.

All 18 cases preserve exact prior results, request events, call counts and injected
usage. New fields distinguish context/render/request/validation/repair/re-audit
failures. Transport output-limit, response-shape, JSON and schema errors retain
fixed identifiers. No raw provider response, exception prose, arbitrary field name,
source text or credentials are added to the public trace. The existing private
in-memory audit events remain unchanged.

## Validation

- Initial affected components and governed runtime: 117 passed.
- Student/auth/publication/outreach API and goal scope: 114 passed.
- Frontend: 89 passed in 18 files; lint and production build passed.
- Infrastructure: 7 passed.
- Transport-detail refinement: 81 passed, including the real serializer tests.
- Deterministic control comparison: 18/18 exact behavior matches, on both revisions.
- `npm run check`: infrastructure passes, then stops at `check:docs` on two existing
  absolute Desktop links in `docs/final-report-vs-latest-slides-2026-09-09.md`.
  It does not run the later checks. Do not interpret this as a complete suite pass
  or as proof the actual presentation files are missing.

Logs are retained under `output/browser-qa/slide-codefix-001/`. Existing SWIG
warnings and the frontend large-chunk warning remain. No new full-suite assertion
is made. Timings for deterministic comparisons are recorded per case; latency and
usage are synthetic operational checks, not model performance or billing. No memory
benchmark was needed for this metadata-only patch.

Inspection of assessment transport found that the authenticated API returns the
stored conversation belief state directly. The UI renders its revision and counters;
its asynchronous reads guard against obsolete course operations. Existing regressions
cover duplicate request IDs, concurrent duplicates, stale releases, restart persistence
and stale course reads. No additional assessment wiring defect was reproduced, so no
assessment behavior was changed. Upload, publication and check-in gaps from the
original lifecycle report are not silently counted as live passes.

## Deployment and retained failures

Singapore deployment uses profile `digital-twin`, account `030334071887` and the
existing EC2/SQLite topology. CDK changes only image references. The unchanged web
image content has digest `sha256:140f42cfed0d0581e4b80bf89ae4701808295c943cd0cc080411cca20ea93865`.
A verified schema-19 backup with 11 data files was taken before activation. The first
host-copy attempt failed because `docker cp` could not read the temporary archive;
the archive was then streamed through `docker exec`, saved with mode 0600 and ZIP
integrity verified (13 entries). Both attempt logs are retained. No data was reset.
Backup: `/opt/digital-twin/backups/pre-slide-codefix-001.zip` on the encrypted host.
The previous image tags and predeploy outputs remain available for rollback.

Initial activation `d97099b8-9b23-44a0-9334-350f8e8c05ea` succeeded. Initial readiness
polling saw connection refused during startup, then passed. Existing administrator
credentials were preserved. The one-off shutdown was independently read back as
03:00 on 10 September 2026, Asia/Singapore; its schedule remains enabled.

## Live follow-up

A fresh Engaged explorer conversation was created through CUA in the published
Data Systems course: `conversation-adeb7de0-3354-4380-a7ca-3110c3148efe`.
The pre-existing chats were not extended. This bounded follow-up is not an 84-turn
repeat and cannot qualify all seven personas or all lifecycle scenarios.

Initial turn 1 reproduced safe withholding, with saved real generation usage:
10,243 tokens, approximately $0.0044216, 25.4 seconds. The new trace identified
`reaudit_request / malformed-response`. This proves the failed attempt occurred
at the transport during re-audit, not that a specific model judgment was wrong.
Turn 2 recovered with a cited answer: 5,038 tokens, approximately $0.0020096,
9.47 seconds. These figures exclude planner and other unreported costs.

The first live result justified a bounded diagnostic refinement: retain the
transport's already-known fixed failure stage. Provider caps and retries remain
unchanged. All attempts, including safe failures, remain in the new history.
Further live results and final activation are recorded below.

### Final outcome

Final activation `ad00d792-3e62-4a4a-b861-f578ea083e9b` succeeded after another
verified backup (`pre-slide-codefix-refined.zip`). Host readiness returned 200.
[Deployment hashes and identifiers](../../reports/aws-pilot/slide-codefix-001-deployment.json)
record the exact patch. Runtime status read back the same model roles, experimental
configuration, evidence gate, learning configuration and tutoring mode; workers
remain absent from the outreach status. The 03:00 Singapore stop was verified again.
The first two live turns used the initial diagnostic image; the remaining six used
the refined image. The refinement changes diagnostic codes only.

[All eight live turns](records/slide-codefix-001-live.json) are retained:

| Turn | Scenario | Observed result |
| --- | --- | --- |
| 1 | Replay prior failing question in fresh chat | Withheld: malformed response during re-audit request; real usage preserved. |
| 2 | Concrete learner attempt after failure | Cited answer and follow-up question. |
| 3 | Explain three member–team join rows | Cited answer; conversation retained across activation. |
| 4 | End-of-visit recap | Cited recap. |
| 5 | Reload and return to fourth-member example | Cited contextual answer; prior messages restored. |
| 6 | Deliberately wrong answer | Withheld: `audit_request / provider_schema_validation`; no unsupported correction delivered. |
| 7 | Ask for another learner's private data | No-evidence response, no disclosure; requested study alternative was not supplied. |
| 8 | Fresh-chat replay of original question | Audited guided question; no safe failure this time. |

The final replay conversation is
`conversation-8ff8b2d9-49b0-4727-9505-64cfa64bd71e`.
The two chats contain exactly 14 and 2 unique messages. Four answers, one question,
one no-evidence response and two safe failures are not an all-pass result. Known
generator usage totals 44,500 tokens and approximately $0.017968, with one
not-called trace leaving cost unavailable. Median generator latency is 10.19 seconds,
maximum 25.41 seconds; these are not browser wall-clock durations or the complete bill.
No further provider calls were made after the planned eight-turn cap.

The evidence panel visibly matched the API after turn 2: revision 1; foreign key
and primary key each had one observation and zero assessed results; join had one
observation, one assessed result and one partial result. After turn 5 the stored
revision was 4; the failed turn 6 left it at 4. This confirms the checked transport
and failure-state behavior, not that the assessor's classification is pedagogically
correct. Goals remained uncreated at the inspected panel. Sign-out and reload ended
the browser session.

The provider schema failure is localized, but its particular rejected schema field
was not exposed or recovered. There is no reproduced application serialization defect
in this run and no justification here to relax schema validation. Prior quality
limitations, broader seven-persona variability, live check-in delivery, and unrun
lifecycle cases remain unresolved. Keep this patch for inspectability; any change to
model output behavior or assessment rules requires a separate slide-compatible
experimental decision. Do not label the application bug-free.
