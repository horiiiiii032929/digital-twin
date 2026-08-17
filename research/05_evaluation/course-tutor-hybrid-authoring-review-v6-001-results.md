# Course-tutor hybrid authoring review v6 results

Result ID: `course-tutor-hybrid-authoring-review-v6-001`

Date: 2026-08-14

Status: Model committee complete; qualified for the frozen 41-case blinded
independent-human audit. Human audit, sealing, held-out tutor execution, and
professor approval remain incomplete.

Decision: Go deeper to the blinded human audit. Keep the exact v6 model
records, alias clarification, direct official DeepSeek transport, two-family
quorum, and mandatory human sample. Do not inspect model verdicts before the
human audit, do not treat local unanimity as approval, and do not create a seal
until all human decisions pass and GitHub Support confirms the public-history
purge.

## Boundary and bindings

- Plan: `course-tutor-hybrid-authoring-review-v6`.
- Candidate: unchanged private `course-tutor-v1.2.3` draft 004.
- Candidate hashes: unchanged from v5.
- Clean model-execution revision:
  `bccc3b379ff29875f1f1305f5c1f185a79dcf004`.
- Clean deterministic-finalizer revision:
  `39796ca98285799bc579923bc40b428a78c92d5c`.
- Completed-checkpoint SHA-256 used by the finalizer:
  `6bd3c82ea6e69cecbffd2c62326c37f54e44baa44f0dc3aece52a7d9ced8583f`.
- Provider/model: official DeepSeek API / `deepseek-v4-pro`, documented
  `DeepSeek-V4-Pro-0813`, thinking effort `high`.
- Returned fingerprint:
  `a307abda487cd1b463329ccb945ce396`.
- Local models: frozen `qwen3:4b` and the frozen Huihui Qwen 3 derivative;
  Gemma was not called.
- Tutor outputs, condition mapping, held-out execution ledger, and seal remain
  unopened or absent.

The complete private ensemble is ignored at
`reports/generated/course-tutor-v1.2.3-hybrid-authoring-review/ensemble_review.json`.
Its SHA-256 is
`c0c3d0fbac4424b54e36c7d8312d588f847099cb3b8463b9b34957d4ef2308e9`.

## Model committee result

- Decision records: 456/456 across 152 cases and three model artifacts.
- Valid decisions: 455; invalid decisions: one.
- DeepSeek: 143 approve, eight revise, one invalid; 153 underlying private
  attempts.
- Base Qwen: 152 approve, zero revise/invalid.
- Qwen derivative: 152 approve, zero revise/invalid.
- Two-family approve: 143 cases.
- Unanimous approve: 143 cases.
- Valid-decision disagreement: eight cases, all DeepSeek revise versus both
  local approvals.
- The one DeepSeek-invalid case also had both local approvals and is assigned
  to human review.
- DeepSeek failed-check counts across the eight revisions: claim atomicity in
  eight and evidence support in four. Split-assignment failures: zero.
- Required human cases: 41, below the frozen maximum of 48. This is the union
  of the unchanged 16-case stratified sample, all 19 no-evidence cases, and all
  nine DeepSeek non-approvals, with frozen overlaps.

The 12 alias-induced held-out split revisions seen in v5 did not recur. The
three v5 development atomicity concerns were not disclosed or reused; v6
independently produced eight atomicity revisions that remain hidden from the
human reviewer.

## Transport and operational result

- Public DeepSeek stress gate: 10/10 valid, one stable fingerprint.
- Local public preflights: 2/2 valid with frozen digests.
- External calls: 163 total: ten public and 153 private attempts.
- Known usage: 253,431 input tokens, 407,225 output tokens, including 385,450
  recorded reasoning tokens.
- Conservative cost: USD 0.464528235, below the USD 2 hard stop.
- Private DeepSeek elapsed time: 6,368.57135 seconds in aggregate.
- Finish reasons across private attempts: 151 `stop` and two `length`.
- One case exhausted both 8,192-token attempts. One attempt returned truncated
  malformed JSON after 8,119 reasoning tokens; the other used all 8,192 tokens
  for reasoning and returned no JSON. It is preserved as invalid and assigned
  to human review.

The 8,192-token increase eliminated v5's 4,096-token failures for every other
case, but it is not universally sufficient in high-thinking mode. This does
not invalidate v6 because the frozen protocol explicitly permits final invalid
model decisions and escalates them.

## Finalization repair

All 456 decisions completed and were checkpointed before deterministic summary
generation failed on the invalid row's null decision. No model call occurred
after that failure. A separately committed finalizer:

- fixed null-decision counting;
- required the exact frozen 456 reviewer/case records with no missing, extra,
  duplicate, or in-progress row;
- accepted drift only in the clean code revision used for finalization;
- preserved the original model-execution binding and completed-checkpoint
  hash; and
- recorded its own clean revision in the ensemble.

The recovered ensemble passed the sealing-stage model validation for all 152
cases before any human decision was added.

## Blinded human artifacts

- Packet:
  `reports/generated/course-tutor-v1.2.3-hybrid-authoring-review/human_audit_packet.md`
  — SHA-256
  `a7b550eacd14b18db27b5d4773962eee7763a418e058e9ab8442a16446cefea9`.
- Template:
  `reports/generated/course-tutor-v1.2.3-hybrid-authoring-review/human_audit_template.json`
  — SHA-256
  `75bd158688c8ba2033827ef196d59496f4e97cfdd15c044e9b3910892207d01c`.
- Automated leak check found no model/provider names, model decisions,
  selection reasons, or escalation labels in either human artifact.

The human reviewer must inspect only the packet and template until all 41
decisions are complete. Every case requires six boolean checks, an
approve/revise decision, notes, reviewer identity and role, a timezone-aware
timestamp, and confirmation that model decisions were not inspected.

## Limitations

- Both local models approved every case; they provide a second-family quorum
  artifact but no demonstrated sensitivity to the detected atomicity defects.
- The derivative reviewer is correlated with base Qwen and is not a third
  independent model family.
- One DeepSeek case has no valid final judgment because the 8,192-token budget
  was exhausted twice.
- The human audit is targeted, not a full professor review of all 152 cases.
- Model committee completion does not establish professor fidelity, dataset
  approval, release readiness, or student-facing safety.
- At model-result registration, GitHub Support ticket `4659958` remained an
  independent sealing dependency. The post-run administrative update below
  records its later closure without changing this model result.

## Post-run administrative update

On 2026-08-14, GitHub Support closed ticket `4659958` after confirming no
remaining references and completing server-side garbage collection and
cached-view clearance for public commit `02dbf8d`. The authenticated commit API
then returned no commit for the SHA, and the public commit URL returned HTTP
404. This satisfies the independent purge dependency but does not change any
committee decision or waive the human audit. See the
[purge closure record](../00_admin/2026-08-14-github-public-history-purge-closure.md).

## Next gate

Complete the blinded 41-case human audit. If every selected case is approved,
validate the ensemble and audit together, then create the seal. The GitHub
purge dependency is satisfied. Any human revision requires candidate repair
and a new prospective authoring-review decision; do not silently edit or
approve the current draft.
