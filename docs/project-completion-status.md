# Project completion status

Updated: 2026-09-06. Engineering and development evidence are recorded below;
this is not a release qualification or a declaration that every project goal passed.

完成範囲と終了条件は [completion contract](project-completion-contract.md) に固定します。
今回、外部 LLM を含む対話・自律支援・再起動と、教材管理・教授画面・並行処理を
実装・検証しました。動作の証拠は増えましたが、指導品質は改善が必要です。
実際の教授らしさ、代表的な実教材への一般化、学生の学習効果は未検証です。

## Latest technical re-audit

The [6 September technical re-audit](research/2026-09-06-technical-reaudit.md)
reproduced and repaired authority, ingestion, provider-accounting, SQLite
checkpoint/transaction and stale frontend-state defects. Thirty changed/new
execution files were reviewed; the full inventory also retains historical
reviews and is not an assertion that every file was freshly audited.

The configured required checks completed across a final prefix and resumed
remaining stages: **2,539 Python tests, 71 frontend tests, lint and build passed**.
Earlier failed runs are retained. A final autonomous-writer integration followed
that full suite and passed **75 impacted regressions**, including mixed
reactive/autonomous generation and durable state checks. The exact ordering,
source hashes, exclusions and limitations are recorded in the audit. No selected
model/profile was promoted and no external LLM calls were required for these
technical repairs. The English report remains a compiled, visually checked
24-page software-centered report with AI-use disclosure and a separate complete trial appendix. Semantic quality and real instructor fidelity gates remain open.

## Completion audit

| Goal | Completed work and evidence | Remaining gate |
| --- | --- | --- |
| G1 Question adequacy | Opt-in question-specific generation and response-schema correction. [Live 005](../research/05_evaluation/cross-course-quality-development-001-live-005-results.md): 44 successful external calls; 39/44 mechanical containment versus 28/44 control. | Fresh independent semantic grading; reused synthetic exact-span scores do not establish accuracy. |
| G2 Teaching alignment | Corrected an application rule overriding explanation-first profiles; added bounded hints and dialogue continuation. [Luna progression](../research/05_evaluation/final-profile-operational-dialogue-development-001-progression-live-001-results.md) and [Terra comparison](../research/05_evaluation/final-profile-operational-dialogue-development-001-progression-terra-live-001-results.md) recorded. | Generic questions, repeated evidence and weak follow-up remain; Terra did not justify replacement. Actual instructor fidelity requires instructor examples and independent review. Generated-response approval now has a successful small HTTPS browser diagnostic; representative candidate qualification and actual instructor assessment remain open. |
| G3 Knowledge ingestion | UTF-8 text/Markdown upload, permission/de-identification attestation, checksum lineage and withdrawal. [Composition test](../tests/api/test_candidate_ingestion_composition.py) connects upload, profile and course-model approval, publication, candidate citation and withdrawal. | Composition test uses a synthetic provider. One combined PDF/transcript/forum course through the same candidate UI composition remains unqualified. No automatic anonymisation, audio transcription or Canvas integration claim. |
| G4 Instructor feedback | Thirty-day active-learner denominator, small-group suppression and persistent review outcomes. [Browser QA](../tests/manual-completion-browser-2026-09-06.md) verifies upload, review/reload and mobile layout. | Source-group signals do not establish concept-level diagnosis or usefulness to a real instructor. |
| G5 Persistent autonomy | [Full operational trial](../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md): 24 histories × 30 virtual days, 654 actual provider calls, 484 tutor turns, 16 proactive messages, 24 restarts, 48 consent changes, zero consent violations. | 11 output-limit failures and two rejected question-focus proposals; generic outreach and guidance. Virtual time and synthetic students are not real-month uptime or learning evidence. |
| G6 Recovery and capacity | [Schema-18 recovery](../research/05_evaluation/schema18-foundation-development-20260906-001-results.md): 42 checks. Fixed SQLite writer/event-loop stall and added opt-in provider concurrency with budget reservations. [Serial](../research/05_evaluation/final-profile-asgi-tutoring-concurrency-development-20260906-001-results.md) and [concurrent](../research/05_evaluation/final-profile-asgi-tutoring-concurrency-development-20260906-002-results.md) runs each completed 100 tutoring requests and 150 real provider calls. | Observed p95 148.576 versus 31.968 seconds is local in-process evidence; even the concurrent result misses the proposed 15-second gate. The same accepted configuration across browser, restore and authenticated load remains unqualified; network/distributed production reliability is outside this trial. |
| G7 Evaluation quality | Four fictional courses × eleven case types; all failures and scoring limitations retained. [77-case diagnostic review](../research/05_evaluation/dialogue-full-live-001-assistant-review.md) and [professor review packet](../research/05_evaluation/professor-review-development-005/README.md) prepared. | Representative permitted courses and independent human review remain open. Assistant reviews are unblinded and are not an independent accuracy or learning estimate. |
| G8 Report | English LaTeX abstract, related work, methodology, existing architecture/activity diagrams, bibliography and new evidence integrated. Historical results and limitations retained. | Compiled 24-page software-centered report with AI-use disclosure and a separate complete trial appendix visually checked; author/advisor acceptance remains pending and claims stay limited to observed evidence. |

