# Historical README implementation notes

Preserved from the README at commit `d25e2727336c48cced3c84ce680fc25c7554e91c`.
These dated rollout statements are historical context, not current publication
status or authorization to execute an experiment. Relative Markdown links were
adjusted for this archive location.

## Invite-only staging candidate

The current foundation adds credentialed administrator/professor/student
access, secure revocable cookie sessions, durable SQLite schema migrations,
owned onboarding state, content-addressed source storage, recoverable ingestion
jobs, password/account/data lifecycle controls, redacted operations,
backup/restore, and a Caddy HTTPS package. The exact V8 images built and became
healthy in isolated local HTTPS, and clean administrator bootstrap plus source
ingestion worked. Publication intentionally failed closed because no production
evidence-sufficiency method was selected. The current source adds the corrected
provider-neutral successor boundary, a deterministic source-linked 120-case
decision draft, and a bounded independent-review workflow. The no-call
simulation passes, but the actual independent review and dataset freeze remain
pending, and the source has not been rebuilt into images or selected for release. Issue
[#105](https://github.com/horiiiiii032929/digital-twin/issues/105) owns that R1
release blocker; public DNS/certificate and clean-host rehearsal follow only
after it passes.

Start with [staging deployment and recovery](../../docs/deployment.md) and the
[deployment threat model](../../docs/deployment-threat-model.md). Never copy a real
secret into a tracked file.

## Current implementation status

Start with the dated [current project status](../../docs/current-status.md) for the
active branch, evidence decisions, GitHub queue, and next human gate.

Implemented in the Sprint 1 prototype:

- Chat-led onboarding workflow with deterministic follow-up handling.
- Metadata-only source inventory with permission, sensitivity, and label state.
- Structured tutor policy generation with release blockers.
- Preview evidence cases with source audit, decisions, and custom prompt review.
- Confirm/discard revision loop for professor feedback.
- Approval checklist that gates draft release status.
- Modular onboarding domain, API factory/routes, and frontend adapters with
  compatibility facades for the original imports.

Implemented as Sprint 2 foundations:

- Provider-neutral document, chunk, retrieval, citation, and tutor-answer models.
- Chunker, retriever, and asynchronous tutor-generator protocols.
- Synthetic, network-free fixtures used only by tests.
- Permission-gated local UTF-8 text, Markdown, and selectable-text PDF parsing.
- Stable source-version, content-hash, page, locator, and figure provenance.
- Deterministic heading/paragraph chunking with inherited tutoring permission.
- Evaluated BM25 retrieval with permission and active-version filtering plus
  explicit source evidence.
- Retrieval v2 comparison of BM25, local BGE-small dense retrieval, and
  reciprocal-rank fusion. The result is `Refine`, with no v2 replacement.
- A versioned component profile, evaluation records, result registry, and CI
  validators that prevent undocumented implementation replacement.
- An explicit, swappable evidence-sufficiency boundary and a 50-case held-out
  comparison. The result is `Refine`, with no safe gate selected.
- Deterministic grounded-generation, tutor-policy, citation-validation, and
  provider-failure controls behind replaceable interfaces.
- A LiteLLM adapter and local Ollama benchmark path with latency, token, model,
  and reported-cost traces.
- A frozen synthetic generator-qualification boundary for DeepSeek V4 Flash:
  P0/P1 failed development citation correctness, while strict-evidence P2
  passed all 48-case development floors, 36/36 repeated stability attempts,
  104/104 one-time held-out attempts, and a 20/20 second-review sample. The
  exact generator and P2 prompt are selected in the experimental profile with
  the deterministic rollback; the second review was not independent human
  judgment.
- A registered local Gemma 3 4B exploratory result: structural checks passed,
  but factual-support review passed only 15/18 model answers, so no generator or
  prompt was selected.
- The one-time 60-case cross-course held-out comparison selected M2 hybrid RRF
  for the experimental profile, with BM25 retained as the explicit rollback.
- A bounded synthetic-account student workflow with fail-closed course/release
  authorization, SQLite conversation persistence, citations, idempotency,
  provider fallback, and restart recovery.
- A responsive student tutoring workspace with release-bound conversation
  restoration, grounded citation inspection, stable retries, stale-release
  recovery, and a mobile citation sheet.
- An evaluation-gated publication lifecycle with durable drafts, atomic release
  replacement, withdrawal, rollback, and stale-conversation denial. The v2
  synthetic architecture result passes 19/19 acceptance checks.
- A prospective region-aware PDF foundation for tables, cells, diagrams,
  equations, scans, mixed layouts, original crops, release-ready chunks, and
  access-checked student crop citations. Its final 21-case synthetic
  development attempt passed 13/14 gates and selected no multimodal profile
  because the relative warm-p95 gate failed.
- A frozen experimental technical baseline with machine-checked claim limits,
  component-to-result links, reproducibility commands, rollback, and explicit
  unsupported capacity/deployment/learning claims.
- A prospective A1 single-host staging foundation with 41/41 local checks,
  checksum-verified clean restore, 0% errors across 100 synthetic API requests,
  2.765 ms local API p95, 0.30 GiB peak RSS, and explicit A0 demo rollback.

Current evidence and limitations:

- The 13-lecture IT5002 pilot is development evidence, not the final research
  boundary or selected method.
- In its 13 answerable development cases, local Qwen3 reranking retrieved
  complete evidence for 10 cases versus 3 for heading-aware BM25.
- The separate 59-case one-time rapid run failed after 29 cases. It is
  registered as invalid, retired, and never rerun.
- All observed no-evidence results used calibration cases and therefore are not
  independent final evidence.
- Jina was retired before hosted execution and is not a selection dependency.
  Local Qwen3 remains the semantic provider binding for the M0-M3 study.
- Local M3 preserved 80.0% complete-evidence success after optimization, but
  its best tested p95 was 28.13 seconds. It remains a research candidate and is
  deployment-ineligible on the reference hardware. The held-out comparison
  selected M2, which reached 85% complete evidence@3 versus BM25's 80% at
  164 ms warm p95; BM25 remains the rollback.
- Synthetic product activation now covers credentialed professor/admin/student
  access, publication, scanned-PDF ingestion, visual citations, migrations,
  restart, backup/restore, lifecycle controls, and a bounded 100-request local
  capacity result. It still lacks a production OCR/layout provider, valid
  professor-fidelity and real-workflow evidence, public HTTPS rehearsal,
  representative concurrent selected-model capacity, and release-candidate
  evidence.

The active goal is release of an invite-only Course Digital Twin for multiple
professors and courses, not a one-course RAG pilot, local-only demonstration,
or standalone benchmark. The merged professor/student workspace is the UX
baseline. PR #103 merged the deterministic 10,000-package factual-QA successor
and a provider-unauthorized pilot simulation. PR #104 merged the V8 image
requalification and its fail-closed evidence-sufficiency blocker. The active
#105 branch is now frozen at V12 with the corrected open-set boundary, authored
120-case decision draft, and bounded review workflow. The draft remains
unfrozen and unopened; provider review and candidate execution remain blocked.
Remaining release gates cover a selected answerability method, factual quality,
professor fidelity, target-host deployment and operations, complete workflows,
privacy, and approval-gated usability.

See the
[real-world product scope](../../research/00_admin/2026-08-18-real-world-product-scope.md)
for the prospective product and the [release plan](../../docs/release-plan.md) for
the active delivery order. The
[technical evidence freeze](../../reports/technical-evidence-freeze-2026-08-18.md)
remains authoritative for the earlier experimental baseline and is not
rewritten by the expanded product goal.

## Sprint 1 Onboarding Prototype

The current prototype supports the professor review loop for chat-led Course
Digital Twin setup: metadata-only source inventory, generated tutor policy,
evidence-backed preview cases, chat-based revision proposals, and a persisted
approval checklist.

Sprint 1 keeps uploads metadata-only and uses a deterministic source catalog for
preview grounding. It does not read local file contents or call a live search
provider.

Prof. Lek reviewed the onboarding direction and approved continuing with the
chat-led approach. Canvas should remain an optional source connector rather than
a required dependency; approved local or synthetic documents are the baseline
for the next grounding prototype.

See [docs/onboarding-prototype.md](../../docs/onboarding-prototype.md) for the reviewer
flow and [tests/manual/onboarding-prototype.md](../../tests/manual/onboarding-prototype.md)
for manual verification steps.

See [reports/issue-6-professor-feedback.md](../../reports/issue-6-professor-feedback.md)
for the Sprint 1 review decision and its implementation implications.

See [docs/github-project.md](../../docs/github-project.md) for how repository issues
map to the linked GitHub Project fields.
