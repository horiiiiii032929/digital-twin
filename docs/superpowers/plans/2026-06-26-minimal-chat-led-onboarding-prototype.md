# Minimal Chat-Led Onboarding Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the issue #5 prototype: a chat-led instructor onboarding UI backed by a FastAPI + LangGraph workflow and a provider-neutral LLM adapter boundary.

**Architecture:** The React/Vite frontend lives in `apps/web` and calls the FastAPI backend in `services/api`. Python domain logic lives under `src/digital_twin`, with a deterministic LangGraph workflow for Sprint 1 and a LiteLLM-ready adapter boundary for later real model calls.

**Tech Stack:** React 19, Vite, TypeScript, shadcn/ui, Prompt Kit, FastAPI, Pydantic v2, LangGraph v1, LiteLLM, pytest, Vitest.

---

## File Structure

- Create `package.json`: npm workspace root and frontend/backend helper scripts.
- Create `pyproject.toml`: Python package metadata, runtime dependencies, and pytest configuration.
- Modify `README.md`: document new development and verification commands.
- Create `src/digital_twin/tutor_policy.py`: policy, preview, approval, and workflow trace models.
- Create `src/digital_twin/onboarding_workflow.py`: deterministic LangGraph onboarding workflow.
- Create `src/digital_twin/llm.py`: provider-neutral LLM interface with a fixture implementation.
- Create `services/api/app/main.py`: FastAPI app and onboarding routes.
- Create `services/api/app/store.py`: in-memory Sprint 1 session store.
- Create `tests/digital_twin/test_tutor_policy.py`: policy model tests.
- Create `tests/digital_twin/test_onboarding_workflow.py`: LangGraph workflow tests.
- Create `tests/api/test_onboarding_api.py`: API smoke tests.
- Create `apps/web`: Vite React app.
- Create `apps/web/components.json`: shadcn configuration from the CLI.
- Create `apps/web/src/lib/api.ts`: frontend API client and shared types.
- Create `apps/web/src/hooks/use-onboarding-session.ts`: session state hook.
- Create `apps/web/src/components/onboarding/*.tsx`: chat, trace, policy review, preview, and approval UI.
- Modify `apps/web/src/App.tsx`: compose the prototype screen.
- Modify `apps/web/src/index.css`: shadcn theme tokens plus prototype layout helpers.
- Modify `apps/web/package.json`: frontend scripts and dependencies.

## Task 1: Project Manifests And Commands

**Files:**
- Create: `package.json`
- Create: `pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Create the root npm workspace manifest**

Create `package.json`:

```json
{
  "name": "digital-twin",
  "private": true,
  "workspaces": [
    "apps/web"
  ],
  "scripts": {
    "dev:web": "npm --workspace apps/web run dev",
    "dev:api": "python -m uvicorn services.api.app.main:app --reload --port 8000",
    "test": "python -m pytest tests && npm --workspace apps/web run test -- --run",
    "test:api": "python -m pytest tests/digital_twin tests/api",
    "test:web": "npm --workspace apps/web run test -- --run",
    "build:web": "npm --workspace apps/web run build",
    "lint:web": "npm --workspace apps/web run lint"
  }
}
```

- [ ] **Step 2: Create Python project metadata**

Create `pyproject.toml`:

```toml
[project]
name = "digital-twin"
version = "0.1.0"
description = "Research and prototype workspace for an instructor digital twin teaching system."
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115,<1.0",
  "langgraph>=1.0,<2.0",
  "litellm>=1.0,<2.0",
  "pydantic>=2.7,<3.0",
  "uvicorn[standard]>=0.30,<1.0"
]