## Earlier verification (before the follow-up fixes)

Final `npm run check` completed successfully (exit 0): **2,085 Python tests**
in the configured required suite, **56 frontend tests**, documentation and
evaluation validators, frontend lint, and production build all passed.
The configured Python command retains its existing four historical-artifact test
file exclusions; this is the repository's standard check, not a claim that every
possible local test file was included. Full output is retained locally at
`reports/generated/completion-verification-20260906/npm-check.log`.

The earlier unrestricted Python run had 2,063 passes and two execution-freeze
coverage failures. Their main-entry guards/registry integration were corrected;
the final required suite includes the corrected checks. Earlier scoped runs and
the candidate ingestion composition test also passed; overlapping counts are
not added together. The frontend build retains a non-fatal >500 kB bundle-size
warning. Passing code tests does not override failed model-quality or latency gates.

The English LaTeX report compiled to 15 pages; abstract, results, conclusion,
references and the integrated figures were visually checked. No undefined
references or overfull/underfull boxes remain. The included-vector-PDF version
warning is documented in the report README.

The [scoped code audit](research/2026-09-06-completion-code-audit.md) binds the
63 reviewed changed/new files to their hashes. The repository inventory retains
previous reviews for unchanged files; it does not claim the whole repository was
re-audited in this turn. Browser QA used isolated synthetic deterministic services.

## Evaluation quantity and quality

The [evaluation-quality audit](evaluation-quality-audit-2026-09-06.md) distinguishes
independent cases, repeated development cases, provider calls and clustered turns.
654 calls and 484 tutor turns are operational volume, not 654 or 484 independent
quality samples. The full trial has 24 histories, six synthetic personas and one
seed. The 77-case review deliberately selects failures, outreach and endpoints;
it is diagnostic, not a random estimate of overall quality.

Historical factual quality (63.25%) and unsuccessful evaluations remain unchanged.
The opt-in development candidate and provider concurrency have not silently
replaced the [selected profile](../research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json).

The proposed fresh 400-answerable / 200-boundary / 200-profile confirmation
has not been executed for this candidate. Development findings did not justify
promoting it or treating the reused 44-case packet as that confirmation.

## Priorities before the follow-up (historical)

1. Improve guidance after an actual student attempt and the need for proactive
   support. Compare against the current candidate on prospectively frozen cases;
   retain repeated/generic messages as failures rather than increasing volume alone.
2. Evaluate a larger output-token allowance against the recorded 500-token
   baseline, including validity, latency and cost. Keep the original eleven
   incomplete outputs and two correctly rejected proposals in the registry.
3. Re-evaluate the candidate on the already permitted four-course portfolio and obtain instructor exemplars;
   freeze a separate evaluation split and obtain independent professor/human ratings.
   The prepared review packet is a development aid, not completed human approval.
4. Complete the generated-response approval preview and one combined
   PDF/transcript/forum course journey. Confirm the accepted candidate through
   the same authenticated deployment, restore and concurrent workload, including
   the still-unmet 15-second p95 target; then update the versioned selection and
   report only if the predefined gates pass.

No simulated mastery trajectory is presented as evidence of student learning.
Real educational effectiveness requires a separately designed study.

Related: [completion plan](../research/04_experiments/2026-09-05-project-completion-plan.md),
[quality contract](quality-and-learning-plan.md),
[result registry](../research/05_evaluation/result-registry.md).

## Follow-up quality audit and repairs

The follow-up found critical evaluation and runtime defects; the project is
still a development candidate, not a qualified teaching release.

