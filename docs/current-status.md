# Current project status

Status date: 2026-08-20

This is the operational starting point for prospective work. Frozen experiment
plans, result records, corrections, profiles, and the technical evidence freeze
remain authoritative for the historical runs and claims they document.

The repository-wide correctness audit is complete on `main` at merge revision
`db2f5e9` through PR
[#98](https://github.com/horiiiiii032929/digital-twin/pull/98):
all 434 executable or execution-affecting files are hash-bound and audited,
with zero pending files and zero open findings. The canonical verification gate
now fails if pending or open records reappear. The execution freeze remains
active for all general evaluation actions. It covers 52 protected entrypoints
and retains an exact bounded authorization only for the completed
`factual-qa-v3-oracle-pilot-001`. Manual review found material source-design
defects in the unexecuted `factual-qa-v3-scale-rehearsal-001`, so its bounded
authorization was revoked. The corrected
`factual-qa-v3-scale-rehearsal-002` source and evaluation logic have completed
manual review and remain blocked pending explicit execution authorization. No
path permits private or held-out data.

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
check passes 641 Python tests and 46 frontend tests, frontend lint, and the
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
connections. These corrections pass the current 641-test Python suite.
Frontend, verification, tooling, evaluation configuration, and historical
artifacts are also fully dispositioned in the current 434-file audit. Evaluation
execution remains unauthorized because the freeze is intentionally still
active pending the next explicit work decision.

## Current outcome

The project has moved from an experimental local-demo goal to a deployed,
invite-only real-world Course Digital Twin goal. The new prospective baseline is
the [real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md).

PR [#83](https://github.com/horiiiiii032929/digital-twin/pull/83) merged the
reviewed conversation-first professor and student workspaces into `main` at
`acaaecd`. Issues #82 and #84 are `Done / Keep`. The merged flow passed the
recorded repository checks, 19/19 synthetic publication/student checks,
responsive browser QA, and independent Impeccable review. This establishes the
product UX baseline; it does not establish human usability or production
readiness.

Issue [#88](https://github.com/horiiiiii032929/digital-twin/issues/88) remains
in progress with a **Go Deeper** local architecture result, but is now marked
externally blocked while a public host and domain are selected. The deployable
candidate passed 41/41 synthetic checks across credentialed access, professor
upload/publication, student answer/original-region citation, restart,
backup/clean restore, security, lifecycle, and bounded capacity. The measured
100-request error rate was 0%, API p50/p95 was 2.345/2.964 ms, ingestion was
52.455 ms, and peak RSS was 0.30 GiB on the development host. The professor UI
now supports resumable course/student/source/release delivery, and rendered
desktop/mobile QA passed without console errors. Public DNS/TLS, host-side
restore, and the staging walkthrough remain before #88 can close.
The tested local candidate is frozen at revision `e619df9` by
`deployable-product-foundation-freeze-v1`; its three external gates remain
explicitly pending.
The subsequent container rehearsal found and corrected a duplicate-image build
race and an eager demo-store import, then hardened Caddy to a non-root user. At
clean revision `1fcd6fd`, the exact images built and passed 15/15 live HTTPS
journey checks, 5/5 after a separate-project clean restore, and 5/5 after
switching back to the untouched original volume. Local Caddy TLS is now proven;
public DNS/trusted certificate issuance and the same rehearsal on the selected
host remain external gates.
The current candidate now uses model policy v2. It rejects Gemma, Claude, and
retired local general-Qwen calls before provider I/O; retains direct DeepSeek;
pins the exact prospective local `qwen3.5:9b-q4_K_M` artifact; controls optional
OpenRouter DeepSeek/Mistral routes; and retains exact Jina candidate identities.
At clean revision `c28ae5f`, the requalified V5 package passed 113/113 focused
policy/provider tests, 41/41 in-process checks, a clean image build, 15/15 live
HTTPS checks, and three 5/5 restart/restore/rollback replays with zero model
calls. V1-V5 remain historical evidence. The successor V6 freeze preserves the
same qualified V5 implementation and
evidence revision but narrows current-tree matching to 45 implementation and
configuration artifacts. Append-only evaluation records remain revision-bound
evidence without making every new research result invalidate the deployment
package.
V6's historical evidence remains valid, but its current-package match is now
explicitly suspended during the repository correctness audit. It authorizes no
release claim; a newly qualified deployable freeze is required after the
repository correctness freeze passes.

The exact local `qwen3.5:9b-q4_K_M` reviewer completed two 22-probe
synthetic-public method-development attempts. Both detected 11/11 planted
defects and 6/6 visual defects at USD 0. The corrected attempt also passed 6/6
clean visual controls and 11/11 derived failure labels, but falsely rejected
one correct cross-course abstention, so the local model remains advisory-only
and is not an autonomous acceptance gate. Direct DeepSeek remains the retained
path; an exact OpenRouter independent reviewer is prospective and uncalled.
PR [#93](https://github.com/horiiiiii032929/digital-twin/pull/93) merged the
foundation into `main` at `adf39af`; this accepts the local/container-qualified
implementation without promoting the still-pending public deployment claim.

GitHub Project 1 is reorganized around product goal
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
| Product UX | Keep as baseline | Professor and student conversation-first workspaces; responsive synthetic flows | Human workflow/usability evidence and complete real source/account lifecycle |
| Text retrieval | Keep experimentally | M2 hybrid BM25 plus local Qwen3 dense RRF selected on the one-time cross-course held-out comparison; BM25 rollback | Release-candidate end-to-end quality against realistic workload |
| Multimodal retrieval | Refine; no selection | Region-aware tables/cells/diagrams/equations/OCR, scanned-PDF API ingestion, original crop citations, 13/13 synthetic complete@3 and lineage; unfavorable historical and V2 attempt results preserved | Production OCR/layout qualification, representative real-PDF quality and end-to-end latency; frozen relative micro-p95 gate still failed |
| Generator and prompt | Historical experimental selection plus later Refine evidence | Versioned DeepSeek and deterministic boundaries and unfavorable results preserved | Stable currently available candidate, independently calibrated semantic review, and release binding |
| Professor fidelity | Refine / Paused | Invalid C0-C3 comparison and correction preserved; execution policy protects held-out | Independent expert calibration, valid prospective development comparison, and hard-gate pass |
| Publication/student core | Go Deeper as single-host staging candidate | Earlier 19/19 publication slice, 41/41 in-process foundation checks, built images, 25/25 live local-HTTPS/recovery checks, deterministic preflight, and A0 demo rollback | Public trusted HTTPS/target-host restore, real-workflow usability, representative source quality, and release-candidate evaluation |
| Large factual QA | Reviewed 120-case rehearsal pending execution authorization; no 10,000 scale | The 40-case synthetic-public oracle pilot passed every machine gate and its human audit. The corrected single-method 120-case successor has completed source and logic review with DeepSeek V4 Flash authoring, first-party OpenRouter Mistral Small 4 review, concurrency eight, 20 paired citation/lineage mutations, deterministic retention authority, and hard quality/speed/cost gates | Publish the reviewed design, separately freeze and authorize rehearsal 002, then pass the clean no-call preflight before the one-time execution |

## Immediate critical path

| Order | Issue | State | Exit condition |
| ---: | --- | --- | --- |
| 1 | Repository correctness freeze | Merged / Keep corrections | PR #98 merged at `db2f5e9`; the current branch has 434/434 files audited and keeps the global freeze with one completed bounded run ID |
| 2 | [#87 Factual-QA dataset quality](https://github.com/horiiiiii032929/digital-twin/issues/87) | In Progress / reviewed rehearsal pending authorization | Publish rehearsal 002, separately authorize its bounded execution, pass the clean no-call preflight, and run it before deciding whether to scale |
| 3 | [#88 Deployable product foundation](https://github.com/horiiiiii032929/digital-twin/issues/88) | In Progress / Go Deeper / blocked | Local 41/41 and 25/25 HTTPS/recovery checks passed; complete public DNS/TLS, target-host restore, and public staging walkthrough after host/domain selection |
| 4 | [#24 Fidelity calibration](https://github.com/horiiiiii032929/digital-twin/issues/24) | Todo / Refine | Calibrate the automated evaluator against independent expert labels; keep this separate from factual QA |
| 5 | [#9 Production operations](https://github.com/horiiiiii032929/digital-twin/issues/9) | Todo / blocked by #88 | Isolation, recovery, observability, backup/restore, security, latency, cost, and capacity evidence on the target host |
| 6 | [#25 Deployed end-to-end validation](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / blocked by #24 and #88 | One immutable staging release candidate passes or receives an explicit Refine/Drop decision |
| 7 | [#10 Real-workflow pilot](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / blocked by #9 and #25 | Approval-gated professor/student workflow evidence; usability remains separate from learning outcomes |

Issues #85 and #86 are complete and archived from the live Project view. PR #91 merged the tested multimodal product
foundation and three registered prospective development attempts. Attempt 003 passed 13/14 gates:
all quality, safety, action, text-control, and lineage gates passed; relative
warm p95 failed at 0.053 ms versus 0.023 ms. No multimodal profile was selected,
and the historical held-out split was not opened. Issue #87 preserves attempt
002's passed machine gates and uncompleted audit as historical v2 evidence, but
the active boundary is now the broader v3 no-model implementation over the
eligible Academia Vault. This remains method validation, not a model benchmark.
Issue #88 remains active but externally blocked; its implementation and local
qualification are complete enough for a controlled host rehearsal, not for a
real-user pilot.

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
recorded roles. `qwen3.5:9b-q4_K_M` and exact OpenRouter DeepSeek/Mistral routes
are prospective only; they require new project-specific quality evidence. See
[the current model policy](../research/00_admin/2026-08-19-current-model-policy-v2.md).

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
The corrected successor has completed manual source and evaluation-logic review
at 120 cases but is not yet frozen or authorized for execution. It uses
concurrent direct DeepSeek V4 Flash authoring and a first-party OpenRouter
Mistral Small 4 independent review, with 20 paired deterministic defect probes
and a 12-case priority human-audit packet. Both provider credentials are
present in the environment. The no-call preflight currently stops because the
reviewed instrument is intentionally not frozen and the design changes are not
yet committed. Scale toward 10,000 remains unauthorized.

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
4. this dated operational status;
5. the live GitHub Project fields and dependencies;
6. component guides and historical plans.

Never edit an old result to make it appear successful. Add a correction or a
new prospective run and retain the original evidence.