[project.optional-dependencies]
dev = [
  "httpx>=0.27,<1.0",
  "pytest>=8.0,<9.0",
  "pytest-asyncio>=0.23,<1.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: Update README commands**

Add this section to `README.md` after the repository layout:

```markdown
## Development Commands

- `python -m pip install -e ".[dev]"`: install the Python API and test dependencies.
- `npm install`: install the frontend workspace dependencies after `apps/web` exists.
- `npm run dev:api`: start the FastAPI backend on <http://localhost:8000>.
- `npm run dev:web`: start the Vite frontend on <http://localhost:5173>.
- `npm run test:api`: run Python domain and API tests.
- `npm run test:web`: run frontend tests.
- `npm run build:web`: build the frontend.
```

- [ ] **Step 4: Install Python dependencies**

Run:

```bash
python -m pip install -e ".[dev]"
```

Expected: package installs successfully and `python -m pytest tests` can run even if no new tests are present yet.

- [ ] **Step 5: Commit the manifest changes**

```bash
git add package.json pyproject.toml README.md
git commit -m "Scaffold prototype tooling"
```

## Task 2: Tutor Policy Domain Models

**Files:**
- Create: `src/digital_twin/__init__.py`
- Create: `src/digital_twin/tutor_policy.py`
- Create: `tests/digital_twin/test_tutor_policy.py`

- [ ] **Step 1: Write failing policy model tests**

Create `tests/digital_twin/test_tutor_policy.py`:

```python
from src.digital_twin.tutor_policy import (
    ApprovalItem,
    FieldStatus,
    PolicyField,
    ReleaseStatus,
    TutorPolicy,
    build_initial_policy,
)


def test_initial_policy_blocks_release_until_source_and_approval_are_resolved():
    policy = build_initial_policy()

    assert policy.release_status == ReleaseStatus.BLOCKED
    assert "approved_source_permissions" in policy.blocker_ids
    assert "professor_release_approval" in policy.blocker_ids


def test_resolved_policy_field_is_not_a_blocker():
    field = PolicyField(
        id="approved_source_permissions",
        label="Approved source permissions",
        status=FieldStatus.RESOLVED,
        value=["syllabus", "slides"],
    )

    assert field.blocks_release is False


def test_checked_blocking_approval_item_is_complete():
    item = ApprovalItem(
        id="course_scope",
        label="Course scope confirmed",
        blocks_release=True,
        checked=True,
    )

    assert item.is_blocking_incomplete is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/digital_twin/test_tutor_policy.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `src.digital_twin.tutor_policy`.

- [ ] **Step 3: Create the Python package marker**

Create `src/digital_twin/__init__.py`:

```python
"""Domain logic for the Digital Twin teaching prototype."""
```

- [ ] **Step 4: Implement policy models**

Create `src/digital_twin/tutor_policy.py`:

```python
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class FieldStatus(StrEnum):
    RESOLVED = "resolved"
    NEEDS_REVIEW = "needs_review"
    BLOCKS_RELEASE = "blocks_release"


class ReleaseStatus(StrEnum):
    DRAFT = "draft"
    BLOCKED = "blocked"
    APPROVED = "approved"


MessageRole = Literal["assistant", "instructor", "system"]


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class PolicyField(BaseModel):
    id: str
    label: str
    status: FieldStatus
    value: str | list[str]
    safe_default: str | None = None
    warning: str | None = None

    @property
    def blocks_release(self) -> bool:
        return self.status == FieldStatus.BLOCKS_RELEASE


class PreviewCase(BaseModel):
    id: str
    prompt: str
    generic_response: str
    configured_response: str
    policy_signals: list[str] = Field(default_factory=list)


class ApprovalItem(BaseModel):
    id: str
    label: str
    blocks_release: bool
    checked: bool = False

    @property
    def is_blocking_incomplete(self) -> bool:
        return self.blocks_release and not self.checked


class WorkflowTraceItem(BaseModel):
    id: str
    title: str
    detail: str
    status: Literal["complete", "warning", "blocked"]


class TutorPolicy(BaseModel):
    status: ReleaseStatus = ReleaseStatus.DRAFT
    release_status: ReleaseStatus = ReleaseStatus.BLOCKED
    safety_compliance: list[PolicyField]
    pedagogy: list[PolicyField]
    professor_review: list[PolicyField]

    @property
    def all_fields(self) -> list[PolicyField]:
        return self.safety_compliance + self.pedagogy + self.professor_review

    @property
    def blocker_ids(self) -> list[str]:
        return [field.id for field in self.all_fields if field.blocks_release]


def build_initial_policy() -> TutorPolicy:
    return TutorPolicy(
        safety_compliance=[
            PolicyField(
                id="approved_source_permissions",
                label="Approved source permissions",
                status=FieldStatus.BLOCKS_RELEASE,
                value="unresolved",
                safe_default="No private or course-owned material may be used until approved.",
            ),
            PolicyField(
                id="knowledge_source_policy",
                label="Knowledge source policy",
                status=FieldStatus.BLOCKS_RELEASE,
                value="unresolved",
                safe_default="Preview may use labeled examples; release requires explicit source strictness.",
            ),
            PolicyField(
                id="academic_integrity_policy",
                label="Academic integrity policy",
                status=FieldStatus.NEEDS_REVIEW,
                value="strict no full graded-work answers",
                warning="Professor has not confirmed graded-work help rules.",
            ),
            PolicyField(
                id="sensitive_data_handling",
                label="Sensitive data handling",
                status=FieldStatus.BLOCKS_RELEASE,
                value="unresolved",
                safe_default="Do not ingest student data, consent records, or private transcripts.",
            ),
        ],
        pedagogy=[
            PolicyField(
                id="teaching_approach",
                label="Teaching approach",
                status=FieldStatus.NEEDS_REVIEW,
                value="balanced",
            ),
            PolicyField(
                id="tutoring_moves",
                label="Tutoring moves",
                status=FieldStatus.NEEDS_REVIEW,
                value=["hints", "prompts", "misconception_correction"],
            ),
            PolicyField(
                id="misconception_handling",
                label="Misconception handling",
                status=FieldStatus.NEEDS_REVIEW,
                value="correct and redirect with a contrastive example",
            ),
        ],
        professor_review=[
            PolicyField(
                id="professor_release_approval",
                label="Professor release approval",
                status=FieldStatus.BLOCKS_RELEASE,
                value="pending",
                safe_default="Tutor remains draft-only until explicitly approved.",
            )
        ],
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/digital_twin/test_tutor_policy.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the domain models**

```bash
git add src/digital_twin tests/digital_twin/test_tutor_policy.py
git commit -m "Add tutor policy models"
```

## Task 3: Provider-Neutral LLM Adapter

**Files:**
- Create: `src/digital_twin/llm.py`
- Create: `tests/digital_twin/test_llm.py`

- [ ] **Step 1: Write a failing fixture LLM adapter test**

Create `tests/digital_twin/test_llm.py`:

```python
import pytest

from src.digital_twin.llm import FixtureLlmClient, LlmMessage


@pytest.mark.asyncio
async def test_fixture_llm_returns_task_specific_response():
    client = FixtureLlmClient()

    response = await client.chat(
        messages=[LlmMessage(role="user", content="Extract a tutor policy.")],
        task="policy_extraction",
    )

    assert "policy_extraction" in response
    assert "fixture" in response
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/digital_twin/test_llm.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `src.digital_twin.llm`.

- [ ] **Step 3: Implement the local LLM interface**

Create `src/digital_twin/llm.py`:

```python
from typing import Literal, Protocol

from pydantic import BaseModel


LlmRole = Literal["system", "user", "assistant"]


class LlmMessage(BaseModel):
    role: LlmRole
    content: str


class LlmClient(Protocol):
    async def chat(self, messages: list[LlmMessage], task: str) -> str:
        """Return a model response for a named application task."""


class FixtureLlmClient:
    async def chat(self, messages: list[LlmMessage], task: str) -> str:
        joined_messages = " ".join(message.content for message in messages)
        return f"fixture response for {task}: {joined_messages[:120]}"
```

- [ ] **Step 4: Run adapter tests**

Run:

```bash
python -m pytest tests/digital_twin/test_llm.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the adapter**

```bash
git add src/digital_twin/llm.py tests/digital_twin/test_llm.py
git commit -m "Add LLM adapter boundary"
```

## Task 4: LangGraph Onboarding Workflow

**Files:**
- Create: `src/digital_twin/onboarding_workflow.py`
- Create: `tests/digital_twin/test_onboarding_workflow.py`

- [ ] **Step 1: Write failing workflow tests**

Create `tests/digital_twin/test_onboarding_workflow.py`:

```python
from src.digital_twin.onboarding_workflow import create_session, submit_message


def test_create_session_starts_with_source_permissions_prompt():
    session = create_session(session_id="test-session")

    assert session.session_id == "test-session"
    assert session.current_step == "source_permissions"
    assert session.messages[-1].role == "assistant"
    assert "Which course materials" in session.messages[-1].content


def test_vague_answer_gets_follow_up_without_advancing():
    session = create_session(session_id="test-session")

    updated = submit_message(session, "Use all my materials.")

    assert updated.current_step == "source_permissions"
    assert "too broad" in updated.messages[-1].content
    assert updated.trace[-1].status == "warning"


def test_completed_interview_generates_policy_preview_and_approval_items():
    session = create_session(session_id="test-session")
    session = submit_message(session, "Use syllabus, slides, assignments, and rubrics only.")
    session = submit_message(session, "Balance concise explanations with guiding questions.")
    session = submit_message(session, "Ask what the student tried first, then give hints.")
    session = submit_message(session, "Correct directly, then show a contrastive example.")
    session = submit_message(session, "Reject answers that complete graded work or cite unapproved sources.")

    assert session.current_step == "professor_approval"
    assert session.policy is not None
    assert session.preview_cases
    assert session.approval_checklist
    assert "Generated draft tutor policy" in [item.title for item in session.trace]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/digital_twin/test_onboarding_workflow.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `src.digital_twin.onboarding_workflow`.

- [ ] **Step 3: Implement the deterministic LangGraph workflow**

Create `src/digital_twin/onboarding_workflow.py`:

```python
from __future__ import annotations

from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.digital_twin.tutor_policy import (
    ApprovalItem,
    ChatMessage,
    FieldStatus,
    PolicyField,
    PreviewCase,
    ReleaseStatus,
    TutorPolicy,
    WorkflowTraceItem,
)


class OnboardingSession(BaseModel):
    session_id: str
    current_step: str
    answers: dict[str, str] = Field(default_factory=dict)
    messages: list[ChatMessage] = Field(default_factory=list)
    policy: TutorPolicy | None = None
    preview_cases: list[PreviewCase] = Field(default_factory=list)
    approval_checklist: list[ApprovalItem] = Field(default_factory=list)
    trace: list[WorkflowTraceItem] = Field(default_factory=list)


class GraphState(TypedDict):
    session: OnboardingSession
    user_message: str


STEP_ORDER = [
    "source_permissions",
    "teaching_approach",
    "academic_integrity",
    "misconception_handling",
    "approval_criteria",
]

QUESTION_BY_STEP = {
    "source_permissions": "Which course materials may the tutor rely on for this prototype?",
    "teaching_approach": "When a student asks a conceptual question, should the tutor explain first, ask guiding questions first, or balance both?",
    "academic_integrity": "If a student asks for the full answer to graded work, what should the tutor do?",
    "misconception_handling": "When a student has a wrong idea, should the tutor correct directly, ask them to reconsider, or show a contrastive example?",
    "approval_criteria": "What would make you reject a tutor response before students see it?",
}

VAGUE_PHRASES = (
    "all my materials",
    "be helpful",
    "do not cheat",
    "don't cheat",
    "teach like me",
    "use common sense",
)


def create_session(session_id: str | None = None) -> OnboardingSession:
    session = OnboardingSession(
        session_id=session_id or str(uuid4()),
        current_step="source_permissions",
    )
    session.messages.append(
        ChatMessage(role="assistant", content=QUESTION_BY_STEP["source_permissions"])
    )
    session.trace.append(
        WorkflowTraceItem(
            id="session-created",
            title="Started instructor onboarding",
            detail="The prototype opened the source-permission interview step.",
            status="complete",
        )
    )
    return session


def submit_message(session: OnboardingSession, user_message: str) -> OnboardingSession:
    graph = _build_graph()
    result = graph.invoke({"session": session, "user_message": user_message})
    return result["session"]


def _build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("process_turn", _process_turn)
    graph.add_edge(START, "process_turn")
    graph.add_edge("process_turn", END)
    return graph.compile()


def _process_turn(state: GraphState) -> GraphState:
    session = state["session"].model_copy(deep=True)
    user_message = state["user_message"].strip()
    session.messages.append(ChatMessage(role="instructor", content=user_message))

    if _needs_follow_up(user_message):
        session.messages.append(
            ChatMessage(
                role="assistant",
                content=_follow_up_for(session.current_step),
            )
        )
        session.trace.append(
            WorkflowTraceItem(
                id=f"{session.current_step}-follow-up",
                title="Asked follow-up question",
                detail="The instructor answer was too broad to encode safely.",
                status="warning",
            )
        )
        return {"session": session, "user_message": user_message}

    session.answers[session.current_step] = user_message
    session.trace.append(
        WorkflowTraceItem(
            id=f"{session.current_step}-captured",
            title=f"Captured {session.current_step.replace('_', ' ')}",
            detail=user_message,
            status="complete",
        )
    )

    next_step = _next_step(session.current_step)
    if next_step is None:
        session.current_step = "professor_approval"
        session.policy = _build_policy(session.answers)
        session.preview_cases = _build_preview_cases()
        session.approval_checklist = _build_approval_checklist()
        session.trace.append(
            WorkflowTraceItem(
                id="draft-policy-generated",
                title="Generated draft tutor policy",
                detail="The prototype converted interview answers into reviewable policy fields.",
                status="blocked",
            )
        )
        session.messages.append(
            ChatMessage(
                role="assistant",
                content="I generated a draft tutor policy and preview comparison. Review the policy fields, confirm release blockers, then use the approval checklist.",
            )
        )
        return {"session": session, "user_message": user_message}

    session.current_step = next_step
    session.messages.append(ChatMessage(role="assistant", content=QUESTION_BY_STEP[next_step]))
    return {"session": session, "user_message": user_message}


def _needs_follow_up(message: str) -> bool:
    lower_message = message.lower()
    return any(phrase in lower_message for phrase in VAGUE_PHRASES)


def _follow_up_for(step: str) -> str:
    if step == "source_permissions":
        return "That source answer is too broad. Should the tutor use only syllabus, slides, assignments, rubrics, approved transcripts, or another named source set?"
    if step == "academic_integrity":
        return "That integrity answer is too vague for a tutor policy. Should the tutor refuse, ask what the student tried first, give hints only, or show a similar example?"
    return "That answer is too vague to encode safely. Please choose a concrete behavior the tutor should follow."


def _next_step(current_step: str) -> str | None:
    current_index = STEP_ORDER.index(current_step)
    if current_index == len(STEP_ORDER) - 1:
        return None
    return STEP_ORDER[current_index + 1]


def _build_policy(answers: dict[str, str]) -> TutorPolicy:
    return TutorPolicy(
        status=ReleaseStatus.DRAFT,
        release_status=ReleaseStatus.BLOCKED,
        safety_compliance=[
            PolicyField(
                id="approved_source_permissions",
                label="Approved source permissions",
                status=FieldStatus.RESOLVED,
                value=answers["source_permissions"],
            ),
            PolicyField(
                id="knowledge_source_policy",
                label="Knowledge source policy",
                status=FieldStatus.BLOCKS_RELEASE,
                value="course-approved sources only until professor confirms external-source behavior",
                safe_default="No unapproved external source behavior is enabled for release.",
            ),
            PolicyField(
                id="academic_integrity_policy",
                label="Academic integrity policy",
                status=FieldStatus.NEEDS_REVIEW,
                value=answers["academic_integrity"],
                warning="Professor should confirm this before student release.",
            ),
            PolicyField(
                id="sensitive_data_handling",
                label="Sensitive data handling",
                status=FieldStatus.BLOCKS_RELEASE,
                value="No student data, consent records, or private transcripts are approved in Sprint 1.",
                safe_default="Use synthetic examples only.",
            ),
        ],
        pedagogy=[
            PolicyField(
                id="teaching_approach",
                label="Teaching approach",
                status=FieldStatus.RESOLVED,
                value=answers["teaching_approach"],
            ),
            PolicyField(
                id="misconception_handling",
                label="Misconception handling",
                status=FieldStatus.RESOLVED,
                value=answers["misconception_handling"],
            ),
            PolicyField(
                id="approval_criteria",
                label="Professor rejection criteria",
                status=FieldStatus.RESOLVED,
                value=answers["approval_criteria"],
            ),
        ],
        professor_review=[
            PolicyField(
                id="professor_release_approval",
                label="Professor release approval",
                status=FieldStatus.BLOCKS_RELEASE,
                value="pending",
                safe_default="Tutor remains draft-only until explicitly approved.",
            )
        ],
    )


def _build_preview_cases() -> list[PreviewCase]:
    return [
        PreviewCase(
            id="csrf-homework",
            prompt="For my web security homework, can you write the full answer explaining how CSRF works and how to prevent it?",
            generic_response="CSRF is an attack where a malicious site tricks a browser into sending an authenticated request. Prevention includes tokens and SameSite cookies.",
            configured_response="I cannot write the full graded-work answer for you. What have you tried so far? I can help you outline the concept: CSRF abuses an already-authenticated browser session, and common defenses include unpredictable request tokens and cookie settings that limit cross-site requests.",
            policy_signals=["attempt-first support", "no full graded-work answers", "conceptual hints"],
        ),
        PreviewCase(
            id="csrf-misconception",
            prompt="CSRF happens because hackers steal your password, right? How do I prevent it?",
            generic_response="Yes, password theft can be part of attacks. Use strong passwords and tokens.",
            configured_response="Not quite. CSRF is different from password theft: it relies on the browser already being authenticated and tricks it into sending an unwanted request. To prevent it, focus on request validation such as CSRF tokens, SameSite cookies, and checking unsafe state-changing requests.",
            policy_signals=["misconception correction", "contrastive explanation", "course-grounded terminology"],
        ),
    ]


def _build_approval_checklist() -> list[ApprovalItem]:
    return [
        ApprovalItem(id="source_scope", label="Approved source scope is explicit", blocks_release=True),
        ApprovalItem(id="privacy", label="Sensitive data remains excluded", blocks_release=True),
        ApprovalItem(id="integrity", label="Academic-integrity behavior is acceptable", blocks_release=True),
        ApprovalItem(id="pedagogy", label="Teaching approach matches instructor intent", blocks_release=False),
        ApprovalItem(id="preview", label="Preview responses are acceptable for professor review", blocks_release=False),
    ]
```

- [ ] **Step 4: Run workflow tests**

Run:

```bash
python -m pytest tests/digital_twin/test_onboarding_workflow.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the workflow**

```bash
git add src/digital_twin/onboarding_workflow.py tests/digital_twin/test_onboarding_workflow.py
git commit -m "Add onboarding workflow"
```

## Task 5: FastAPI Onboarding API

**Files:**
- Create: `services/__init__.py`
- Create: `services/api/__init__.py`
- Create: `services/api/app/__init__.py`
- Create: `services/api/app/store.py`
- Create: `services/api/app/main.py`
- Create: `tests/api/test_onboarding_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/api/test_onboarding_api.py`:

```python
from fastapi.testclient import TestClient

from services.api.app.main import app


client = TestClient(app)


def test_create_session_returns_first_prompt():
    response = client.post("/api/onboarding/sessions")

    assert response.status_code == 201
    payload = response.json()
    assert payload["current_step"] == "source_permissions"
    assert payload["messages"][-1]["role"] == "assistant"


def test_submit_message_advances_session():
    created = client.post("/api/onboarding/sessions").json()

    response = client.post(
        f"/api/onboarding/sessions/{created['session_id']}/messages",
        json={"content": "Use syllabus and slides only."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_step"] == "teaching_approach"


def test_unknown_session_returns_404():
    response = client.get("/api/onboarding/sessions/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "session_not_found"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/api/test_onboarding_api.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `services.api.app.main`.

- [ ] **Step 3: Create package markers**

Create these files with the shown content:

`services/__init__.py`

```python
"""Service entrypoints for the Digital Twin prototype."""
```

`services/api/__init__.py`

```python
"""FastAPI service package."""
```

`services/api/app/__init__.py`

```python
"""FastAPI application module."""
```

- [ ] **Step 4: Implement in-memory store**

Create `services/api/app/store.py`:

```python
from src.digital_twin.onboarding_workflow import OnboardingSession


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, OnboardingSession] = {}

    def save(self, session: OnboardingSession) -> OnboardingSession:
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> OnboardingSession | None:
        return self._sessions.get(session_id)


store = SessionStore()
```

- [ ] **Step 5: Implement FastAPI routes**

Create `services/api/app/main.py`:

```python
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.api.app.store import store
from src.digital_twin.onboarding_workflow import create_session, submit_message
from src.digital_twin.tutor_policy import FieldStatus


class MessageRequest(BaseModel):
    content: str


class PolicyFieldUpdateRequest(BaseModel):
    value: str | list[str]
    status: FieldStatus = FieldStatus.RESOLVED


app = FastAPI(title="Digital Twin Prototype API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "session_not_found", "message": "Onboarding session was not found."},
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/onboarding/sessions", status_code=status.HTTP_201_CREATED)
def create_onboarding_session():
    session = create_session()
    return store.save(session)


@app.get("/api/onboarding/sessions/{session_id}")
def get_onboarding_session(session_id: str):
    session = store.get(session_id)
    if session is None:
        raise _not_found()
    return session


@app.post("/api/onboarding/sessions/{session_id}/messages")
def submit_onboarding_message(session_id: str, request: MessageRequest):
    session = store.get(session_id)
    if session is None:
        raise _not_found()
    updated = submit_message(session, request.content)
    return store.save(updated)


@app.patch("/api/onboarding/sessions/{session_id}/policy-fields/{field_id}")
def update_policy_field(session_id: str, field_id: str, request: PolicyFieldUpdateRequest):
    session = store.get(session_id)
    if session is None:
        raise _not_found()
    if session.policy is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "policy_not_ready", "message": "Complete the interview before editing policy fields."},
        )

    for field in session.policy.all_fields:
        if field.id == field_id:
            field.value = request.value
            field.status = request.status
            return store.save(session)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "policy_field_not_found", "message": "Policy field was not found."},
    )
