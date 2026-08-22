# Course Digital Twin release plan

Status date: 2026-08-22

This is the operational plan for releasing the system. The
[real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md)
defines what the product is; immutable evaluation records define what has been
proven. This plan orders the remaining work without changing historical
results.

## Release goal

Ship an invite-only Course Digital Twin that a professor can configure, review,
publish, update, withdraw, and roll back, and that authorized students can use
for autonomous, persistent, citation-grounded tutoring. The accepted
[autonomous tutoring graph](autonomous-tutoring-graph.md) is the student-facing
method: code controls the bounded graph while models interpret learner state
and generate natural responses inside approved evidence and policy boundaries.

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
| Autonomous tutoring | A bounded learner-state and pedagogical-intent graph adapts across turns without ungrounded claims, policy drift, unbounded execution, or silent state corruption | T0 remains the release control; T1 passed all ten network-free development trajectories and may advance only to one separately frozen confirmation | [#107](https://github.com/horiiiiii032929/digital-twin/issues/107) |
| Grounding | Text path remains a qualified fallback; evidence sufficiency must decide answer versus abstain; multimodal inputs either pass prospective gates or fail closed | Text retrieval fallback retained; reviews 003, 004, and 006 are invalid/revoked; review 005 is preserved and unexecuted; no evidence-sufficiency or multimodal method is selected | [#105](https://github.com/horiiiiii032929/digital-twin/issues/105), [#86](https://github.com/horiiiiii032929/digital-twin/issues/86) |
| Factual quality | Deterministic source truth, citation integrity, boundary handling, deduplication, and staged large-dataset evidence receive a recorded decision | #87 completed Keep after pilot 003 passed every 100-case gate; #110 owns optional 1,000/9,000-case scale, which remains unauthorized | [#87](https://github.com/horiiiiii032929/digital-twin/issues/87), [#110](https://github.com/horiiiiii032929/digital-twin/issues/110) |
| Professor behavior | Factual/citation hard gates remain separate from professor-specific behavior; the profile and evaluator are approved and calibrated | Build-only C0–C3/profile contract ready; professor guidance pending | [#24](https://github.com/horiiiiii032929/digital-twin/issues/24) |
| Deployment | Public host, trusted TLS, credentialed roles, durable storage, migrations, jobs, and exact release binding work | Current images build and become healthy; clean bootstrap works; publication fails closed until evidence sufficiency is selected | [#88](https://github.com/horiiiiii032929/digital-twin/issues/88) |
| Operations | Isolation, observability, rate/cost limits, backup, restore, deletion, incident handling, and rollback pass on the target host | Local evidence exists; target-host evidence pending | [#9](https://github.com/horiiiiii032929/digital-twin/issues/9) |
| Privacy and security | No credentials or unrestricted private data enter Git; source rights, retention, access, deletion, and incident boundaries are reviewed | Repository controls active; production review pending | [#9](https://github.com/horiiiiii032929/digital-twin/issues/9) |

Any failed hard gate produces a registered `Refine`, `Go Deeper`, or `Drop`
decision. Schedule pressure cannot convert a failure into a pass.

## Work after the supervisor direction checkpoint

The professor acknowledged the deterministic source-linked Q&A and separate
C0-C3 directions on 2026-08-21. The following work remains reversible and does
not require model spending or private data:

1. Preserve merged PR #103 as the deterministic factual-QA and correctness
   checkpoint.
2. Preserve closed #87 and pilot 003 as Keep evidence. Queue #110 to design a
   separate 1,000-case checkpoint while its execution and the remaining 9,000
   cases stay unauthorized.
3. Reconcile the release documentation, GitHub parent issue, Project fields,
   and blocker labels around this plan.
4. Preserve the completed network-free T0/T1 development result and its revoked
   authorization. Keep T1 rejected by staging configuration while preparing,
   but not executing, one separately frozen confirmation.
5. Preserve V8's historical current-image `Refine` result and V12's corrected
   build-only evidence-sufficiency workflow. Exact Mistral review 002 stopped
   safely after one malformed sensitivity response and remains invalid and
   revoked. Review 003 now requests endpoint-qualified
   strict JSON Schema, preserves malformed content and parser detail, and passed
   the complete 13-call/132-judgment simulation plus a clean live no-call
   preflight. Its separately authorized execution stopped before a provider
   response with an authentication-class transport error. The key itself then
   passed OpenRouter's read-only current-key check, but no quality evidence was
   produced. Attempt 003 is preserved as invalid and revoked. Review 004 now
   uses OpenRouter's documented native chat-completions transport, retains
   sanitized upstream status and router metadata, and passed its full
   network-free simulation and clean live no-call preflight. Its separately
   authorized sensitivity request exposed first-party Mistral endpoint statuses
   400 and 401 but produced no provider response, judgment, reported token, or
   cost. Review 004 is invalid and revoked; do not retry this exact binding.
   Review 005 now pins stable Gemini 3.7 Flash to the exact Google AI Studio
   standard endpoint with strict structured output, zero retries or fallbacks,
   and a USD 0.39 maximum reservation. Its network-free simulation, repository
   gate, and clean live metadata-only preflight pass. It remains build-only and
   provider-unauthorized.
   Review 006 preserved 005 and pinned GPT-5.4 mini to the exact OpenAI
   standard endpoint and dated backend. Its separately authorized sensitivity
   request returned HTTP 400 before any provider response, judgment, reported
   token, or cost. Review 006 is invalid and revoked; do not retry this exact
   binding or automatically fall back to review 005. Review 007 keeps the same
   GPT snapshot and strict schema but removes nonessential reasoning/seed
   parameters, permits same-model OpenAI/Azure provider fallback, and raises
   the emergency ceiling to USD 1.50. Its network-free simulation and live
   metadata-only preflight pass; provider execution remains unauthorized.
6. Keep the Professor Digital Twin calibration packet empty and the held-out
   set closed until the profile-authoring guidance arrives.

## Decisions still required

| Decision | Needed from | Earliest dependent action |
| --- | --- | --- |
| Explicit professor profile, or inferred profile reviewed and approved by the professor | Professor guidance | Populate fidelity calibration cases |
| Execute the separately authorized resilient same-model review 007 once and adjudicate its bounded priority packet | Researcher | Complete dataset review before selecting an answerability gate |
| Public host and domain | Researcher | Trusted-HTTPS target-host rehearsal |
| Human pilot permission and consent boundary | Professor/institution and researcher | Recruit or expose real users |

## Release decision record

R1 can be marked `Keep` only when the same immutable revision, configuration,
data/profile versions, and deployment pass product, quality, safety, privacy,
operations, and rollback gates. Otherwise record `Refine`, `Go Deeper`, or
`Drop`, identify the failing owner issue, and retain the previous local package
as rollback.