- Semantic scoring: 32 controls repeated twice passed, but review of actual
  outputs exposed missed premature solutions and inconsistent profile judgments.
  The [advisory judge](../research/05_evaluation/completion-semantic-review-development-001-live-002-results.md)
  was dropped as a decision-bearing scorer. Its raw counts are not accuracy.
- Output contracts: increasing the token cap alone exchanged truncation for
  schema failures. At the same 1,500-token cap, explicit bounded-contract
  communication reduced schema failures from 14/36 to 0/36 in the
  [paired development trial](../research/05_evaluation/bounded-contract-progression-development-001-live-001-results.md).
  This is format reliability, not established teaching quality.
- Named referents: an opt-in contextual router recovered three previously
  blocked narrowed follow-ups and two fresh named-concept questions in a
  [32-turn comparison](../research/05_evaluation/bounded-contract-progression-development-001-referents-live-001-results.md).
  Only an explicitly named approved concept can defer lexical ambiguity;
  answerability, course and integrity checks remain in force.
- Usage integrity: missing provider token fields now remain unknown and stop
  further budget admission instead of becoming zero. The
  [repair](../research/05_evaluation/provider-usage-integrity-development-001-results.md)
  passed 11 contract cases and 58 focused regression tests. An audit of 954
  recent provider outcome rows found no missing/nonpositive counts; no historical
  cost correction was inferred.
- Mixed-source integration: the
  [expanded joined scenario](../research/05_evaluation/mixed-source-candidate-recovery-development-001-attempt-006-results.md)
  passed 143 assertions across ingestion, credentialed access, dashboard review,
  withdrawal and isolated restore. These are assertions in one scenario, not
  143 independent quality samples; its provider was injected.

The [22-response blinded human packet](../research/05_evaluation/professor-review-quality-audit-20260906/README.md)
has blank ratings and has not been sent or human-reviewed. Candidate confirmation
on fresh representative cases, actual instructor fidelity and student learning
remain unestablished. The selected release profile has not changed. The earlier
full-check totals above predate these follow-up changes.

### Authenticated load follow-up

The [actual HTTPS trial](../research/05_evaluation/authenticated-loopback-load-development-001-live-001-results.md)
completed 180 POSTs and 180 external calls, preserving 360 messages with no
observed HTTP, provider, lineage or non-answer failures. Three 25-learner bursts
had p95 values of 14.375, 14.101 and 13.310 seconds; all six low/high bursts passed
the unchanged 15-second gate. This was explicit v3 at 1,500 output tokens and
provider concurrency five; the v4 named-referent option was disabled. Two factual
templates and short local bursts do not qualify broad teaching quality, sustained
production capacity, v4 operational behavior or long-term uptime. The previous
in-process latency failures remain valid for their different configurations.

### Current priorities after these experiments

1. Establish valid semantic and pedagogical judgments on fresh representative
   candidate responses; obtain independent human/instructor ratings. Existing
   course permissions are available, but do not substitute for this evaluation.
2. Improve and compare substantive follow-up guidance using those judgments;
   retain generic questions and premature solutions as failures. The opt-in
   schema/referent fixes alone do not meet this requirement.
3. Qualify one frozen candidate consistently across quality, instructor approval,
   browser, restore and operational workloads before changing the selected profile.
   The new v3 load and v4 referent runs are distinct configurations.
4. Extend operational testing to sustained/diverse workloads if the report or
   deployment claims require them. No real-month uptime or learning-effect claim
   is supported by accelerated synthetic time.

### Follow-up verification scope

After the final source changes, **128 targeted tests passed** covering the
provider transport and budgets, semantic instruments, candidate generation,
named references, dialogue bridge and network/mixed-source evaluators. The
first overlapping run observed an in-progress duplicate-label edit and had one
failure; both logs are retained in
`reports/generated/completion-followup-verification-20260906/`. The stable rerun
passed. This is a targeted regression result; the earlier 2,085-test full check
was not rerun for this follow-up and is not attributed to the latest code.

After formatting two evaluation helpers, their 17 tests and scoped Ruff checks
also passed (overlapping counts are not added). The follow-up audit refreshed
only 27 changed/new executable paths with explicit reviewer attribution;
all 1,176 inventory entries passed consistency validation. Evaluation records,
execution-freeze coverage (195 entrypoints), local links and `git diff --check`
also passed. These checks do not establish semantic or educational validity.


## Instructional continuation development