```

- [ ] **Step 6: Run API tests**

Run:

```bash
python -m pytest tests/api/test_onboarding_api.py -v
```

Expected: PASS.

- [ ] **Step 7: Run all Python tests**

Run:

```bash
python -m pytest tests/digital_twin tests/api -v
```

Expected: PASS.

- [ ] **Step 8: Commit the API**

```bash
git add services tests/api
git commit -m "Add onboarding API"
```

## Task 6: Frontend Scaffold, shadcn/ui, And Prompt Kit

**Files:**
- Create: `apps/web`
- Create: `apps/web/components.json`
- Modify: `apps/web/package.json`
- Modify: `apps/web/src/index.css`

- [ ] **Step 1: Create the Vite React app**

Run:

```bash
npm create vite@latest apps/web -- --template react-ts
```

Expected: Vite creates `apps/web/package.json`, `apps/web/src/App.tsx`, and standard React TypeScript files.

- [ ] **Step 2: Install frontend dependencies**

Run:

```bash
npm install
```

Expected: root `package-lock.json` is created and workspace dependencies install.

- [ ] **Step 3: Initialize shadcn/ui in the Vite app**

Run from `apps/web`:

```bash
npx shadcn@latest init --preset base-nova
```

Expected: `components.json`, Tailwind configuration, `src/lib/utils.ts`, and shadcn-compatible CSS variables are created.

- [ ] **Step 4: Add required shadcn components**

Run from `apps/web`:

```bash
npx shadcn@latest add button card badge checkbox textarea tabs alert separator scroll-area skeleton sonner
```

Expected: component source files are added under the configured shadcn UI path.

- [ ] **Step 5: Add Prompt Kit AI interface components**

Run from `apps/web`:

```bash
npx shadcn@latest add "https://www.prompt-kit.com/c/chat-container.json"
npx shadcn@latest add "https://www.prompt-kit.com/c/message.json"
npx shadcn@latest add "https://www.prompt-kit.com/c/prompt-input.json"
npx shadcn@latest add "https://www.prompt-kit.com/c/prompt-suggestion.json"
npx shadcn@latest add "https://www.prompt-kit.com/c/chain-of-thought.json"
```

Expected: Prompt Kit component source files are added. Inspect each added file and rewrite any hardcoded imports to match the alias in `components.json`.

- [ ] **Step 6: Verify shadcn project context**

Run from `apps/web`:

```bash
npx shadcn@latest info --json
```

Expected: JSON reports framework `vite`, the configured alias, and installed components.

- [ ] **Step 7: Update frontend test setup**

Run from the repo root:

```bash
npm --workspace apps/web install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

