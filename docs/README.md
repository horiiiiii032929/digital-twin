# Documentation map

Use this page to distinguish active implementation guidance from historical
design records.

## Start here after submission

- [Submitted report and source package](../reports/submitted/2026-09-06/README.md)
- [Final report versus the latest 70-slide presentation — 9 September](final-report-vs-latest-slides-2026-09-09.md)
- [Post-report learning and answer runtime candidates](post-report-learning-runtime-2026-09-08.md)
- [Post-report app and evaluation priorities — Japanese, 8 September](post-report-development-inventory-2026-09-08-ja.md)
- [Runnable setup and verification record](post-submission-verification.md)
- [Repository maintenance and reference protection](repository-maintenance.md)
- [Evaluation registry](../research/05_evaluation/result-registry.md)

The guides below retain their original project and release context. Use their
dates and linked profiles to distinguish implemented behaviour from prospective
plans; older milestones are not current deployment claims.

## Active product and architecture

- [Application testing summary — all walkthrough and fix runs through 10 September](application-test-summary-2026-09-10.md)
- [AWS pilot browser scenario test plan](../tests/manual/aws-pilot-scenario-plan-2026-09-09.md)
- [Connected course lifecycle simulation](../tests/manual/aws-pilot-lifecycle-simulation-v1.md)
- [Seven-persona roleplay demo](seven-persona-demo.md)
- [Deployed demo accounts and seed operations](pilot-demo-accounts.md)
- [Synthetic pilot seed data design](seed-data-design.md)

- [Course Digital Twin release plan](release-plan.md)
- [Current project status](current-status.md)
- [Real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md)
- [Technical evidence freeze](../reports/technical-evidence-freeze-2026-08-18.md)
- [Frozen claim-to-evidence matrix](../reports/claim-to-evidence-matrix.md)
- [Project brief](project-brief.md)
- [Digital Twin architecture](architecture.md)
- [Autonomous tutoring loop V2.1 — canonical prospective design](autonomous-tutoring-loop-v2.md)
- [Autonomous tutor best-practice audit — research basis](../research/01_literature/2026-08-31-autonomous-tutor-best-practice-audit.md)
- [Proactive Professor Digital Twin outreach](proactive-outreach.md)
- [Proactive mixed-initiative tutoring research](../research/01_literature/2026-08-27-proactive-mixed-initiative-tutoring.md)
- [Component inventory](component-inventory.md)
- [Quality and learning plan](quality-and-learning-plan.md)
- [GitHub Project workflow](github-project.md)
- [Privacy and ethics](privacy-and-ethics.md)
- [Evaluation architecture](evaluation-architecture.md)
- [Evaluation data flow and threat model](evaluation-data-flow-and-threat-model.md)
- [Staging deployment and recovery](deployment.md)
- [Deployable product threat model](deployment-threat-model.md)

The product definition is maintained in
[`research/00_admin/2026-08-18-real-world-product-scope.md`](../research/00_admin/2026-08-18-real-world-product-scope.md).
The [release plan](release-plan.md) is the operational order of work.
The earlier frontier scope and all frozen experiment records remain historical
sources of truth for the decisions and results they document.

### Autonomous tutoring reading order

1. Use [Autonomous tutoring loop V2.1](autonomous-tutoring-loop-v2.md) as the
   only implementation-facing prospective architecture.
2. Use the
   [best-practice audit](../research/01_literature/2026-08-31-autonomous-tutor-best-practice-audit.md)
   for the academic justification, alternatives, limitations, and evidence.
3. Use the earlier
   [loop and evaluation research](../research/01_literature/2026-08-31-autonomous-tutoring-loop-and-evaluation.md)
   for the temporal-loop and evaluation synthesis.
4. Treat [Autonomous tutoring graph V1](autonomous-tutoring-graph.md) as the
   historical T1-v1 design and local-control evidence only.

## Active component guides

- [Onboarding prototype](onboarding-prototype.md)
- [Local ingestion](local-ingestion.md)
- [Local retrieval](local-retrieval.md)
- [Live generation](live-generation.md)
- [Student tutoring workflow](student-workflow.md)
- [RAG and LLM benchmarking](rag-and-llm-benchmarking.md)
- [Agent contracts](agents/README.md)

Component guides describe implemented or previously evaluated boundaries. When
they mention an older sprint, fixed provider, or retired experiment, the
versioned result/decision remains historically valid but the roadmap instruction
is superseded by the active scope and component inventory.

## Historical designs

Historical implementation plans and specifications live under
[`archive/`](archive/README.md). They explain why the current code exists but
must not be used as the active delivery plan.

The [Autonomous tutoring graph V1](autonomous-tutoring-graph.md) remains in the
main documentation tree because current T1-v1 evidence binds to it, but it is
not the prospective implementation specification.

Research experiment plans and results are not moved to the documentation
archive. Their dates, frozen protocols, failures, and decisions are durable
research evidence.

- [AWS browser lifecycle run 001](../tests/manual/aws-pilot-lifecycle-001-results.md): 84 sustained learner turns, deployed coding fixes, retained failures and [106-case coverage](../tests/manual/aws-pilot-lifecycle-001-coverage.md).

- [Slide-aligned coding fix plan](../research/04_experiments/2026-09-09-slide-aligned-code-fix-plan.md): latest 70-slide presentation fingerprint, mandatory preserved contracts, known AWS differences and bounded repair gates.

- [Slide-aligned coding-fix results](../research/05_evaluation/slide-codefix-001-results.md): bounded diagnostics deployed; eight-turn follow-up and remaining failures.
