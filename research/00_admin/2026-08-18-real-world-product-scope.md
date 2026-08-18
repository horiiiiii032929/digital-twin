# Real-world Course Digital Twin product scope

Date: 2026-08-18

Status: authoritative for prospective product delivery

Supersedes the delivery constraints in
[`2026-07-27-frontier-digital-twin-scope.md`](2026-07-27-frontier-digital-twin-scope.md)
for future work. Historical experiment plans, results, claims, profiles, and
freeze records remain unchanged and authoritative for their own runs.

## Product goal

Deliver a deployed, invite-only Course Digital Twin that a real professor can
configure and publish and that authorized students can use for persistent,
citation-grounded tutoring.

The merged local professor/student workspace is the product UX baseline, not
the completed product. The release target is a real hosted pilot with
credentialed roles, governed multimodal source ingestion, durable state,
observable operations, recovery, and evidence from realistic users and
workloads.

This is still an evaluation-first project. Deployment does not convert an
experimental model or component into a production selection. Every replaceable
model, parser, retriever, prompt, policy, judge, and architecture boundary keeps
an explicit control, versioned evidence, hard gates, and rollback.

## Product-level definition of done

### Administrator

- Invite, revoke, recover, and assign administrator, professor, and student
  accounts without synthetic identity headers.
- Associate users with permitted courses and releases.
- Inspect service health, ingestion failures, audit events, provider usage,
  cost, and capacity without exposing unnecessary course or student content.
- Apply retention, deletion, export, backup, restore, and incident procedures.

### Professor

- Create and manage multiple courses.
- Upload approved selectable-text and scanned PDFs containing prose, tables,
  diagrams, equations, screenshots, and mixed layouts.
- Review source permission, sensitivity, version, extraction, excluded content,
  and processing failures.
- Configure teaching behaviour, tutoring policy, examples, tone, boundaries,
  and academic-integrity behaviour through the chat-led workflow.
- Preview representative questions and inspect grounding, citations, policy
  behaviour, and known failures before publication.
- Publish, withdraw, update, and roll back a Digital Twin atomically.

### Student

- Sign in and access only assigned published courses.
- Start and resume persistent single- and multi-turn tutoring conversations.
- Receive grounded tutoring, clarification, refusal, or no-evidence actions.
- Inspect source, version, page, region, and approved crop citations.
- Recover from network, provider, ingestion, and stale-release failures without
  losing input or crossing a permission boundary.

### Operations

- Run the API, web application, durable database, object storage, and
  asynchronous ingestion jobs in an HTTPS staging environment.
- Apply versioned migrations and environment-specific configuration with
  managed secrets.
- Emit redacted structured logs, metrics, traces, audit events, health checks,
  alerts, and provider/token cost controls.
- Demonstrate backup, restore, rollback, deletion, rate limits, quotas, and
  bounded capacity from clean infrastructure.

## Evaluation programme

### E1: trusted multimodal product grounding

Repair the known multimodal region-metric defect before selecting another
candidate. The historical V3 result is retained and corrected or invalidated;
it is never overwritten.

Replace coarse OCR line grouping and page-level descriptions with region-aware
extraction for reading order, columns, tables, cells, figures, equations,
captions, and scans. Preserve original page/region lineage and keep heavyweight
visual processing offline. Generated descriptions are metadata, not source
truth. Gemma is excluded from the new candidate path; any replacement vision
model must be qualified prospectively behind a provider-neutral interface.

Use a new development set. Keep the existing 24-case multimodal held-out split
closed until the candidate, configuration, metrics, gates, and analysis are
frozen. Retain the selected text retriever as the explicit fallback.

### E2: large factual QA scale benchmark

Implement the professor's suggestion as a separate benchmark approaching
10,000 factual question-answer cases. Build a larger permission-safe dummy
document corpus first, including a meaningful multimodal slice, then generate
and cross-check cases with multiple independent LLMs.

