# Course Digital Twin release plan

Status date: 2026-08-25

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
| Grounding | Text path remains a qualified fallback; generated claims must be supported before an answer is released; multimodal inputs either pass prospective gates or fail closed | The T0 service now supports bounded evidence selection and optional post-generation atomic-claim validation. The clean 160-case synthetic development run passed its integration gates, but NLI/model binding and independent confirmation remain `Go Deeper`; no product profile or multimodal method is selected | [#105](https://github.com/horiiiiii032929/digital-twin/issues/105), [#86](https://github.com/horiiiiii032929/digital-twin/issues/86) |
| Factual quality | The actual T0 product must retrieve and answer without receiving gold answers, claims, evidence, or citations | The any-hit control released 34/80 synthetic boundaries. The successor public-source confirmation now binds 100 fresh source/question-family clusters, 200 deterministic cases, 40 disjoint controls, and a blinded three-family review packet; semantic review and product execution remain unopened | [#127](https://github.com/horiiiiii032929/digital-twin/issues/127), with [#110](https://github.com/horiiiiii032929/digital-twin/issues/110) preserved as engineering history |
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
2. Preserve closed #87 and completed #110 as engineering evidence that the
   deterministic synthetic workflow processed 10,000 rows. Analysis correction
   001 supersedes any academic factual-accuracy or independent-sample
   interpretation. The new #127 harness ran 160 development cases through the
   actual T0 product without gold injection. Its clean paired result validates
   evidence selection, atomic-claim release plumbing, and the any-hit failure,
   but cannot select the method because the synthetic source aliases and
   questions are aligned by construction. Fresh independent data remain next.
   Confirmation protocol 001 preserves the unexecuted external-human design.
   Protocol 002 replaces only that infeasible review layer with three blinded
   LLM families plus a maximum 60-case researcher packet. Deterministic source
   truth, 200 cases/100 clusters, fixed strata and gates, and cluster-aware
   analysis remain unchanged. This is silver reference evidence, not external
   human ground truth. Exact public sources, cases, controls, and the blinded
   packet are now built and hash-bound. Exact Codex, Mistral, and DeepSeek
   reviewer bindings and the calibration-first executor are also frozen and
   pass the complete network-free simulation. Only the bounded 40-control
   calibration is authorized. Product bindings, researcher audit, confirmation
   execution, and the final tranche remain unopened; the next decision follows
   calibration rather than another redesign.
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
   the emergency ceiling to USD 1.50. Its paid sensitivity request also failed
   before a provider response, so review 007 is invalid/revoked and the
   OpenRouter path is stopped. Review 008 instead uses the direct official
   DeepSeek V4 Pro API, JSON-object output plus deterministic schema validation,
   zero retries/fallbacks, a USD 0.15834 reservation, and a USD 1.50 ceiling.
   Its 13-call/132-judgment simulation and read-only official model-list match
   pass. Its separately authorized sensitivity call returned the exact model
   and valid JSON but detected only 5/6 deliberate defects; all 12 bulk calls
   were suppressed. Review 008 is dropped and authorization is revoked.
   Deterministic audit 001 subsequently inspected all 120 cases and generated
   corrected draft 002 under a successor hash. The researcher confirmed all
   four policy/scope boundaries, and decision freeze 001 now binds the immutable
   draft and confirmation packet. The split remains unopened and every
   downstream execution authority remains closed.
6. Keep the Professor Digital Twin calibration packet empty and the held-out
   set closed until the profile-authoring guidance arrives.

## Decisions still required

| Decision | Needed from | Earliest dependent action |
| --- | --- | --- |
| Explicit professor profile, or inferred profile reviewed and approved by the professor | Professor guidance | Populate fidelity calibration cases |
| Select or reject the provisional atomic-claim method using leakage-free end-to-end evidence | Researcher/evaluation checkpoint | Product binding and grounded publication/student journeys |
| Public host and domain | Researcher | Trusted-HTTPS target-host rehearsal |
| Human pilot permission and consent boundary | Professor/institution and researcher | Recruit or expose real users |

## Release decision record

R1 can be marked `Keep` only when the same immutable revision, configuration,
data/profile versions, and deployment pass product, quality, safety, privacy,
operations, and rollback gates. Otherwise record `Refine`, `Go Deeper`, or
`Drop`, identify the failing owner issue, and retain the previous local package
as rollback.
