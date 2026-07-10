# AI agent scaffolds

This directory defines the project-facing contracts for each AI agent in the
Course Digital Twin system. The files are scaffolds, not production prompts.
They should stay implementation-facing: inputs, outputs, safety rules, current
status, and open work.

## Agent map

| Agent | Status | Primary surface |
| --- | --- | --- |
| [Onboarding Orchestrator Agent](onboarding-orchestrator-agent.md) | Prototype | Instructor setup chat and workflow state |
| [Source Governance Agent](source-governance-agent.md) | Prototype | Source inventory, permissions, and source labels |
| [Tutor Policy Agent](tutor-policy-agent.md) | Prototype | Generated tutor policy and release blockers |
| [Preview Evidence Agent](preview-evidence-agent.md) | Prototype | Response previews, source audit, and acceptance evidence |
| [Revision Review Agent](revision-review-agent.md) | Prototype | Professor feedback to confirmed policy revision |
| [Student Tutoring Agent](student-tutoring-agent.md) | Planned | Student-facing tutor responses |
| [Learning Gap Analytics Agent](learning-gap-analytics-agent.md) | Planned | Instructor-facing learning-gap summaries |

## Shared rules

- Keep instructor and student data out of committed fixtures and docs.
- Treat all uploaded course files as metadata-only until ingestion is explicitly
  implemented and approved.
- Prefer deterministic behavior in Sprint 1 tests.
- Make every release-affecting decision auditable through policy fields,
  preview decisions, source inventory, or approval checklist entries.
- Keep agent boundaries narrow enough that each agent can be evaluated
  independently.
