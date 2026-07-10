# Instructor digital twin stack design

Date: 2026-06-25
Issue: #5 `[S1 06/28] Minimal chat-led onboarding prototype`

## Decision

Use a Python-backed web prototype with a model-independent workflow layer:

- Frontend: React, Vite, and TypeScript.
- Backend API: FastAPI on Python 3.11 or 3.12.
- Workflow orchestration: LangGraph v1.
- LLM portability: a small local adapter backed by LiteLLM.
- UI system: shadcn/ui with project design tokens.
- AI chat UI primitives: Prompt Kit components installed through the shadcn
  registry flow.
- Storage for Sprint 1: in-memory or fixture-backed state only.
- RAG for Sprint 1: out of scope; prepare interfaces but do not implement it.

This stack supports the onboarding prototype without locking the project to one
LLM provider or prematurely committing to a production data platform.

## Product framework

This project should not use an IoT-focused digital twin platform. The object
being modeled is not a physical asset, sensor, building, or machine. The useful
twin is an instructor-aligned teaching system with a reviewable policy.

The prototype should implement an Instructor Digital Twin Framework with these
layers:

1. Identity Layer: course identity, instructor role, and onboarding state.
2. Knowledge Layer: approved materials, source permissions, and source labels.
3. Pedagogy Layer: teaching approach, tutoring moves, misconception handling,
   examples, and feedback preferences.
4. Policy Layer: academic-integrity rules, refusal behavior, privacy rules, and
   release blockers.
5. Interaction Layer: onboarding interview, generated policy review, preview
   comparison, revision, and professor approval.
6. Evaluation Layer: generic-vs-configured comparison and later rubric scoring.
7. Governance Layer: consent, sensitive-data exclusion, versioning, and audit
   trail.

Sprint 1 should visibly demonstrate the Identity, Knowledge, Pedagogy, Policy,
Interaction, and Governance layers. The Evaluation layer can appear as preview
comparison evidence, but full scoring waits until the evaluation sprint.

## Architecture

The prototype should use this shape:

```text
apps/web
  React + Vite frontend
  shadcn/ui component system
  Prompt Kit chat primitives
  Chat-led onboarding UI
  Policy review/editor
  Preview comparison
  Approval checklist

services/api
  FastAPI backend
  LangGraph onboarding workflow
  LiteLLM-backed model adapter
  Deterministic prototype fixtures

src/digital_twin
  Python domain models
  Tutor policy schema
  Source permission rules
  Preview response fixtures
```

The frontend should call the backend through a small API boundary rather than
embedding workflow rules in React. The backend should expose onboarding session
operations, policy review operations, preview generation, and approval state.

## UI component system

The frontend should use shadcn/ui as the application component system. This
keeps the prototype visually consistent while still giving the repository local
ownership of component source code.

Use shadcn components for:

- buttons and icon buttons
- cards and review panels
- tabs or segmented controls
- forms, fields, checkboxes, and toggles
- dialogs or sheets if a review flow needs them
- alerts, badges, separators, skeletons, and toasts

Use Prompt Kit for AI-interface primitives that map directly to the onboarding
experience:

- chat container
- message rendering
- prompt input
- prompt suggestions
- file upload placeholder
- source display
- reasoning or workflow trace display

Prompt Kit components should be added through the shadcn CLI registry flow. For
the Chain of Thought component, use:

```bash
npx shadcn@latest add "https://prompt-kit.com/c/chain-of-thought.json"
```

The Chain of Thought component should not expose raw hidden model reasoning.
Use it for professor-facing workflow transparency, such as:

- "Collected source permissions"
- "Detected unresolved academic-integrity warning"
- "Generated draft tutor policy"
- "Prepared preview comparison"
- "Approval blocked until source permissions are confirmed"

This gives reviewers an understandable audit trail without displaying private
model reasoning tokens.

## LangGraph role

LangGraph v1 should model the onboarding workflow as a state graph:

```text
course_setup
-> source_permissions
-> teaching_approach
-> academic_integrity
-> misconception_handling
-> generated_policy
-> preview_comparison
-> professor_approval
```

For Sprint 1, graph nodes can be deterministic and fixture-backed. The graph
still provides a clean place to add LLM calls, persistence, interruption, and
human-in-the-loop review later.

The graph state should include:

- session id
- current step
- chat transcript
- source-permission answers
- extracted tutor policy draft
- release blockers
- warnings
- preview examples
- approval checklist state

## LLM portability

Application code should not call a provider SDK directly. All model calls should
go through a local adapter interface such as:

```python
class LlmClient:
    async def chat(self, messages: list[dict[str, str]], task: str) -> str:
        ...
```

The first implementation can return deterministic fixture output. A later
implementation can call LiteLLM and route to OpenAI, Anthropic, Gemini, local
OpenAI-compatible endpoints, or another provider through configuration.

This keeps LangGraph responsible for workflow state and LiteLLM responsible for
provider portability.

## Sprint 1 scope

In scope:

- Scaffold a React/Vite frontend.
- Scaffold a FastAPI backend.
- Define Python tutor-policy models.
- Create a LangGraph onboarding workflow.
- Use deterministic prototype responses for professor review.
- Render the chat-led setup sequence, generated policy, preview comparison, and
  approval checklist.
- Keep sensitive data out of fixtures.

Out of scope:

- Production authentication.
- Real course-material ingestion.
- Vector storage.
- RAG.
- Database persistence.
- Real student chatbot.
- Analytics dashboard.
- Live professor or student data.

## Error handling

Sprint 1 error handling should be simple and visible:

- Backend validation errors should return structured JSON with a stable error
  code and human-readable message.
- The frontend should show recoverable inline errors without losing the current
  transcript.
- If model output is unavailable, the workflow should fall back to deterministic
  fixture output.
- Approval should remain blocked when source permissions, privacy decisions, or
  professor release approval are unresolved.

## Testing

Initial tests should focus on the Python domain and workflow boundary:

- Policy model validation.
- Release blocker calculation.
- Follow-up behavior for vague instructor answers.
- LangGraph step transitions.
- API smoke tests for session creation, chat progression, preview, and approval.

Frontend tests can wait until the UI stabilizes unless a helper contains
non-trivial policy logic.

## References

- FastAPI documentation: https://fastapi.tiangolo.com/
- LangGraph v1 documentation: https://docs.langchain.com/oss/python/releases/langgraph-v1
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- LiteLLM documentation: https://docs.litellm.ai/docs/
- Digital Twin Consortium Capabilities Periodic Table:
  https://www.digitaltwinconsortium.org/initiatives/capabilities-periodic-table/
