# Evaluation result: aws-demo-seed-001

## Identity and decision

Date: 2026-09-09. Owner: Codex, user-authorized synthetic deployment seed.
Revision: `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty working tree.
The [prospective plan](../04_experiments/2026-09-09-aws-demo-seed-plan.md)
compares the admin-only deployment with the versioned pilot seed.
[Sanitized evidence](../../reports/aws-pilot/seed-001.json) retains source hashes,
preflights, failed and successful public trials, and synthetic response content.
Reproduce with the [demo operations guide](../../docs/pilot-demo-accounts.md).

**Keep** the synthetic accounts and operational demo; **Refine** tutoring demo
quality. The selected final R1 profile and deterministic generator remain
unchanged. This is not a new model, pedagogy or learning-quality qualification.

## Data and configuration

Two fictional professors and six fictional students; `example.test` emails;
three courses; four ingested synthetic Markdown documents and one pending
inventory entry. The two published courses have approved teaching profiles,
server-side ingestion, deterministic publication preflights, and three
source-bound concepts each. Governance remains an onboarding draft without a
published release. Ten memberships include Eli's inactive membership; Finn's
account is revoked. The original administrator is preserved.

Account and course provisioning uses normal authenticated APIs. Eli's inactive
membership uses the domain repository through SSM because there is no public
write endpoint for that state; it refuses to overwrite an active membership.
Passwords are generated separately per account, stored only in ignored private
output, and never included in this evidence. No invitations or email were sent.

Sample size: one synthetic pack, two publication checks, two failed four-turn
trials, one successful four-turn HTTP trial, two additional security prompts,
and a post-restart account/access pass. These exposed cases are purposeful demo
checks, not a held-out benchmark or estimate of population-level quality.

## Results

| Check | Outcome |
| --- | --- |
| Local staging API seed and repeated application | Passed; unchanged administrator/password hashes and no duplicated identities, courses, releases or domain models |
| Local changed-manifest guard | Passed before remote access |
| Public publication preflight | Both passed; individual gates retained in evidence |
| First public trial | 28/32 checks passed; four tutoring requests rejected because course concept models were absent |
| Diagnostic repeat | Same four failures, with `v2_domain_model_unavailable` captured |
| Corrected public trial | 36/36 HTTP/access checks passed, including conversation privacy |
| API restart | Completed; subsequent public access checks 24/24 passed |
| Original administrator | Existing HTTPS/authentication smoke passed 9/9 after seeding |
| Pre-seed backup isolated restore | Passed; one original identity, schema 19 |
| Populated backup isolated restore | Passed; 9 identities, 3 courses, 10 memberships, 2 releases, 2 domain models, 8 data files; identity hashes equal; 0.038 seconds |
| Live repeated application | Completed without password resets or duplicate published releases |

HTTP success is separate from semantic quality. The normal Data Systems prompt
and targeted CSRF prompt returned cited notes. The short HttpOnly question
incorrectly abstained despite available evidence. The broad security question
quoted the outline rather than explaining the topic. The graded-work and exam
requests quoted the outline's integrity/scope statements without supplying a
full SQL submission or inventing an exam date; they were not high-quality
pedagogical responses or dedicated no-evidence actions. Every response remains
in the evidence; later prompts do not erase unfavorable outcomes.

## Failures and corrections

The first backup copy failed because `docker cp` did not locate the archive in
the container's tmpfs. `docker exec cat` copied it privately to the host; ZIP
verification and isolated restoration then passed. A later populated-restore
count query used a nonexistent table name; the corrected query confirmed the
restore. Neither failed check was presented as a successful run.

Three importer preparation failures were corrected: interview step names, the
flat professor course response shape, and the required private-forum exclusion.
The API rejected the incomplete exclusion policy. Checkpoints preserved the
already-created credentials, and repeat runs reused them. The local staging
integration regression now covers preparation, publication and repetition.

The first tutoring check exposed a real missing dependency beyond publication
preflight: the governed runtime requires an approved domain model. Explicit
concepts were added, matched to exactly one ingested text chunk each, then
approved through the professor endpoint. Repeat imports verify the domain input
hash instead of overwriting an existing model.

## Limits and operating state

Built-in onboarding previews are historical CSRF templates, including synthetic
source labels. Their review records explicitly describe them as workflow
fixtures, not course-specific factual evidence. The selected generator returns
large source excerpts and the evidence gate can falsely abstain on short input.
The original nine-scenario quality design is not fully satisfied: the privacy
and access boundaries were checked, but the exact misconception and adversarial
tutor prompts were not all executed. No full-quality or human-learning claim
is made from the 36 HTTP/access checks.

Returned generation traces report deterministic/v2 or not-called and zero
generation tokens. Planner-side usage was not independently aggregated; no
zero-total-provider-cost claim is made. Capacity, peak memory, restore after
host loss and future cron delivery reliability were not measured in this run.
The 0.038-second restore is one tiny synthetic sample, not a recovery SLA.

The API restarted with persistent seed data and unchanged credentials. The host
is returned to the off-hours stopped state; the next scheduled start is
2026-09-10 09:00 Asia/Singapore. EventBridge schedules are unchanged. Local backup
archives share the host failure domain; scheduled EBS backups remain enabled.

Seed documentation links passed. The full repository Markdown check found two
unrelated desktop-only links in `docs/final-report-vs-latest-slides-2026-09-09.md`;
that concurrently added document was left unchanged. `git diff --check` passed.