The tutor now has an opt-in typed representation for specific questions,
feedback grounded in the student's actual text, and source-linked explanation
steps. Citation provenance remains checked; these bindings do not prove semantic
correctness. The default selected release is unchanged.

The first full paired development run produced 29/48 useful targets after an
adverse review correction (originally30/48), versus
16/48 for the extractive control and failed its quality gates. Replay of 29
rejected outputs identified overly restrictive rendering rules. The separately
versioned correction then produced 43/48 useful targets and 13/16 primary
instructional targets, against 15/48 and 1/16 for the concurrent control.
These are assistant-reviewed synthetic development results, not human accuracy.

A separate boundary sidecar failed its usefulness gate (6/8): missing-detail
coverage and an overbroad access-policy statement still need correction.
Therefore this candidate remains Refine and the held-out confirmation packet
has not been used. See the [improvement program](pedagogical-improvement-program-2026-09-06.md)
for the causal diagnosis and preserved sequence. The previous test totals above
predate this implementation; final verification will be recorded separately.

The subsequent V7 request-coverage representation regressed (33/48 main,
6/8 boundary,5/8 mixed-stage). V8 instead simplifies the model response to
instructional units and source IDs. It passes the narrow main gate at39/48,
with16/16 primary targets; both sidecars pass8/8. All264 provider attempts
completed, with one additional local main-run rejection. However, six
explanatory-profile compound/mixed requests still receive quizzes rather than
the requested explanations. The overall decision remains Refine; this does
not meet the broader95% project standard, and confirmation remains unopened.
See the [V8 content review](../research/05_evaluation/paired-pedagogy-development-v8-live-001-assistant-review.md).

Full V8 source verification subsequently passed: `npm run check` exit0,
2,229 Python tests,56 frontend tests, required instrument/document validators,
frontend lint and production build. The log is retained locally at
`reports/generated/compact-completion-verification-20260906/npm-check.log`.
This snapshot precedes the V9 profile-authority change. The existing nonfatal
frontend bundle-size warning remains; passing software checks does not establish
pedagogical correctness.

V9 improves main usefulness to45/48 with16/16 primary targets, but its
prospectively added12/12 appropriate explanatory-move criterion reaches11/12.
Boundary passes8/8; mixed-stage passes7/8 with one uncertain initial question
excluded. The missing target is a local rejection of an extra source-free
absence explanation; two other cases expose clarification happening after
an empty-evidence stop. All264 external calls completed. V9 remains Refine,
and confirmation is still unopened. The attempted full V9 check stopped at
an evaluation-registry formatting error before Python tests; the row was fixed
and all322 machine records then validated. This attempt is not a full-check pass.
See the [V9 review](../research/05_evaluation/paired-pedagogy-development-v9-live-001-assistant-review.md).

V10 passes the narrow development criteria:48/48 useful targets,16/16 primary,
12/12 explanatory moves,8/8 boundary and8/8 mixed-stage. All264 provider calls
completed; one preceding local rejection remains recorded. The implementation
is frozen for a single unopened confirmation, profile-context comparison,
permissioned course diagnostic and same-configuration operational checks.
This is development acceptance, not project-wide qualification or human fidelity.
See the [V10 review](../research/05_evaluation/paired-pedagogy-development-v10-live-001-assistant-review.md).

The once-only V10 confirmation subsequently failed its zero-critical gate:
one response attributed a separate named mechanism's behavior to the requested
mechanism while citing both sources. Two target local rejections also remain.
A second possible workflow implication is treated as uncertain rather than a
proven second critical error. The candidate remains Refine; real-course transfer
was not started. Ongoing V10 operations are retained as diagnostics, not quality
qualification. A further version requires a prospective general correction and
new confirmation data, not a rerun of the consumed packet.

The full V10 check completed Python verification with2,265 passes and one
failure: an old test required the literal inline `envDir` expression, while Vite
now uses the same resolved repository path through a variable. This is preserved
as a failed full-check attempt at
`reports/generated/typed-instruction-completion-verification-20260906/npm-check.log`.
The test now loads the actual Vite configuration and checks its resolved
repository environment directory. All eight configuration tests pass. Frontend
steps after the Python failure were not reached; final integrated verification
must follow the role-model and worker changes.