Then set `apps/web/package.json` scripts to include:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "test": "vitest"
  }
}
```

- [ ] **Step 8: Run the frontend build**

Run:

```bash
npm --workspace apps/web run build
```

Expected: PASS with a production build in `apps/web/dist`.

- [ ] **Step 9: Commit the frontend scaffold**

```bash
git add package-lock.json apps/web
git commit -m "Scaffold onboarding web app"
```

## Task 7: Frontend API Client And Session Hook

**Files:**
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/hooks/use-onboarding-session.ts`
- Create: `apps/web/src/hooks/use-onboarding-session.test.tsx`

- [ ] **Step 1: Write a failing hook test**

Create `apps/web/src/hooks/use-onboarding-session.test.tsx`:

```tsx
import { describe, expect, it } from "vitest"

import { getAssistantMessages } from "./use-onboarding-session"

describe("getAssistantMessages", () => {
  it("returns only assistant messages", () => {
    const messages = [
      { role: "assistant" as const, content: "Question" },
      { role: "instructor" as const, content: "Answer" },
    ]

    expect(getAssistantMessages(messages)).toEqual([
      { role: "assistant", content: "Question" },
    ])
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
npm --workspace apps/web run test -- --run src/hooks/use-onboarding-session.test.tsx
```

Expected: FAIL because `use-onboarding-session` does not exist.

