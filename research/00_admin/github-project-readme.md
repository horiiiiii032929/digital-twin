# Digital Twin Product Delivery

Status date: 2026-08-18

This Project tracks the transition from an evaluated local prototype to a
deployed, invite-only Course Digital Twin that real professors can configure
and publish and authorized students can use.

## Current position

- PR #83 merged the reviewed conversation-first professor and student
  workspaces. Issues #82 and #84 are `Done / Keep`.
- M2 hybrid text retrieval remains the experimental selection with BM25
  rollback. The synthetic publication/student foundation remains 19/19.
- These components are a product baseline, not release or usability evidence.
- Multimodal retrieval has no selected profile and is not integrated into real
  ingestion. A concrete duplicate-loop defect in the V3 region relevance
  calculation must be corrected before its region metrics are trusted.
- Professor fidelity remains `Refine / Paused`; the prior C0-C3 comparison is
  invalid for selection and its held-out split remains closed.
- Credentialed identity, durable production storage, source jobs, deployment,
  observability, backup/restore, capacity, and human workflow evidence remain
  incomplete.

## Product goal

The deployed pilot must provide:

- credentialed administrator, professor, and student roles;
- independently configurable multi-course Digital Twins;
- governed text and multimodal ingestion for scans, tables, diagrams,
  equations, screenshots, and mixed layouts;
- professor configuration, preview, evaluation, publication, withdrawal,
  update, and rollback;
- course-isolated persistent student tutoring with source/page/region/version
  citations;
- durable database and object storage, migrations, ingestion jobs, HTTPS
  deployment, managed secrets, observability, backup/restore, and rollback;
- calibrated fidelity, factual correctness, safety, isolation, reliability,
  latency, cost, capacity, and approval-gated usability evidence.

## Active gates

| Gate | Target | Required outcome |
| --- | --- | --- |
| P0 Product UX baseline | Complete | PR #83 merged; local demo and tests retained |
| P1 Multimodal Product Grounding | 2026-08-28 | Correct evaluator, region-aware product ingestion/retrieval, visual citations, prospective decision and fallback |
| P2 Deployable Product Foundation | 2026-09-06 | Credentialed RBAC, durable data/storage, jobs, staging deployment, observability, security, backup/restore, rollback |
| P3 Pilot Validation and Release | 2026-09-13 | Large factual benchmark, calibrated fidelity, end-to-end/operations evidence, release or explicit no-release decision |

## Critical path

1. #85 corrects and hardens multimodal evaluation and is the only item in
   progress.
2. #86 builds region-aware multimodal product grounding. Gemma is excluded;
   any replacement model must be qualified prospectively.
3. #88 replaces prototype infrastructure with a deployable foundation.
4. #87 builds a larger permission-safe dummy document corpus and a separate
   factual QA benchmark approaching 10,000 cases, including a multimodal slice.
5. #24, #9, and #25 provide fidelity, operational, and deployed end-to-end
   evidence.
6. #10 runs only after consent/privacy/recruitment approval and validates real
   workflows without converting usability into a learning-outcome claim.

Product goal #8 is the parent. GitHub blocked-by links encode the sequence.
Issues #13 and #44 retain report/presentation and professor communication.

## Evaluation contract

Every replaceable component and architecture boundary defines its decision,
control, candidates, dataset, metrics, gates, failure cases, operational
measures, and rollback before execution. Every favorable, unfavorable,
invalid, or inconclusive named result remains registered.

The verified 100-case benchmark remains the high-confidence research set. The
new large factual benchmark is separate and uses multi-model generation and
cross-checking, deterministic source validation, disagreement handling, and a
stratified human audit. Multi-model agreement is not ground truth.

## Operating rules

- Keep one unblocked execution issue `In Progress`.
- Do not open held-out data before candidate/configuration/gates are frozen.
- Do not commit private course or student data, credentials, consent records,
  `.env`, or bulky per-case outputs.
- Do not use solution files, answer keys, or submissions.
- Do not claim deployment, production readiness, professor fidelity, human
  usability, learning improvement, adoption, or an SLA before its gate.
- Preserve the local demo, text retrieval, BM25, and deterministic paths as
  explicit controls or rollbacks where applicable.

The durable prospective baseline is
`research/00_admin/2026-08-18-real-world-product-scope.md`. Historical
experiment records and the technical evidence freeze remain authoritative for
their own results.
