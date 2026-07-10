from functools import lru_cache
from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from src.digital_twin.onboarding.interview import (
    QUESTION_BY_STEP,
    _empty_answer_follow_up,
    _follow_up_for,
    _needs_follow_up,
    _next_step,
)
from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.onboarding.policy import _build_policy
from src.digital_twin.onboarding.preview import (
    _build_approval_checklist,
    _build_preview_cases,
    _decision_record_for,
    _snapshot_for,
)
from src.digital_twin.onboarding.release import _recompute_release_state
from src.digital_twin.onboarding.revisions import (
    _is_confirmation_message,
    _is_discard_message,
    _proposal_from_feedback,
    confirm_revision_proposal,
    discard_revision_proposal,
)
from src.digital_twin.tutor_policy import ChatMessage, WorkflowTraceItem


class GraphState(TypedDict):
    session: OnboardingSession
    user_message: str


def create_session(session_id: str | None = None) -> OnboardingSession:
    session = OnboardingSession(
        session_id=session_id or str(uuid4()),
        current_step="source_permissions",
    )
    session.messages.append(
        ChatMessage(role="assistant", content=QUESTION_BY_STEP["source_permissions"])
    )
    _append_trace(
        session,
        base_id="session-created",
        title="Started instructor onboarding",
        detail="The prototype opened the source-permission interview step.",
        status="complete",
    )
    return session


def submit_message(session: OnboardingSession, user_message: str) -> OnboardingSession:
    graph = _build_graph()
    result = graph.invoke({"session": session, "user_message": user_message})
    return result["session"]


@lru_cache(maxsize=1)
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

    if session.current_step == "professor_approval":
        if session.revision_proposal and _is_confirmation_message(user_message):
            session = confirm_revision_proposal(session)
            session.messages.append(
                ChatMessage(
                    role="assistant",
                    content=(
                        "Confirmed. I updated the affected policy fields and "
                        "regenerated the preview evidence for review."
                    ),
                )
            )
            return {"session": session, "user_message": user_message}

        if session.revision_proposal and _is_discard_message(user_message):
            session = discard_revision_proposal(session)
            session.messages.append(
                ChatMessage(
                    role="assistant",
                    content="Discarded the pending revision proposal.",
                )
            )
            return {"session": session, "user_message": user_message}

        proposal = _proposal_from_feedback(session, user_message)
        if proposal is not None:
            session.revision_proposal = proposal
            session.messages.append(
                ChatMessage(
                    role="assistant",
                    content=(
                        "I mapped that feedback to a policy revision. Confirm "
                        f"to apply: {proposal.proposed_value}"
                    ),
                )
            )
            _append_trace(
                session,
                base_id="revision-proposal-created",
                title="Proposed policy revision from chat feedback",
                detail=proposal.rationale,
                status="warning",
            )
        else:
            session.messages.append(
                ChatMessage(
                    role="assistant",
                    content=(
                        "The draft tutor policy is ready for policy review and "
                        "approval. Review the policy fields, preview cases, and "
                        "approval checklist before releasing it to students."
                    ),
                )
            )
            _append_trace(
                session,
                base_id="professor-approval-message-received",
                title="Kept draft policy in professor review",
                detail=(
                    "The instructor sent another message after draft generation; "
                    "the generated review artifacts were preserved."
                ),
                status="blocked",
            )
        return {"session": session, "user_message": user_message}

    if not user_message:
        session.messages.append(
            ChatMessage(
                role="assistant",
                content=_empty_answer_follow_up(session.current_step),
            )
        )
        _append_trace(
            session,
            base_id=f"{session.current_step}-empty-answer",
            title="Asked for concrete answer",
            detail=(
                "The instructor submitted an empty answer, so no policy "
                "field was captured."
            ),
            status="warning",
        )
        return {"session": session, "user_message": user_message}

    if _needs_follow_up(session.current_step, user_message):
        session.messages.append(
            ChatMessage(
                role="assistant",
                content=_follow_up_for(session.current_step),
            )
        )
        _append_trace(
            session,
            base_id=f"{session.current_step}-follow-up",
            title="Asked follow-up question",
            detail="The instructor answer was too broad to encode safely.",
            status="warning",
        )
        return {"session": session, "user_message": user_message}

    session.answers[session.current_step] = user_message
    _append_trace(
        session,
        base_id=f"{session.current_step}-captured",
        title=f"Captured {session.current_step.replace('_', ' ')}",
        detail=user_message,
        status="complete",
    )

    next_step = _next_step(session.current_step)
    if next_step is None:
        session.current_step = "professor_approval"
        session.policy = _build_policy(session.answers)
        session.preview_cases = _build_preview_cases(session.policy, session.policy_version)
        session.preview_decisions = {
            preview.id: _decision_record_for(preview)
            for preview in session.preview_cases
        }
        session.evidence_snapshots = [
            _snapshot_for(preview) for preview in session.preview_cases
        ]
        session.approval_checklist = _build_approval_checklist()
        _recompute_release_state(session)
        _append_trace(
            session,
            base_id="draft-policy-generated",
            title="Generated draft tutor policy",
            detail=(
                "The prototype converted interview answers into reviewable "
                "policy fields."
            ),
            status="blocked",
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


def _append_trace(
    session: OnboardingSession,
    *,
    base_id: str,
    title: str,
    detail: str,
    status: Literal["complete", "warning", "blocked"],
) -> None:
    session.trace.append(
        WorkflowTraceItem(
            id=f"{base_id}-{len(session.trace) + 1}",
            title=title,
            detail=detail,
            status=status,
        )
    )