Multi-model agreement is not ground truth. Every retained case requires source
evidence, provenance, deterministic validation, deduplication, disagreement
handling, and a stratified human audit. Pilot the process before scaling. Keep
this dataset separate from the verified 100-case retrieval benchmark and the
Professor Digital Twin fidelity comparison.

### E3: Professor Digital Twin fidelity

Hold the question, evidence, generator, and decoding fixed while comparing a
generic assistant, grounded generic tutor, and professor-configured Digital
Twin. Run deterministic grounding, citation, safety, and policy gates before
qualitative judging. Calibrate automated judges against independent professor
or expert labels; do not rely on an LLM judge alone.

The earlier invalid C0-C3 result remains diagnostic. Its held-out split stays
closed until a new prospective development result passes all reliability and
grounding gates.

### E4: deployed product and human workflow validation

Run one frozen release candidate through administrator, professor, and student
journeys in staging. Measure task success, grounding, citation validity,
policy behaviour, isolation, reliable turn completion, latency, queue time,
cost, resource use, failure attribution, recovery, backup/restore, and rollback.

After consent, privacy, recruitment, and supervisor approval are recorded, run
a small invite-only usability pilot. Keep usability, trust, tutoring quality,
and learning outcomes as separate claims. No learning-outcome claim follows
from a usability pilot.

## Delivery gates

| Gate | Target | Required outcome |
| --- | --- | --- |
| P0 Product UX baseline | Complete | PR #83 merged; professor and student conversation-first workspaces retained as the implementation baseline |
| P1 Multimodal product grounding | 2026-08-28 | Correct evaluator, region-aware ingestion/retrieval, product citation integration, prospective decision and fallback |
| P2 Deployable product foundation | 2026-09-06 | Credentialed RBAC, durable data/storage, jobs, staging deployment, observability, security, backup/restore, and rollback |
| P3 Pilot validation and release | 2026-09-13 | Large factual benchmark, calibrated fidelity, operational/end-to-end evidence, and a release or explicit no-release decision |

Dates are planning targets, not evidence or release claims. A failed hard gate
produces a documented Refine, Go Deeper, or Drop decision rather than a hidden
schedule-driven pass.

## Critical-path issues

1. [#85](https://github.com/horiiiiii032929/digital-twin/issues/85) corrects
   and hardens multimodal evaluation.
2. [#86](https://github.com/horiiiiii032929/digital-twin/issues/86) builds the
   region-aware multimodal product path.
3. [#88](https://github.com/horiiiiii032929/digital-twin/issues/88) replaces
   prototype infrastructure with a deployable foundation.
4. [#87](https://github.com/horiiiiii032929/digital-twin/issues/87) creates the
   large factual QA scale benchmark.
5. [#24](https://github.com/horiiiiii032929/digital-twin/issues/24),
   [#9](https://github.com/horiiiiii032929/digital-twin/issues/9), and
   [#25](https://github.com/horiiiiii032929/digital-twin/issues/25) provide
   fidelity, operations, and end-to-end release evidence.
6. [#10](https://github.com/horiiiiii032929/digital-twin/issues/10) is the
   approval-gated real-workflow/usability pilot.

#85 is complete. #86 implemented the prospective region-aware foundation and
recorded a Refine decision after its final synthetic development attempt passed
all quality/integration gates but failed the frozen relative p95 gate. The live
GitHub Project remains the source for the next unblocked execution item.

## Claim and safety boundaries

- Do not commit private course material, student interactions, credentials,
  consent records, `.env` files, or bulky per-case output.
- Do not use solution files, answer keys, submissions, or assessment answers.
- Do not send private data to a model/provider without a recorded permission,
  terms, retention, region, cost, and fallback decision.
- Do not claim production readiness, human usability, professor fidelity,
  learning improvement, adoption, or scale before the corresponding gate.
- Preserve every named favorable, unfavorable, invalid, and inconclusive
  result. Corrections link to originals; they never erase them.
- Keep the local demo, BM25, selected text profile, and deterministic generator
  available as explicit controls or rollbacks where applicable.
