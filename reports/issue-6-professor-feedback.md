# Issue #6 professor feedback

Date recorded: 2026-07-10

Related issue: #6 `[S1 06/28] Professor review for chat-led onboarding`

## Material reviewed

Prof. Lek received a short description of the five-question chat-led onboarding
flow and the fast onboarding demo video. The review request asked whether the
questions captured the professor's teaching perspective without making setup too
complex.

## Feedback

- The onboarding direction "sounds good."
- Limited guest access to a Canvas course may be available for later testing.
- The prototype should not be tightly integrated with Canvas because its value
  depends on whether sufficiently rich information is available there.

## Decision

`Keep`

Continue with the chat-led onboarding direction. The Sprint 1 artifact is a
workflow prototype with deterministic and synthetic outputs, not yet a live AI
Digital Twin.

## Implementation implications

- Keep approved local or synthetic documents as the baseline source path.
- Build source ingestion and retrieval behind provider-neutral interfaces.
- Add live LLM generation only after the approved-source boundary is explicit.
- Treat Canvas as an optional adapter after inspecting a safe guest or sample
  course.
- Do not commit credentials, private course materials, or student data.

## Next evidence target

Demonstrate one end-to-end grounded tutoring path:

Student question -> approved document retrieval -> tutor policy -> live LLM ->
grounded response with visible source evidence.