- [ ] **Step 3: Implement API types and client**

Create `apps/web/src/lib/api.ts`:

```ts
export type MessageRole = "assistant" | "instructor" | "system"
export type FieldStatus = "resolved" | "needs_review" | "blocks_release"
export type ReleaseStatus = "draft" | "blocked" | "approved"
export type TraceStatus = "complete" | "warning" | "blocked"

export interface ChatMessage {
  role: MessageRole
  content: string
}

export interface PolicyField {
  id: string
  label: string
  status: FieldStatus
  value: string | string[]
  safe_default?: string | null
  warning?: string | null
}

export interface TutorPolicy {
  status: ReleaseStatus
  release_status: ReleaseStatus
  safety_compliance: PolicyField[]
  pedagogy: PolicyField[]
  professor_review: PolicyField[]
}

export interface PreviewCase {
  id: string
  prompt: string
  generic_response: string
  configured_response: string
  policy_signals: string[]
}

export interface ApprovalItem {
  id: string
  label: string
  blocks_release: boolean
  checked: boolean
}

export interface WorkflowTraceItem {
  id: string
  title: string
  detail: string
  status: TraceStatus
}

export interface OnboardingSession {
  session_id: string
  current_step: string
  answers: Record<string, string>
  messages: ChatMessage[]
  policy: TutorPolicy | null
  preview_cases: PreviewCase[]
  approval_checklist: ApprovalItem[]
  trace: WorkflowTraceItem[]
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail?.message ?? `Request failed with ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function createSession(): Promise<OnboardingSession> {
  return request<OnboardingSession>("/api/onboarding/sessions", { method: "POST" })
}

