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
    "source_permissions": (
        "Which course materials may the tutor rely on for this prototype?"
    ),
    "teaching_approach": (
        "When a student asks a conceptual question, should the tutor explain first, "
        "ask guiding questions first, or balance both?"
    ),
    "academic_integrity": (
        "If a student asks for the full answer to graded work, "
        "what should the tutor do?"
    ),
    "misconception_handling": (
        "When a student has a wrong idea, should the tutor correct directly, "
        "ask them to reconsider, or show a contrastive example?"
    ),
    "approval_criteria": (
        "What would make you reject a tutor response before students see it?"
    ),
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
                detail=(
                    "The prototype converted interview answers into reviewable "
                    "policy fields."
                ),
                status="blocked",
            )
        )
        session.messages.append(
            ChatMessage(
                role="assistant",
                content=(
                    "I generated a draft tutor policy and preview comparison. "
                    "Review the policy fields, confirm release blockers, then "
                    "use the approval checklist."
                ),
            )
        )
        return {"session": session, "user_message": user_message}

    session.current_step = next_step
    session.messages.append(
        ChatMessage(role="assistant", content=QUESTION_BY_STEP[next_step])
    )
    return {"session": session, "user_message": user_message}


def _needs_follow_up(message: str) -> bool:
    lower_message = message.lower()
    return any(phrase in lower_message for phrase in VAGUE_PHRASES)


def _follow_up_for(step: str) -> str:
    if step == "source_permissions":
        return (
            "That source answer is too broad. Should the tutor use only syllabus, "
            "slides, assignments, rubrics, approved transcripts, or another named "
            "source set?"
        )
    if step == "academic_integrity":
        return (
            "That integrity answer is too vague for a tutor policy. Should the tutor "
            "refuse, ask what the student tried first, give hints only, or show a "
            "similar example?"
        )
    return (
        "That answer is too vague to encode safely. Please choose a concrete behavior "
        "the tutor should follow."
    )


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
                value=(
                    "course-approved sources only until professor confirms "
                    "external-source behavior"
                ),
                safe_default=(
                    "No unapproved external source behavior is enabled for release."
                ),
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
                value=(
                    "No student data, consent records, or private transcripts are "
                    "approved in Sprint 1."
                ),
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
            prompt=(
                "For my web security homework, can you write the full answer "
                "explaining how CSRF works and how to prevent it?"
            ),
            generic_response=(
                "CSRF is an attack where a malicious site tricks a browser into "
                "sending an authenticated request. Prevention includes tokens and "
                "SameSite cookies."
            ),
            configured_response=(
                "I cannot write the full graded-work answer for you. What have you "
                "tried so far? I can help you outline the concept: CSRF abuses an "
                "already-authenticated browser session, and common defenses include "
                "unpredictable request tokens and cookie settings that limit "
                "cross-site requests."
            ),
            policy_signals=[
                "attempt-first support",
                "no full graded-work answers",
                "conceptual hints",
            ],
        ),
        PreviewCase(
            id="csrf-misconception",
            prompt=(
                "CSRF happens because hackers steal your password, right? How do I "
                "prevent it?"
            ),
            generic_response=(
                "Yes, password theft can be part of attacks. Use strong passwords "
                "and tokens."
            ),
            configured_response=(
                "Not quite. CSRF is different from password theft: it relies on the "
                "browser already being authenticated and tricks it into sending an "
                "unwanted request. To prevent it, focus on request validation such as "
                "CSRF tokens, SameSite cookies, and checking unsafe state-changing "
                "requests."
            ),
            policy_signals=[
                "misconception correction",
                "contrastive explanation",
                "course-grounded terminology",
            ],
        ),
    ]


def _build_approval_checklist() -> list[ApprovalItem]:
    return [
        ApprovalItem(
            id="source_scope",
            label="Approved source scope is explicit",
            blocks_release=True,
        ),
        ApprovalItem(
            id="privacy",
            label="Sensitive data remains excluded",
            blocks_release=True,
        ),
        ApprovalItem(
            id="integrity",
            label="Academic-integrity behavior is acceptable",
            blocks_release=True,
        ),
        ApprovalItem(
            id="pedagogy",
            label="Teaching approach matches instructor intent",
            blocks_release=False,
        ),
        ApprovalItem(
            id="preview",
            label="Preview responses are acceptable for professor review",
            blocks_release=False,
        ),
    ]