The first role-model full-check attempt was deliberately interrupted (exit130)
before completion when a remaining paired-runner alias connection was found.
No paid model-comparison call had started. The retained log is
`reports/generated/generation-role-completion-verification-20260906/npm-check.log`.
This is an interrupted attempt, not a test pass or evidence of a product defect;
the paired role-client integration must be included in the next frozen check.

The second role-model full check passed after that integration: **2,292 Python
tests and 56 frontend tests**, required documentation/evaluation checks, lint
and production build, exit0. The retained log is
`reports/generated/generation-role-completion-verification-20260906-002/npm-check.log`.
This snapshot includes explicit generator/planner role routing and the actual
worker's experimental-app composition. It does not override model-content
failures; the existing nonfatal frontend bundle-size warning remains.

### Generator comparison and evidence-strength follow-up

Keeping the V10 prompt fixed, Luna-low, Luna-medium and Sol-low tied28/28 on a
short entity/implication diagnostic. The subsequent repeated dialogue/profile
study did not qualify any alias: useful main targets were87/96,95/96 and96/96,
but all three produced a critical unsupported guarantee in the profile packet.
The full study retained1,417 attempts, six provider failures and31 missing turns;
unknown usage makes theUSD2.1051074 total a known-cost subtotal only. See the
[aggregate review](../research/05_evaluation/generation-model-dialogue-stability-development-001-aggregate-assistant-review.md).

V11 adds a general instruction to preserve entity ownership, implication
strength, quantifiers and explicit dependencies. Its schema/model/policy remain
unchanged, and source association still does not verify entailment. Targeted
implementation tests and independent source review passed; live quality and
same-configuration integration remain gates under the
[evidence-strength plan](../research/04_experiments/2026-09-06-evidence-strength-generation-plan.md).
This follow-up does not promote a release or erase earlier failures.

The completed V11 study subsequently recorded96/96 main,27/28 short and10/12
profile opportunities; two critical unsupported guarantees remained. All563 calls
completed, but the semantic gates failed. V12 then repaired32/32 defective
component drafts while damaging one of32 adequate drafts by disclosing a new
concept's answer. V13 preserved40/40 adequate drafts and repaired8/8 fresh
solution-in-question controls, but repaired29/32 old defects against a30/32
floor. These failed outcomes remain registered and neither candidate is selected.
V14's conditional keep/repair wrapper completed112 component controls but failed
its semantic gates:39/40 prior adequate drafts were preserved and14/16 fresh
defects repaired. Two critical errors remained: premature disclosure of a new
concept and unsupported exclusivity in a permission statement. All112 calls
completed with known costUSD1.037656; this is not an integrated tutoring result.
The preregistered medium-reasoning comparison subsequently passes all112 component
controls in each of two trials, with zero observed criticals, known combined
costUSD2.237892 and unchanged isolated snapshots. Both results are registered.
This permits integrated Stage B development, not release promotion or a population
accuracy claim. The only post-output reviewer is the root assistant.
The earlier2,292-test full check predates these changes;
it must not be presented as validation of V14 or the generated-preview workflow.

The experimental generated-preview workflow now stores actual generated replies,
citations, usage and immutable source/profile/composition bindings for case-level
review. Targeted tests verify persistence across repository reconnection, saved
review persistence and refusal of approval after a composition change. The
initial25-test pass covers three composition aliases with injected providers;
live browser review and authentic professor approval remain pending. A later
profile approval retains the authority of the existing published release until
its bound profile is explicitly withdrawn.

Six further targeted cases pass across the same three aliases: pending/queued
outreach is cancelled on profile withdrawal and new outreach is rejected; owned
UTF-8 ingestion proceeds through the actual preview creation/list/get/approval
API without another provider call during review. Student access is rejected.
Frontend tests now pass64 cases after correcting an asynchronous list race that
could hide newly generated evidence or replace the displayed review with an
older result. These checks use synthetic inputs and injected provider responses.
The broader integration invocation passes159 tests; ten HTTPS tests initially
stop because the sandbox denies`ps`. Their retry with local process/socket
access passes all12 tests in that file; the failed attempt remains recorded.
Medium-alias integration initially failed because the role transport validator
accepted only low revision effort. After allowing the separately declared medium
configuration, all four targeted generation/paired/restart/HTTPS contracts pass.
This configuration repair changes no component-test inputs or isolated snapshot.

