# Current project status

Status date: 2026-08-21

This is the operational starting point for prospective work. Frozen experiment
plans, result records, corrections, profiles, and the technical evidence freeze
remain authoritative for the historical runs and claims they document.

The repository-wide correctness baseline was completed on `main` at merge revision
`db2f5e9` through PR
[#98](https://github.com/horiiiiii032929/digital-twin/pull/98):
the current branch extends it to all 481 executable or execution-affecting
files, which are hash-bound and audited,
with zero pending files and zero open findings. The canonical verification gate
now fails if pending or open records reappear. The execution freeze remains
active for all general evaluation actions. It covers 59 protected entrypoints
and retains an exact bounded authorization only for the completed
`factual-qa-v3-oracle-pilot-001`. Manual review found material source-design
defects in the unexecuted `factual-qa-v3-scale-rehearsal-001`, so its bounded
authorization was revoked. The corrected
`factual-qa-v3-scale-rehearsal-002` source and evaluation logic completed manual
review, but its one-time execution is invalid: all 120 author calls completed
before the first-party Mistral ZDR route returned an upstream authentication
failure. Its authorization is revoked and the invalid artifact is preserved.
Unexecuted successor `factual-qa-v3-scale-rehearsal-003` was superseded after the
researcher allowed provider data collection for this synthetic evaluation
phase. Reviewed `factual-qa-v3-scale-rehearsal-004` preserves the two pre-bulk
provider canaries, explicitly allows collection and retention only for committed
synthetic-public fixtures. Its one-time execution completed at clean revision
`6a75410`: 114/120 cases passed deterministic provenance and retrieval recovered
all required evidence in the top three for 96/96 answerable cases, but the
independent reviewer detected only 10/20 controlled mutations. It accepted every
missing- and truncated-citation defect, failing the 90% sensitivity gate. The
completed 12-case manual audit confirmed all six deterministic quarantines and
accepted six stratified controls. The decision is **Refine**; authorization is
revoked and 10,000-case scale remains closed. No path permits private or held-out
data, and the wider freeze remains active.

Successor `factual-qa-v3-scale-rehearsal-005` made exact target-claim, full
evidence-quote, verbatim-source, and no-extra-claim checks explicit. Its paid run
is invalid: both canaries and the pre-dispute stages completed, but one malformed
DeepSeek dispute response aborted the result before completed metrics and exact
accounting were persisted. Authorization is revoked. The correction is a small,
durably checkpointed reviewer qualification rather than another 120-case rerun;
10,000-case execution remains unauthorized.

Completed `factual-qa-v3-reviewer-qualification-006` replaced another full
rehearsal with 24 new deterministic clean/defect pairs. Mistral accepted all 24
clean controls and rejected all 24 defects, including 4/4 in every mutation
class. All 49 calls completed in 16.04 seconds for USD 0.012175 with zero
malformed/provider errors. The strict reviewer is kept as advisory quality
control for the 10,000-case design; deterministic lineage remains authoritative.
The one-time 006 authorization is revoked. The subsequent 24-pair hosted
Qwen3.7 Plus qualification 007 failed six gates: only 41/48 reviews were
contract-valid, clean specificity was 75.0%, mutation sensitivity was 83.3%,
reviewer p95 latency was 42.46 seconds, and measured cost was USD 0.128239.
The provider returned more output tokens than the requested cap, exposing that
the prospective reservation did not enforce the USD 0.10 limit. Qwen is not
selected, its one-time authorization is revoked, and qualified Mistral Small 4
remains the advisory reviewer. Cost enforcement was hardened before the two
paid 100-case attempts. Corrected attempt 002 completed safely as **Refine**:
93/100 cases passed deterministic validation, all 85 answerable cases had valid
citations, reviewer agreement was 97/100, and all 20 mutations were rejected.
Boundary handling, one multi-source claim binding, duplicate questions, and two
malformed outcomes still failed their gates. Its authorization is revoked; the
1,000- and 10,000-case stages remain unauthorized.

The provider-free successor is now implemented as
`factual-qa-v3-10000-pipeline-002` with unauthorized pilot 003. Deterministic
code owns canonical questions and answers, actions, claims, exact quotes,
citations, boundary reasons, and hashes; a model may propose only question
wording. Historical pipeline 001 remains unchanged. Pipeline 002 corrects its
cross-course boundary mismatch prospectively, producing exactly 8,000
answerable and 2,000 empty-lineage boundary packages. All 10,000 are byte-stable
and normalized-question unique. The normal 222-call network-free simulation
passes every gate, while paid preflight remains `blocked-not-authorized`.

The current metadata checkpoint also found that older prospective DeepSeek
prices in the repository were stale. Pilot 003 binds the current documented
DeepSeek V4 Flash 0731 and V4 Pro 0813 revisions using conservative peak prices,
plus exact OpenRouter `mistralai/mistral-small-2603` routing with fallback
disabled. The frozen policy snapshot records DeepSeek account-linked retention
and PRC storage plus the OpenRouter registry's 30-day, no-training Mistral
policy. Only synthetic-public fixtures are permitted. Historical result
bindings were not changed. Paid execution requires another live metadata check
within 24 hours.

The complete locked dependency set now reports zero known Python or JavaScript
vulnerabilities and has no active exceptions. The optional retrieval stack was
upgraded to Torch 2.13.0, Transformers 5.15.1, and Sentence Transformers 6.0.0;
historical retrieval results remain bound to their old environment, and the
upgraded stack is not selected until a new post-freeze evaluation is authorized.

The runtime-boundary checkpoint is complete. Persistence updates are
non-destructive, release content is immutable, staging evidence is resolved
from successful server-side ingestion jobs, storage deletion is durable and
retryable, backup/restore is bounded and atomic, and concurrent student turns
converge on one response with authoritative citation metadata. The final local
check passes 754 Python tests and 46 frontend tests, frontend lint, and the
production build. This is a correctness closure, not a renewed deployment or
model-selection claim.

The onboarding and policy checkpoint is also complete. Professor session writes
now reject stale updates and owner takeover, each reviewed setup is bound to one
course, and source or policy changes revoke approvals that no longer match the
reviewed state. Preview decisions must match the current policy version, every
custom preview must be accepted, and staging release creation now carries only
server-owned ingestion job IDs from the browser. Rendered desktop navigation
from tutor setup to course delivery passed without console errors; the broader
frontend and cross-browser audit remains open.

The active-runtime audit is now complete at 96/96 inventoried files. Identity
security mutations and their audit records commit atomically; course ownership
creation is atomic; account, owner, and membership roles cannot drift; one
published release per course is enforced in SQLite; and repository writes
revalidate copied domain models. Publication cannot bypass evaluation/policy
gates, expired ingestion workers cannot finalize jobs, chunked uploads are
stream-bounded, rate-limit storage is bounded, and readiness checks all durable
connections. These corrections pass the current 754-test Python suite.
Frontend, verification, tooling, evaluation configuration, and historical
artifacts are also fully dispositioned in the current 481-file audit. Evaluation
execution remains frozen; only the completed historical oracle pilot remains in
the bounded allowlist. No 100-, 1,000-, or 10,000-case stage is authorized.

## Current outcome

The active goal is to release the system, not to maximize any individual
benchmark. The [release plan](release-plan.md) defines a hosted R1 release
candidate, an approval-gated R2 invite-only pilot, and an R3 final project
release. The [real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md)
continues to define the product; evaluation tracks are evidence gates toward
that release.

The project owner accepted
[`autonomous-tutoring-graph-001`](autonomous-tutoring-graph.md) as the
student-facing architecture decision on 2026-08-21. The existing student
workflow is now named as the T0 grounded control. The build-only T1 successor
now adds a typed learner-state contract, deterministic pedagogical-intent
selection, a fixed LangGraph path, one-repair maximum, deterministic fallback,
atomic SQLite state revisions, race rejection, restart recovery, and an
explicit local demo/test mode. Its ten-trajectory development method is now
frozen for one network-free execution; provider, paid, held-out, and
automatic-promotion execution remain unauthorized. Staging rejects T1 until a
finite multi-turn confirmation and
release-profile decision pass. T2 applies the professor-approved policy to the
same graph and remains pending professor-profile guidance. This checkpoint does
not resolve the professor's pending 10,000-case dataset-method guidance.

PR [#83](https://github.com/horiiiiii032929/digital-twin/pull/83) merged the
reviewed conversation-first professor and student workspaces into `main` at
`acaaecd`. Issues #82 and #84 are `Done / Keep`. The merged flow passed the
recorded repository checks, 19/19 synthetic publication/student checks,
responsive browser QA, and independent Impeccable review. This establishes the
product UX baseline; it does not establish human usability or production
readiness.

Issue [#88](https://github.com/horiiiiii032929/digital-twin/issues/88) remains
in progress. Its V7 in-process result was **Go Deeper**, while the later V8
current-image result is **Refine**. The post-correctness V7 candidate at
clean implementation revision `f553be5` passed 42/42 current in-process checks:
credentialed professor/student journeys, server-owned ingestion lineage,
policy approval and publication, grounded answers and citations, restart,
schema-v8 backup/restore, security, lifecycle, and bounded capacity. Its
100-request error rate was 0%, API p50/p95 was 2.717/3.073 ms, ingestion was
52.342 ms, and dependency audits reported zero known vulnerabilities. The run
used no external model and no private data.

`deployable-product-foundation-freeze-v7` now binds that result to 14 current
runtime trees and 17 critical files. It makes no current container-image or
release claim. A later controlled Docker restart recovered the engine and
exposed two release-critical facts in attempt V8. First, the image omitted the
documented bootstrap, backup, restore, and lifecycle commands; the image now
copies those exact operational entrypoints and no broad tooling tree. Second,
the rebuilt API, worker, and Caddy containers became healthy, clean
administrator bootstrap worked, and source ingestion reached release
publication, but the real product profile correctly refused publication with
`evidence_sufficiency_required`. Evidence-sufficiency v1 selected no safe
method, while the 42/42 in-process harness explicitly injected an AnyHit test
control. V7 therefore proves those mechanics only under its synthetic control;
it does not prove a releasable product configuration. Attempt V8 is **Refine**
with no selected release candidate. A prospective evidence-sufficiency
successor must pass before public DNS/TLS, clean-host restore, and the public
walkthrough can support release.

Issue [#105](https://github.com/horiiiiii032929/digital-twin/issues/105) now
owns that successor. V10 implemented a provider-neutral open-set gate that keeps
semantic scoring separate from the final answer/abstain policy and fails closed
for incomplete, contradictory, ambiguous, malformed, or unknown-lineage
evidence. A post-V9 review also corrected malformed plain-object verifier output
so it now follows the same redacted fail-closed path as raised verifier errors.
The deterministic 120-case synthetic-public decision draft is now authored:
80 answerable and 40 abstain cases across nine slices, 40 source versions, and
text, table, diagram, code, and equation evidence. All answer cases bind exact
active-source claims and quotes; all abstain cases have empty authoritative
lineage. Its exact hash passes automated structural validation, but independent
advisory review and the 12-case priority packet remain pending. V12 now binds a
deterministic review workflow: 12 blinded ten-case batches, six clean controls,
six planted defect classes, strict judgment accounting, and a maximum 12-case
priority packet. Its 132-judgment network-free simulation passes, but that is
orchestration evidence rather than review evidence. Prospective review
instrument `002` now binds exact OpenRouter Mistral Small 4 routing, current
published pricing, synthetic-public inputs, and a USD 0.50 ceiling. The review
preflight remains `blocked-not-authorized` because one-time execution is not
authorized. The draft remains
unfrozen and unopened; no exact verifier is selected, and calibration plus
decision execution are unauthorized. V12 is the current **Refine** checkpoint
with no selected implementation. Because its source tree differs from V8, the
V8 image identities are historical evidence; the current source has no image
or publication claim.

The exact local `qwen3.5:9b-q4_K_M` reviewer completed two 22-probe
synthetic-public method-development attempts. Both detected 11/11 planted
defects and 6/6 visual defects at USD 0. The corrected attempt also passed 6/6
clean visual controls and 11/11 derived failure labels, but falsely rejected
one correct cross-course abstention, so the local model remains advisory-only
and is not an autonomous acceptance gate. Direct DeepSeek remains the retained
path; the exact OpenRouter Mistral reviewer is bound prospectively but uncalled.
PR [#93](https://github.com/horiiiiii032929/digital-twin/pull/93) merged the
earlier foundation into `main` at `adf39af`. PR
[#103](https://github.com/horiiiiii032929/digital-twin/pull/103) merged the
deterministic factual-QA successor and repository-correctness corrections at
`4657219`. PR
[#104](https://github.com/horiiiiii032929/digital-twin/pull/104) merged the V7/V8
requalification. V12 remains preserved as a historical corrected build-only
checkpoint. Reviewer-binding instrument `002` and the issue #107 T1 source
change supersede its current-tree match without promoting the still-pending
product or public deployment claim.

GitHub Project 1 is reorganized around release goal
[#8](https://github.com/horiiiiii032929/digital-twin/issues/8) and three active
gates:

- P1 — Multimodal Product Grounding;
- P2 — Deployable Product Foundation; and
- P3 — Pilot Validation and Release.

The older F2 milestone is closed. Open F3 work was reassigned into P1-P3. F4
continues to hold report, presentation, and professor-communication work.

## Evidence state

| Boundary | Current decision | Established | Missing before product release |
| --- | --- | --- | --- |
| Product UX and autonomous tutoring | Keep T0 as release baseline; T1 build-only | Professor and student conversation-first workspaces; typed T1 learner state and intent graph; atomic persistence, bounded repair/fallback, race/restart tests; ten-trajectory network-free contract | Run the finite T0/T1 development and one frozen confirmation method; add privacy-preserving course-improvement aggregation; then obtain human workflow/usability evidence. T2 waits for professor-profile guidance |
| Text retrieval | Keep experimentally | M2 hybrid BM25 plus local Qwen3 dense RRF selected on the one-time cross-course held-out comparison; BM25 rollback | Release-candidate end-to-end quality against realistic workload |
| Multimodal retrieval | Refine; no selection | Region-aware tables/cells/diagrams/equations/OCR, scanned-PDF API ingestion, original crop citations, 13/13 synthetic complete@3 and lineage; unfavorable historical and V2 attempt results preserved | Production OCR/layout qualification, representative real-PDF quality and end-to-end latency; frozen relative micro-p95 gate still failed |
| Generator and prompt | Historical experimental selection plus later Refine evidence | Versioned DeepSeek and deterministic boundaries and unfavorable results preserved | Stable currently available candidate, independently calibrated semantic review, and release binding |
| Professor fidelity | Refine / Paused | Invalid C0-C3 comparison and correction preserved; execution policy protects held-out | Independent expert calibration, valid prospective development comparison, and hard-gate pass |
| Publication/student core | Refine; no current release candidate | V8 images built and became healthy; operational commands and clean bootstrap worked; historical V12 binds the corrected gate, exact 120-case draft, and bounded review workflow | Execute and adjudicate the independent review, freeze the decision set, select a real evidence-sufficiency method, bind the T1 successor, rebuild one source revision, complete HTTPS publication, then public trusted HTTPS/target-host restore and real-workflow evaluation |
| Large factual QA | Provider-free successor Keep; paid method still Refine | Attempt 002 remains preserved; pipeline 002 now creates exactly 8,000 answerable plus 2,000 boundary truth packages with deterministic actions/claims/answers/citations, zero normalized duplicates, and a passing 222-call simulation | Interpret professor guidance and separately authorize one paid pilot 003; only a full pass may open a separately authorized 1,000-case checkpoint |

## Release readiness and critical path

The repository and local product baseline are healthy, but the system is not
release-ready. The current release blockers are an unconfirmed T1 autonomous
tutoring graph, a selected evidence-sufficiency method, professor-method
guidance, separately authorized factual-QA confirmation, public host/domain
selection, target-host operations evidence, professor-fidelity calibration,
and one frozen end-to-end candidate decision.

| Order | Issue | State | Exit condition |
| ---: | --- | --- | --- |
| 1 | [#8 Release goal](https://github.com/horiiiiii032929/digital-twin/issues/8) | In Progress / parent | Keep every implementation and evaluation item tied to the R1/R2/R3 definition of done |
| 2 | Repository correctness and execution freeze | Keep | Maintain a clean audited baseline; no prospective paid or held-out execution without its own authorization |
| 3 | [#107 Autonomous tutoring graph](https://github.com/horiiiiii032929/digital-twin/issues/107) | In Progress / build-only contract implemented | Preserve T0 as rollback, complete the network-free ten-trajectory contract, and freeze one T0/T1 multi-turn confirmation method before staging selection |
| 4 | [#87 Factual-QA dataset quality](https://github.com/horiiiiii032929/digital-twin/issues/87) | In Progress / successor build ready | Interpret professor-method guidance, then separately authorize exactly one paid pilot 003; 1,000 and 10,000 remain closed |
| 5 | [#105 Evidence-sufficiency successor](https://github.com/horiiiiii032929/digital-twin/issues/105) | In Progress / bounded review ready / Refine | Bind and authorize the independent review, adjudicate at most 12 priority cases, freeze the corrected 120-case set, then select an open-set answerability gate without using AnyHit |
| 6 | [#88 Deployable product foundation](https://github.com/horiiiiii032929/digital-twin/issues/88) | In Progress / Refine | Complete current-image publication with the selected gate, then select a host/domain and pass trusted TLS, restore, and walkthrough |
| 7 | [#24 Fidelity calibration](https://github.com/horiiiiii032929/digital-twin/issues/24) | Todo / Refine / professor input | Approve the profile-authoring method and calibrate behavior labels separately from factual hard gates |
| 8 | [#9 Operations](https://github.com/horiiiiii032929/digital-twin/issues/9) and [#25 end-to-end](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / blocked | Qualify one immutable deployed revision for isolation, recovery, observability, latency, cost, complete journeys, and rollback |
| 9 | [#10 Invite-only pilot](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / approval-gated | Complete consented professor/student workflows; keep usability separate from learning outcomes |

Issues #85 and #86 are complete and archived from the live Project view. PR #91 merged the tested multimodal product
foundation and three registered prospective development attempts. Attempt 003 passed 13/14 gates:
all quality, safety, action, text-control, and lineage gates passed; relative
warm p95 failed at 0.053 ms versus 0.023 ms. No multimodal profile was selected,
and the historical held-out split was not opened. Issue #87 preserves paid
attempt 002 and its completed 12-case cross-review as historical evidence. The
active correction moves canonical questions, answers, actions, claim IDs, and
citations into deterministic source truth while keeping model generation and
review advisory. This remains method validation, not a model benchmark.
Issue #88 remains active. V8 images are operational historical evidence, while
the changed V12 source is intentionally unbuilt. Product publication remains
blocked by the unselected evidence-sufficiency component; a host rehearsal is
premature until that gate is selected and the same source revision is rebuilt.

## Known multimodal correction

The suspected duplicated `for hit in raw_hit_rows` loop was not present in the
committed runner, and the preserved values match the single-pass legacy
formula. The actual defect was duplicate gain: overlapping OCR, layout, and
description records could each add discounted IoU for the same gold region,
after which the unnormalized total was capped at one.

Issue #85 replaces that metric with one-to-one region matching and normalized
discounted IoU, tests page/region ranking, IoU thresholds, complete evidence,
atomic recall, and nDCG, and registers a no-model correction. V2 changes from
0.212 to 0.0676 and V3 from 0.186 to 0.0756 on corrected region nDCG. Complete
evidence remains tied at 1/3, V3 atomic recall remains worse at 1/3 versus
V2's 2/3, and the V3 online-model gate still fails. The Drop decision and
text-only rollback therefore remain unchanged. The 24-case held-out split was
not read.

The prospective path now models columns, table rows/cells, figures, diagrams,
equation-like blocks, OCR, reading order, page/region checksums, and original
crops. Scanned PDFs work when an approved OCR provider is injected. Gemma
remains excluded. A production OCR/layout or replacement vision model is
selected only through a new prospective qualification and representative
course evidence.

The active model policy now blocks every Gemma and Claude call and all retired
local general-Qwen calls before provider I/O. Direct DeepSeek V4 Flash/Pro and
the selected task-specific Qwen3 Embedding binding remain current for their
recorded roles. Mistral Small 4 is retained as the qualified advisory reviewer.
Hosted Qwen3.7 Plus failed bounded qualification 007 and is not selected; its
one-time authorization is revoked and no local model is used. See
[the current model policy](../research/00_admin/2026-08-21-current-model-policy-v3.md).

## Large factual-QA interpretation

Issue #87 now adopts a product-first v3 interpretation of the professor's
suggestion. The primary corpus is every eligible file in the canonical Academia
Vault, not a large dummy corpus. A small deterministic dummy corpus with a
hidden fact manifest remains only as an oracle control for extraction,
retrieval, citation, boundary-action, and mutation mechanics. The refreshed
inventory found 2,637 regular files: 294 clear candidates, 437 requiring
review, 1,903 generated/tool-state exclusions, and three sensitive exclusions.
Every file requires a recorded content-safe disposition before release. The v1
semantic triage is preserved but prospectively corrected: path and format alone
cannot finalize supporting or exclusion labels. V2 retains 32 approved
exact-hash authoritative sources and returns 570 readable candidates to
content-level review. This is a provisional queue, not a requirement for 570
manual judgments. The deterministic private content screen verified all 570
hashes, extracted local text for 554, and routed 19 lexical privacy/integrity
signals plus 16 visual/binary sources to priority review. The remaining 535 are
still semantically unresolved; absence of a lexical signal is not eligibility
evidence.

The historical 24-case attempts remain valid evidence about their frozen v2
method, but the preserved six-case audit is no longer the active product gate.
Corrected V3 requires claim-level exact evidence, retrieval without injected gold
passages, multimodal source lineage, deterministic mutation sensitivity, and a
compact human-audit packet. It remains separate from the verified 100-case
retrieval benchmark and Professor Digital Twin fidelity.

The separately authorized 40-case oracle pilot has now executed on four
synthetic selectable-text PDFs. Product ingestion created 115 chunks without
warnings. DeepSeek V4 Flash authored 40 cases, exact local Qwen 3.5 reviewed all
40, and DeepSeek V4 Pro reviewed two disputes. Thirty-nine cases passed exact
deterministic provenance; the one quarantined table case omitted the final words
from its citation, which both LLM reviewers incorrectly accepted. Hybrid
retrieval recovered all required evidence in the top three for 32/32 answerable
cases. The six controlled visual cases used approved accessibility descriptions
and do not establish raw image-only quality. The run passed its machine gates
and the corrected eight-case human audit is complete: seven retained controls
were accepted and the quarantined citation defect was confirmed as a rejection.
Rehearsal 002 completed all 120 direct DeepSeek V4 Flash author calls in memory,
then failed when the first-party OpenRouter Mistral Small 4 ZDR endpoint returned
an upstream `401 Invalid API Key`. The OpenRouter account key remained valid and
reported zero usage, so this is an endpoint-readiness and runner-order defect,
not a missing credential. Exact reviewer attempted-call and external-cost
accounting is incomplete; no generated outputs or quality metrics survive and
002 is registered as invalid. Unexecuted 003 added one schema-valid canary
through each provider before bulk authoring, then was superseded when the
researcher explicitly allowed provider data collection for this evaluation
phase. Successor 004 preserved those canaries and the exact source and model
design while allowing provider collection and retention only for the committed
synthetic-public fixtures. The run completed 268 provider calls for USD 0.046029
and passed every gate except reviewer mutation sensitivity: Mistral rejected all
invalid claim/source bindings but accepted all missing/truncated citations. The
manual audit confirmed six quarantines and six controls. The method must be
refined before real-source or larger execution, and scale toward 10,000 remains
unauthorized.

Rehearsal 005 implemented that refinement with 24 new paired defects across six
mutation classes. Its one-time execution is invalid because a malformed DeepSeek
dispute response discarded completed in-memory stages and left exact accounting
incomplete. Its authorization is revoked. Focused reviewer qualification 006
then passed all clean, defect, per-mutation, completion, latency, and cost gates.

The provider-free `factual-qa-v3-10000-pipeline-001` design now fixes 20 dummy
courses, 1,000 source units, 8,000 deterministic claims, and 10,000 blueprints:
8,000 answerable cases plus 2,000 no-evidence, ambiguity, cross-course, and
academic-integrity boundaries. The local builder passes exact grain, key,
lineage, distribution, stage, determinism, and privacy checks with zero model
calls. Dataset writing and every paid 100, 1,000, and 10,000 stage remain
unauthorized pending separate frozen checkpoints.

The shared `factual-qa-v3-scale-pilot-100` runner binds the first
100 stratified blueprints and validates a maximum of 246 calls under a USD 3.00
emergency stop. Its USD 0.323842 prospective reservation is informational;
actual provider-reported tokens and cost are checkpointed on every call, and
requested-versus-reported token-limit violations are counted explicitly.
Network-free simulations exercised the 222-call no-dispute path and the
246-call maximum-dispute path, including deterministic acceptance, 20 mutation
probes, malformed/provider failure accounting, exact model identity, atomic
checkpoints, safe resume, aggregate and slice gates, and a 12-case priority
packet. The paid run completed as **Refine** at revision `0d60f86`: 226/226
provider calls returned for USD 0.110512 with stable model identities, complete
accounting, and zero token-limit violations. However, only 4/100 authored cases
passed deterministic validity, 9 author responses were malformed, and all 100
Mistral review responses violated the scale-run contract. Because only four
valid cases were boundary cases, zero answerable cases were eligible for the
20 planned mutation probes. The 12-case priority cross-review confirmed all 12
deterministic quarantines. This exposes prompt/schema and mutation-eligibility
defects in the method, not a valid scale-quality result. Authorization is
revoked; the 1,000- and 10,000-case stages remain closed.

Successor `factual-qa-v3-scale-pilot-100-002` corrects those three method
defects without making provider calls. Authoring now uses the full shared JSON
schema plus an exact citation-object contract; scale review imports the same
strict schema, prompts, and validator used by qualification 006; and all 20
mutation probes are built from deterministic canonical controls independent of
author success. At clean revision `d5fe874`, the normal 222-call and maximum
246-call network-free paths passed, and a total-author-malformation regression
still constructed and reviewed all 20 mutations. The full repository gate
passed with 682 Python and 46 frontend tests, and the audit is 449/449 complete.
The paid attempt 002 completed as **Refine** at clean revision `1e2125b`. It
improved deterministic validity from 4/100 to 93/100, restored 97% reviewer
agreement, achieved 100% citation validity, and ran all 20 mutation probes with
20/20 rejection. The valid run used 225 calls and USD 0.102517 with stable
models, complete accounting, and zero token-limit violations. It still failed
five gates: all five ambiguity cases violated the boundary contract, one
multi-source claim/citation binding failed, one author and one review were
malformed, and five exact duplicate questions remained. Codex cross-review
confirmed seven quarantines and five retained controls; two Mistral false
accepts were correctly rejected by deterministic checks and DeepSeek disputes.
Attempt 002 authorization is revoked. The next method should deterministically
assemble actions, claim IDs, and citations, quarantine null authors before model
review, and enforce normalized question uniqueness. The 1,000- and 10,000-case
stages remain unauthorized.

Pipeline 002 implements that method-level correction rather than another prompt
revision. Its truth content hash is
`1b4bd3febd79ce828300b42cc23b379de85f7bf92fa07fe8493f22d56e7f5c8c`.
That merged provider-free checkpoint passed 713 Python and 46 frontend tests
with a 465/465 complete audit. The current V12 checkpoint passes 754 Python and
46 frontend tests with a 481/481 complete audit. Pilot 003 is reviewed but not
frozen or allowlisted. The separate Professor Digital Twin transition now has a
validated C0-C3 contract, approval-gated explicit/inferred professor-profile
schema, and an empty 8-12-case calibration template. Fidelity judging and held-
out access remain paused pending professor guidance.

[Issue #102](https://github.com/horiiiiii032929/digital-twin/issues/102) now
tracks the separate `factual-qa-v3-real-source-pilot-001`. Its draft defines 40
cases across text, code, multi-source, table, diagram, other multimodal, and
boundary slices. It cannot execute until the large dummy-data checkpoint is
decided and every
selected Vault source has an explicit eligible exact-hash disposition. Raw Vault
files remain local; only sanitized evidence may enter GitHub.

## Human and safety boundary

A real-user pilot is now a product gate, but recruitment is not automatically
authorized. Issue #10 requires consent, privacy, recruitment, and supervisor
approval before exposure to real users. Until then, use synthetic accounts and
approved or dummy content.

Private course data, generated review packets, `.env`, build output,
dependencies, model artifacts, and bulky run outputs remain ignored. Do not use
solutions, answer keys, submissions, student data, credentials, or consent
records as committed fixtures.

## Source-of-truth order

When status statements conflict, use:

1. immutable run records and registered corrections for historical results;
2. versioned component/release profiles and the technical evidence freeze;
3. the prospective real-world product scope;
4. the active release plan;
5. this dated operational status;
6. the live GitHub Project fields and dependencies;
7. component guides and historical plans.

Never edit an old result to make it appear successful. Add a correction or a
new prospective run and retain the original evidence.
