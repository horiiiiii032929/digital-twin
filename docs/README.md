# Documentation map

Use this page to distinguish active implementation guidance from historical
design records.

## Active product and architecture

- [Current project status](current-status.md)
- [Real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md)
- [Technical evidence freeze](../reports/technical-evidence-freeze-2026-08-18.md)
- [Frozen claim-to-evidence matrix](../reports/claim-to-evidence-matrix.md)
- [Project brief](project-brief.md)
- [Digital Twin architecture](architecture.md)
- [Component inventory](component-inventory.md)
- [Quality and learning plan](quality-and-learning-plan.md)
- [GitHub Project workflow](github-project.md)
- [Privacy and ethics](privacy-and-ethics.md)
- [Evaluation architecture](evaluation-architecture.md)
- [Evaluation data flow and threat model](evaluation-data-flow-and-threat-model.md)
- [Staging deployment and recovery](deployment.md)
- [Deployable product threat model](deployment-threat-model.md)

The authoritative prospective product scope is maintained in
[`research/00_admin/2026-08-18-real-world-product-scope.md`](../research/00_admin/2026-08-18-real-world-product-scope.md).
The earlier frontier scope and all frozen experiment records remain historical
sources of truth for the decisions and results they document.

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

Research experiment plans and results are not moved to the documentation
archive. Their dates, frozen protocols, failures, and decisions are durable
research evidence.