The integrated V14-medium study completed794 calls and452 turns, no provider
failures, known costUSD2.5082096 and unchanged snapshots. Short28/28, profile12/12
and six contrasts, boundary8/8 and mixed8/8 pass their narrow checks. The main
packet is **not qualifying evidence**: its only-when source constraints conflict
with a gold requirement to guarantee positive action. All seven runs are
registered and all turns were reviewed; main aggregate qualification is withheld.
See the [oracle audit](../research/05_evaluation/meaningful-continuation-v2-oracle-audit.md)
and [fixed-candidate rerun plan](../research/04_experiments/2026-09-06-main-oracle-alignment-plan.md).
The fix versions the dataset and retains an original-source necessity diagnostic;
it does not change the model to match an inconsistent answer key.

### Corrected oracle and remaining model failure

The reproducible main v3 packet now states complete procedures; a separate
original-source necessity diagnostic prevents removing implication-direction
challenges. Both v3 main trials completed; semantic reviews are underway.
The necessity diagnostic is registered: V14-medium7/8 versus V4 4/8, one critical
unsupported Topaz guarantee,24 calls/USD0.0807500, no provider/usage failure.
This blocks fresh confirmation regardless of main scores. V15 global support
assessment is a separately preregistered component experiment, not a release
selection. Root's instruction-scope explanation remains a hypothesis.

V15's completed component repetitions fail independently:109/112 with three
critical disclosures;110/112 with one critical disclosure and one uncertain
ownership claim. Total224 calls/USD2.458640; no provider or unknown-usage failure.
Both are registered. Drop V15 for integration; preserve helper only as experimental
evidence. The separately preregistered direct V11/Sol-high alternative changes
model/effort without adding a reviewer. Isolated contract checks are passing;
actual quality evaluation and root integration remain pending.

## Fresh revision comparison and next verification boundary

The fixed V14-medium/V16 comparison on112new authored controls perarm is complete:
both103/112 useful,56/56adequate preserved,47/56flawed corrected,onecriticaleach.
V16 has two uncertain claims versus one forV14; uncertainty remains unqualified.
All224actualSol-medium calls completed with knownUSD2.566300 and unchanged source
snapshots. The prospective correction/family/zero-critical gates failed; V16 remains
unintegrated. The prior reused-controlDahlia failure is also retained. See
[paired evidence](../research/05_evaluation/fresh-assessment-generalization-comparison-001-results.md).

The next bounded component study separates response proposal from final delivery
verification. It checks full response support plus current-stage usefulness,
allows at most one feedback-guided repair and always rechecks changed prose.
Implementation and new synthetic controls are in progress; there is no accepted
quality result or product promotion. The report describes observed failures,
not an achieved final-verification solution. Main/sealed/course/800target/history
and actualbrowser gates remain pending for any accepted final composition.


## Final-response verification follow-up

The first final-output audit was rejected for integration: its exposed112 run
stopped after54 calls (USD1.012588), with two completed responses rejected by
the verdict/issue-code contract.20 inputs reached processing and92 remained
blocked. Both arms missed the known unsupported guarantee; five of six accepted
repairs removed necessary direct explanations. These are diagnostic observations,
not a completed112-case performance estimate. See
[registered result](../research/05_evaluation/final-response-support-audit-001-exposed-live-001-results.md).

A separately versioned v2 now gives explicit contract consistency and conditional
teaching obligations while preserving v1, strict validation and product defaults.
Its52 scoped tests and all240-input fake-provider preflight passed. Actual v2
provider evaluation also stopped:24calls,12reached/100blocked, one timeout with
unknown usage, knowncostUSD0.38008 and the same critical guarantee retained.
The method is dropped for integration; no fresh128 calls or further prompt-only
retry is justified. See [v2 result](../research/05_evaluation/final-response-support-audit-002-exposed-live-001-results.md).
No semantic-quality claim follows from protocol checks. The prior complete required verification passed2478 Python/64frontend
tests plus lint/build and required validators across preserved resumed runs.


## Actual generated-preview browser diagnostic

[Registered G2 browser result](../research/05_evaluation/generated-professor-preview-browser-development-001-live-001-results.md)
confirms one saved/reviewed actual response from two external calls
(USD0.009635, no failures/unknown usage). UI approval binds the exact artifact
and persists across reload; withdrawn-profile reapproval returns409. Preview
processing added no real runtime student conversation, message, learning state,
learning-gap or outreach rows. Source-change and server-restart browser checks
were not executed. The test uses a synthetic course and unselected V14-medium;
it establishes this workflow, not general quality or instructor fidelity.
