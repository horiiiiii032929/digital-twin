# Course Digital Twin release plan

Status date: 2026-08-21

This is the operational plan for releasing the system. The
[real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md)
defines what the product is; immutable evaluation records define what has been
proven. This plan orders the remaining work without changing historical
results.

## Release goal

Ship an invite-only Course Digital Twin that a professor can configure, review,
publish, update, withdraw, and roll back, and that authorized students can use
for persistent, citation-grounded tutoring.

The first release is a supervisor-reviewable hosted candidate. It becomes an
invite-only pilot release only after the approval-gated real-workflow checks
pass. A local demo, a 10,000-case dataset, or a successful model run is evidence
toward the release; none is the release by itself.

## Release stages

| Stage | Outcome | Promotion rule |
| --- | --- | --- |
| R0 — Local baseline | Reviewed professor/student UX and a locally qualified deployable package | Already established; retain as rollback evidence |
| R1 — Hosted release candidate | One immutable revision runs through trusted HTTPS with credentialed roles, durable state, governed sources, monitoring, restore, and rollback | All R1 hard gates pass on the target host |
| R2 — Invite-only pilot | Approved professors and students complete the core workflows without a critical safety, privacy, grounding, or usability failure | Consent, privacy, supervisor approval, and R1 evidence are complete |
| R3 — Final project release | Reproducible code, configuration, evaluation evidence, demo, report, and explicit release/no-release decision | Every claim is linked to evidence and limitations |

## R1 hard gates

| Gate | Release requirement | Current state | Owner issue |
| --- | --- | --- | --- |
| Product journeys | Administrator, professor, and student happy/failure paths pass on one revision | UX baseline kept; full hosted journey pending | [#25](https://github.com/horiiiiii032929/digital-twin/issues/25) |
| Grounding | Text path remains a qualified fallback; multimodal inputs either pass prospective gates or fail closed without an unsupported quality claim | Text fallback retained; multimodal method is Refine | [#86](https://github.com/horiiiiii032929/digital-twin/issues/86) |
| Factual quality | Deterministic source truth, citation integrity, boundary handling, deduplication, and staged large-dataset evidence receive a recorded decision | 10,000 deterministic truth packages and pilot-003 simulation ready; paid stages unauthorized | [#87](https://github.com/horiiiiii032929/digital-twin/issues/87) |
| Professor behavior | Factual/citation hard gates remain separate from professor-specific behavior; the profile and evaluator are approved and calibrated | Build-only C0–C3/profile contract ready; professor guidance pending | [#24](https://github.com/horiiiiii032929/digital-twin/issues/24) |
| Deployment | Public host, trusted TLS, credentialed roles, durable storage, migrations, jobs, and exact release binding work | Current V7 passed 42/42 in-process; current image/local HTTPS and host/domain gates pending | [#88](https://github.com/horiiiiii032929/digital-twin/issues/88) |
| Operations | Isolation, observability, rate/cost limits, backup, restore, deletion, incident handling, and rollback pass on the target host | Local evidence exists; target-host evidence pending | [#9](https://github.com/horiiiiii032929/digital-twin/issues/9) |
| Privacy and security | No credentials or unrestricted private data enter Git; source rights, retention, access, deletion, and incident boundaries are reviewed | Repository controls active; production review pending | [#9](https://github.com/horiiiiii032929/digital-twin/issues/9) |

Any failed hard gate produces a registered `Refine`, `Go Deeper`, or `Drop`
decision. Schedule pressure cannot convert a failure into a pass.

## Work while professor guidance is pending

The following work is reversible and does not require model spending, private
data, or professor input:

1. Preserve merged PR #103 as the deterministic factual-QA and correctness
   checkpoint.
2. Keep the 100-case pilot-003, 1,000-case, and 9,000-case completion stages
   unauthorized.
3. Reconcile the release documentation, GitHub parent issue, Project fields,
   and blocker labels around this plan.
4. Publish the V7 current-tree deployment freeze while keeping current-image,
   public-host, and release claims explicitly pending.
5. Keep the Professor Digital Twin calibration packet empty and the held-out
   set closed until the profile-authoring guidance arrives.

## Decisions still required

| Decision | Needed from | Earliest dependent action |
| --- | --- | --- |
| Deterministic canonical Q&A with multi-model wording/review, or multi-model canonical generation under deterministic verification | Professor guidance | Freeze and authorize paid pilot 003 |
| Explicit professor profile, or inferred profile reviewed and approved by the professor | Professor guidance | Populate fidelity calibration cases |
| Public host and domain | Researcher | Trusted-HTTPS target-host rehearsal |
| Paid pilot-003 authorization | Researcher, after fresh provider metadata and clean preflight | First provider call for pilot 003 |
| Human pilot permission and consent boundary | Professor/institution and researcher | Recruit or expose real users |

## Release decision record

R1 can be marked `Keep` only when the same immutable revision, configuration,
data/profile versions, and deployment pass product, quality, safety, privacy,
operations, and rollback gates. Otherwise record `Refine`, `Go Deeper`, or
`Drop`, identify the failing owner issue, and retain the previous local package
as rollback.
