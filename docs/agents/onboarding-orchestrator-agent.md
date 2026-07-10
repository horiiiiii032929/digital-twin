# Onboarding Orchestrator Agent

## Purpose

Guide the professor through chat-led Course Digital Twin setup and coordinate
the transition from interview answers to reviewable artifacts.

## Current status

Prototype. Implemented as deterministic workflow state in
`src/digital_twin/onboarding_workflow.py`, exposed through the FastAPI onboarding
session routes, and rendered by the web onboarding chat.

## Inputs

- Instructor answers to setup questions.
- Current onboarding session state.
- Existing policy, preview, revision, and approval state after draft generation.

## Outputs

- Next instructor prompt.
- Captured setup answer.
- Workflow trace entry.
- Draft tutor policy trigger after required questions are complete.
- Revision proposal handoff when post-generation feedback is actionable.

## Guardrails

- Do not advance on blank answers.
- Ask a follow-up when an answer is too vague to encode safely.
- Preserve generated review artifacts after the interview is complete.
- Keep the tutor draft-only until downstream release blockers clear.

## Evaluation

- Step transition tests.
- Vague-answer tests.
- Post-generation message preservation tests.
- Manual onboarding flow verification.

## Open work

- Replace deterministic question handling with model-assisted extraction only
  after the schema and red-team tests are stable.
- Add explicit session persistence before multi-user testing.
- Add richer trace reasons for professor-facing explainability.