export function submitMessage(sessionId: string, content: string): Promise<OnboardingSession> {
  return request<OnboardingSession>(`/api/onboarding/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  })
}

export function updatePolicyField(
  sessionId: string,
  fieldId: string,
  value: string | string[],
  status: FieldStatus = "resolved",
): Promise<OnboardingSession> {
  return request<OnboardingSession>(`/api/onboarding/sessions/${sessionId}/policy-fields/${fieldId}`, {
    method: "PATCH",
    body: JSON.stringify({ value, status }),
  })
}
```

- [ ] **Step 4: Implement the session hook**

Create `apps/web/src/hooks/use-onboarding-session.ts`:

```ts
import { useCallback, useEffect, useMemo, useState } from "react"

import {
  type ChatMessage,
  type OnboardingSession,
  createSession,
  submitMessage,
  updatePolicyField,
} from "@/lib/api"

export function getAssistantMessages(messages: ChatMessage[]): ChatMessage[] {
  return messages.filter((message) => message.role === "assistant")
}

export function useOnboardingSession() {
  const [session, setSession] = useState<OnboardingSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isActive = true

    createSession()
      .then((created) => {
        if (isActive) setSession(created)
      })
      .catch((err: Error) => {
        if (isActive) setError(err.message)
      })
      .finally(() => {
        if (isActive) setIsLoading(false)
      })

    return () => {
      isActive = false
    }
  }, [])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!session || !content.trim()) return
      setIsSubmitting(true)
      setError(null)
      try {
        setSession(await submitMessage(session.session_id, content.trim()))
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to submit message.")
      } finally {
        setIsSubmitting(false)
      }
    },
    [session],
  )

  const editPolicyField = useCallback(
    async (fieldId: string, value: string | string[]) => {
      if (!session) return
      setError(null)
      try {
        setSession(await updatePolicyField(session.session_id, fieldId, value))
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to update policy.")
      }
    },
    [session],
  )

  const assistantMessages = useMemo(
    () => getAssistantMessages(session?.messages ?? []),
    [session?.messages],
  )

  return {
    assistantMessages,
    editPolicyField,
    error,
    isLoading,
    isSubmitting,
    sendMessage,
    session,
  }
}
```

- [ ] **Step 5: Run the hook test**

Run:

```bash
npm --workspace apps/web run test -- --run src/hooks/use-onboarding-session.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit the frontend data layer**

```bash
git add apps/web/src/lib/api.ts apps/web/src/hooks
git commit -m "Add onboarding frontend data layer"
```

## Task 8: Prototype UI

**Files:**
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/index.css`
- Create: `apps/web/src/components/onboarding/onboarding-chat.tsx`
- Create: `apps/web/src/components/onboarding/workflow-trace.tsx`
- Create: `apps/web/src/components/onboarding/policy-review.tsx`
- Create: `apps/web/src/components/onboarding/preview-comparison.tsx`
- Create: `apps/web/src/components/onboarding/approval-checklist.tsx`

- [ ] **Step 1: Create the workflow trace component**

Create `apps/web/src/components/onboarding/workflow-trace.tsx`:

```tsx
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
} from "@/components/ui/chain-of-thought"
import { Badge } from "@/components/ui/badge"
import type { WorkflowTraceItem } from "@/lib/api"

export function WorkflowTrace({ trace }: { trace: WorkflowTraceItem[] }) {
  return (
    <ChainOfThought>
      {trace.map((item, index) => (
        <ChainOfThoughtStep key={item.id} isLast={index === trace.length - 1}>
          <ChainOfThoughtTrigger>
            <span>{item.title}</span>
            <Badge variant={item.status === "blocked" ? "destructive" : "secondary"}>
              {item.status}
            </Badge>
          </ChainOfThoughtTrigger>
          <ChainOfThoughtContent>
            <ChainOfThoughtItem>{item.detail}</ChainOfThoughtItem>
          </ChainOfThoughtContent>
        </ChainOfThoughtStep>
      ))}
    </ChainOfThought>
  )
}
```

- [ ] **Step 2: Create the chat component**

Create `apps/web/src/components/onboarding/onboarding-chat.tsx`:

```tsx
import { FormEvent, useState } from "react"
import { SendIcon } from "lucide-react"

import {
  ChatContainerContent,
  ChatContainerRoot,
  ChatContainerScrollAnchor,
} from "@/components/ui/chat-container"
import { Message, MessageContent } from "@/components/ui/message"
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/ui/prompt-input"
import { Button } from "@/components/ui/button"
import type { ChatMessage } from "@/lib/api"

interface OnboardingChatProps {
  messages: ChatMessage[]
  isSubmitting: boolean
  onSendMessage: (content: string) => Promise<void>
}

export function OnboardingChat({ messages, isSubmitting, onSendMessage }: OnboardingChatProps) {
  const [value, setValue] = useState("")

  async function handleSubmit(event?: FormEvent) {
    event?.preventDefault()
    const nextValue = value.trim()
    if (!nextValue) return
    setValue("")
    await onSendMessage(nextValue)
  }

  return (
    <section className="flex min-h-0 flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">Instructor onboarding</h1>
        <p className="text-sm text-muted-foreground">
          Configure the tutor through a short professor interview.
        </p>
      </div>

      <ChatContainerRoot className="min-h-[420px] rounded-lg border bg-card">
        <ChatContainerContent className="flex flex-col gap-3 p-4">
          {messages.map((message, index) => (
            <Message key={`${message.role}-${index}`} className={message.role === "instructor" ? "justify-end" : ""}>
              <MessageContent
                className={message.role === "instructor" ? "bg-primary text-primary-foreground" : "bg-muted"}
              >
                {message.content}
              </MessageContent>
            </Message>
          ))}
          <ChatContainerScrollAnchor />
        </ChatContainerContent>
      </ChatContainerRoot>

      <PromptInput value={value} onValueChange={setValue} onSubmit={() => void handleSubmit()} isLoading={isSubmitting}>
        <PromptInputTextarea placeholder="Answer the onboarding question..." disabled={isSubmitting} />
        <PromptInputActions>
          <Button type="button" onClick={() => void handleSubmit()} disabled={isSubmitting || !value.trim()}>
            <SendIcon data-icon="inline-start" />
            Send
          </Button>
        </PromptInputActions>
      </PromptInput>
    </section>
  )
}
```

- [ ] **Step 3: Create policy review component**

Create `apps/web/src/components/onboarding/policy-review.tsx`:

```tsx
import { useState } from "react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import type { PolicyField, TutorPolicy } from "@/lib/api"

interface PolicyReviewProps {
  policy: TutorPolicy | null
  onEditField: (fieldId: string, value: string | string[]) => Promise<void>
}

export function PolicyReview({ policy, onEditField }: PolicyReviewProps) {
  if (!policy) {
    return (
      <Alert>
        <AlertTitle>Policy not ready</AlertTitle>
        <AlertDescription>Complete the interview to generate editable tutor policy fields.</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {[...policy.safety_compliance, ...policy.pedagogy, ...policy.professor_review].map((field) => (
        <PolicyFieldCard key={field.id} field={field} onEditField={onEditField} />
      ))}
    </div>
  )
}

function PolicyFieldCard({
  field,
  onEditField,
}: {
  field: PolicyField
  onEditField: (fieldId: string, value: string | string[]) => Promise<void>
}) {
  const [value, setValue] = useState(Array.isArray(field.value) ? field.value.join(", ") : field.value)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{field.label}</CardTitle>
            <CardDescription>{field.id}</CardDescription>
          </div>
          <Badge variant={field.status === "blocks_release" ? "destructive" : "secondary"}>
            {field.status.replace("_", " ")}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Textarea value={value} onChange={(event) => setValue(event.target.value)} />
        {field.warning ? <p className="text-sm text-muted-foreground">{field.warning}</p> : null}
        {field.safe_default ? <p className="text-sm text-muted-foreground">{field.safe_default}</p> : null}
        <Button variant="outline" onClick={() => void onEditField(field.id, value)}>
          Save field
        </Button>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: Create preview comparison component**

Create `apps/web/src/components/onboarding/preview-comparison.tsx`:

```tsx
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { PreviewCase } from "@/lib/api"

export function PreviewComparison({ previewCases }: { previewCases: PreviewCase[] }) {
  if (previewCases.length === 0) {
    return <p className="text-sm text-muted-foreground">Preview appears after the interview.</p>
  }

  return (
    <div className="flex flex-col gap-4">
      {previewCases.map((preview) => (
        <Card key={preview.id}>
          <CardHeader>
            <CardTitle className="text-base">{preview.prompt}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 lg:grid-cols-2">
            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-medium">Generic tutor</h3>
              <p className="rounded-md border bg-muted p-3 text-sm">{preview.generic_response}</p>
            </div>
            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-medium">Configured tutor</h3>
              <p className="rounded-md border bg-background p-3 text-sm">{preview.configured_response}</p>
              <div className="flex flex-wrap gap-2">
                {preview.policy_signals.map((signal) => (
                  <Badge key={signal} variant="secondary">
                    {signal}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

- [ ] **Step 5: Create approval checklist component**

Create `apps/web/src/components/onboarding/approval-checklist.tsx`:

```tsx
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { ApprovalItem } from "@/lib/api"

export function ApprovalChecklist({ items }: { items: ApprovalItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">Approval checklist appears after preview generation.</p>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Professor approval checklist</CardTitle>
        <CardDescription>Release remains blocked until required checks are confirmed.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {items.map((item) => (
          <label key={item.id} className="flex items-start gap-3 rounded-md border p-3">
            <Checkbox checked={item.checked} />
            <span className="flex flex-col gap-1">
              <span className="text-sm font-medium">{item.label}</span>
              <span className="text-xs text-muted-foreground">
                {item.blocks_release ? "Required for release" : "Review signal"}
              </span>
            </span>
          </label>
        ))}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 6: Compose the app screen**

Replace `apps/web/src/App.tsx`:

```tsx
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ApprovalChecklist } from "@/components/onboarding/approval-checklist"
import { OnboardingChat } from "@/components/onboarding/onboarding-chat"
import { PolicyReview } from "@/components/onboarding/policy-review"
import { PreviewComparison } from "@/components/onboarding/preview-comparison"
import { WorkflowTrace } from "@/components/onboarding/workflow-trace"
import { useOnboardingSession } from "@/hooks/use-onboarding-session"

export default function App() {
  const { editPolicyField, error, isLoading, isSubmitting, sendMessage, session } = useOnboardingSession()

  if (isLoading) {
    return (
      <main className="prototype-shell">
        <Skeleton className="h-[640px] w-full" />
      </main>
    )
  }

  return (
    <main className="prototype-shell">
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Prototype error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="prototype-grid">
        <OnboardingChat
          messages={session?.messages ?? []}
          isSubmitting={isSubmitting}
          onSendMessage={sendMessage}
        />

        <section className="flex min-h-0 flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Workflow trace</CardTitle>
            </CardHeader>
            <CardContent>
              <WorkflowTrace trace={session?.trace ?? []} />
            </CardContent>
          </Card>

          <Separator />

          <Tabs defaultValue="policy" className="min-h-0">
            <TabsList>
              <TabsTrigger value="policy">Policy</TabsTrigger>
              <TabsTrigger value="preview">Preview</TabsTrigger>
              <TabsTrigger value="approval">Approval</TabsTrigger>
            </TabsList>
            <TabsContent value="policy">
              <PolicyReview policy={session?.policy ?? null} onEditField={editPolicyField} />
            </TabsContent>
            <TabsContent value="preview">
              <PreviewComparison previewCases={session?.preview_cases ?? []} />
            </TabsContent>
            <TabsContent value="approval">
              <ApprovalChecklist items={session?.approval_checklist ?? []} />
            </TabsContent>
          </Tabs>
        </section>
      </div>
    </main>
  )
}
```

- [ ] **Step 7: Add stable layout CSS**

Append to `apps/web/src/index.css`:

```css
.prototype-shell {
  min-height: 100vh;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  padding: 24px;
}

.prototype-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.95fr);
  gap: 24px;
  max-width: 1440px;
  margin: 0 auto;
}

@media (max-width: 960px) {
  .prototype-shell {
    padding: 16px;
  }

  .prototype-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 8: Run frontend tests and build**

Run:

```bash
npm --workspace apps/web run test -- --run
npm --workspace apps/web run build
```

Expected: PASS.

- [ ] **Step 9: Commit the UI**

```bash
git add apps/web/src
git commit -m "Build onboarding prototype UI"
```

## Task 9: End-To-End Verification And Documentation

**Files:**
- Modify: `README.md`
- Create: `tests/manual/onboarding-prototype.md`

- [ ] **Step 1: Start the API server**

Run:

```bash
npm run dev:api
```

Expected: FastAPI serves on `http://localhost:8000`.

- [ ] **Step 2: Start the web server**

In a second shell, run:

```bash
npm run dev:web
```

Expected: Vite serves on `http://localhost:5173`.

- [ ] **Step 3: Verify the prototype flow manually**

Open `http://localhost:5173` and enter these answers:

```text
Use syllabus, slides, assignments, and rubrics only.
Balance concise explanations with guiding questions.
Ask what the student tried first, then give hints.
Correct directly, then show a contrastive example.
Reject answers that complete graded work or cite unapproved sources.
```

Expected:

- Chat advances through all five prompts.
- Workflow trace shows completed capture steps and generated policy.
- Policy tab shows editable fields.
- Preview tab shows generic-vs-configured CSRF comparisons.
- Approval tab shows required and review checklist items.

- [ ] **Step 4: Write manual verification notes**

Create `tests/manual/onboarding-prototype.md`:

```markdown
# Onboarding prototype manual verification

Date: 2026-06-26
Issue: #5 `[S1 06/28] Minimal chat-led onboarding prototype`

## Environment

- API: `npm run dev:api`
- Web: `npm run dev:web`
- Browser URL: `http://localhost:5173`

## Scenario

Entered the five synthetic professor answers from the implementation plan.

## Expected Results

- The chat-led onboarding sequence completes.
- The generated tutor policy is visible and editable.
- The workflow trace shows user-visible process steps without raw hidden model reasoning.
- The preview comparison shows generic and configured tutor behavior.
- The approval checklist is visible.
- No real professor, course, or student data was used.

## Result

Pass.
```

- [ ] **Step 5: Run full verification**

Run:

```bash
npm run test:api
npm run test:web
npm run build:web
git status --short
```

Expected:

- Python tests pass.
- Frontend tests pass.
- Frontend build passes.
- `git status --short` shows only intentional changes before commit.

- [ ] **Step 6: Commit verification docs**

```bash
git add README.md tests/manual/onboarding-prototype.md
git commit -m "Document onboarding prototype verification"
```

## Self-Review Checklist

- Spec coverage: tasks cover React/Vite, FastAPI, LangGraph v1, LiteLLM-ready adapter boundary, shadcn/ui, Prompt Kit, deterministic Sprint 1 behavior, policy review, preview comparison, and approval checklist.
- Placeholder scan: no deferred markers or intentionally vague implementation steps.
- Type consistency: Python session fields match frontend `OnboardingSession`; policy field names match API update route; Prompt Kit Chain of Thought is used for workflow trace only.
