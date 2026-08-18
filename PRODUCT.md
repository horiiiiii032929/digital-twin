# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The primary user of the professor console is an instructor preparing a
course-specific Digital Twin before students can use it. The instructor needs to
decide which course sources are permitted, express teaching and integrity rules,
inspect generated policy, compare grounded preview behavior, and retain final
release authority.

Students are a separate downstream audience. They use an approved tutor release;
they do not participate in this configuration workflow.

## Product Purpose

Course Digital Twin helps an instructor configure and verify an evidence-grounded
course tutor. Success means that the professor can understand what the tutor may
use, how it should teach, what evidence supports its behavior, which blockers
remain, and whether it is safe to approve for the bounded prototype.

## Positioning

Unlike a generic course chatbot, the system binds conversational configuration to
explicit source permissions, inspectable tutor policy, evidence-backed previews,
and a professor-controlled approval gate.

## Operating Context

The professor console is an occasional but concentrated setup and review
workspace, primarily used on desktop before a tutor release. It combines an
LLM-style interview with structured source, policy, preview, revision, approval,
and workflow-trace records. Canvas remains an optional future connector rather
than a required dependency.

## Capabilities and Constraints

- The professor workflow has exactly five stages: Sources, Interview, Policy,
  Preview, and Approval.
- The current onboarding prototype stores course-material metadata and permission
  decisions; it does not upload or parse source contents through this screen.
- The interview generates a structured tutor policy through the existing
  deterministic prototype service.
- Preview cases expose grounding labels, comparison behavior, warnings, and an
  explicit professor decision.
- Professor feedback can produce a revision proposal that must be confirmed or
  discarded.
- Approval remains blocked until the implemented source, interview, policy,
  preview, and checklist conditions are satisfied.
- The interface must not invent integrations, analytics, course identities,
  collaborators, model capabilities, or deployment readiness.
- The frozen technical baseline is experimental evidence, not a release-ready
  production claim.

## Brand Commitments

The product name is Course Digital Twin. The interface should feel familiar to
users of mature LLM workspaces rather than like a research report or evaluation
dossier. Familiarity may draw on patterns used by ChatGPT, Claude, and NotebookLM,
without copying their branding, proprietary assets, or unsupported capabilities.

## Evidence on Hand

- Product scope and technical boundary: `README.md` and
  `research/00_admin/2026-07-27-frontier-digital-twin-scope.md`.
- Professor onboarding behavior: `docs/onboarding-prototype.md`.
- Current engineering and research status: `docs/current-status.md` and
  `reports/technical-evidence-freeze-2026-08-18.md`.
- UI redesign evaluation: `reports/issue-80-professor-console-redesign.md`.

No human-usability study, professor approval of this final interface, production
capacity evidence, or real-course deployment evidence is currently available.

## Product Principles

- Keep professor authority explicit at every consequential decision.
- Make source grounding, uncertainty, and release blockers inspectable.
- Use conversation for elicitation and structured controls for governance.
- Prefer familiar product conventions over research-instrument presentation.
- State prototype limitations honestly without making them the main interface.

## Accessibility & Inclusion

The web interface must support keyboard navigation, visible focus, screen-reader
names, non-color status communication, 200% zoom, reduced motion, and practical
touch targets on narrow screens.
