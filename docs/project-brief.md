# Project brief

## Problem

Generic AI assistants do not reliably respect course boundaries, approved
evidence, instructor teaching behaviour, publication control, or academic-
integrity policy. A useful real-world system must let professors govern those
boundaries and must remain understandable, recoverable, and safe for students.

## Product direction

Deliver a deployed, invite-only Course Digital Twin for multiple professors
and courses. Professors govern approved text and multimodal sources, teaching
behaviour, tutoring policy, evaluation, publication, withdrawal, and rollback.
Authorized students receive persistent, course-isolated tutoring with
inspectable source, page, region, and version citations.

The current local professor/student application is the product UX baseline.
The target is a hosted pilot with credentialed identity, durable database and
object storage, asynchronous ingestion, observable operations, backup/restore,
and evidence from realistic workflows and workloads.

The authoritative prospective scope is the
[real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md).
Historical experiment records and the technical evidence freeze remain
authoritative for the results they document.

## Research and evaluation questions

1. Can region-aware multimodal ingestion and retrieval improve precise
   grounding for scans, tables, diagrams, equations, and mixed-layout course
   material over the selected text path without requiring a heavyweight vision
   model online?
2. With generator and evidence held constant, does professor configuration
   improve fidelity, pedagogical behaviour, misconception handling, and
   academic-integrity compliance over generic and grounded-generic controls?
3. Can the deployed system complete administrator, professor, and student
   journeys with correct authorization, citation lineage, publication control,
   recovery, observability, and bounded capacity?
4. Can a source-linked generation and review method produce a trustworthy
   factual-QA dataset approaching 10,000 cases while exposing quality,
   abstention, isolation, latency, and cost failures that the verified 100-case
   benchmark cannot estimate?

## Delivery phases

- **P0 — Product UX baseline:** completed by merged PR #83.
- **P1 — Multimodal product grounding:** correct the evaluator, implement real
  region extraction and product ingestion, then select or reject a candidate.
- **P2 — Deployable product foundation:** credentialed RBAC, durable data and
  storage, ingestion jobs, staging deployment, observability, security,
  backup/restore, and rollback.
- **P3 — Pilot validation and release:** large factual-QA dataset quality, calibrated
  fidelity, end-to-end and operational validation, and approval-gated real-user
  workflow evidence.

## Current phase

PR #83 merged the reviewed professor/student conversation-first workspace.
Text retrieval retains the experimentally selected M2 hybrid profile with
BM25 rollback. The bounded synthetic publication/student foundation passes its
registered 19 checks. These are useful baselines, not production evidence.

Issue #85 corrected and audited the multimodal evaluator. Issue #86 now provides
the prospective region-aware ingestion and citation foundation, with a
registered Refine decision and no selected multimodal profile. The deployment, large-benchmark,
fidelity, operations, end-to-end, and pilot issues are explicitly downstream.

## Claim boundary

A deployment, demo, LLM agreement count, or successful synthetic flow does not
by itself establish production readiness, professor fidelity, human usability,
learning improvement, adoption, or an SLA. Each claim requires its prospective
gate and recorded evidence.
