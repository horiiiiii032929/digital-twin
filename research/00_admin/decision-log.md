# Decision Log

Record durable decisions here when they are not better represented as GitHub
issues.

| Date | Area | Decision | Evidence | Follow-up |
| --- | --- | --- | --- | --- |
| 2026-06-22 | Project | Scaffold research-style repository structure | GitHub Project 1 fields and roadmap issues | Mirror future decisions into project issues when useful |
| 2026-07-10 | Instructor onboarding | Keep the chat-led onboarding direction | Prof. Lek review recorded in issue #6 and `reports/issue-6-professor-feedback.md` | Build the grounded tutoring baseline with local approved documents |
| 2026-07-10 | Source architecture | Keep Canvas optional rather than tightly coupled | Prof. Lek noted that Canvas value depends on information richness | Evaluate a safe guest course only after the source-agnostic baseline works |
| 2026-07-15 | RAG retrieval | Refine rather than replace the provisional BM25 baseline | `research/05_evaluation/retrieval-v2-results.md`: dense passed abstention but missed quality; RRF improved coverage but failed abstention and nDCG | Add an evidence-sufficiency boundary and a newly frozen held-out set before live generation |
