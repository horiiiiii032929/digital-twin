from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.digital_twin.tutor_policy import (
    ApprovalItem,
    ChatMessage,
    EvidenceSnapshot,
    FieldStatus,
    KnowledgeSourcePolicy,
    PolicyField,
    PreviewAuditEntry,
    PreviewCase,
    PreviewDecisionRecord,
    PreviewDecisionValue,
    PromptTag,
    ReleaseStatus,
    RevisionProposal,
    SourceInventoryItem,
    SourceLabel,
    SourcePermissionStatus,
    TutorPolicy,
    WorkflowTraceItem,
    timestamp_now,
)


class OnboardingSession(BaseModel):
    session_id: str
    current_step: str
    answers: dict[str, str] = Field(default_factory=dict)
    messages: list[ChatMessage] = Field(default_factory=list)
    source_inventory: list[SourceInventoryItem] = Field(default_factory=list)
    policy: TutorPolicy | None = None
    policy_version: int = 1
    preview_cases: list[PreviewCase] = Field(default_factory=list)
    preview_decisions: dict[str, PreviewDecisionRecord] = Field(default_factory=dict)
    evidence_snapshots: list[EvidenceSnapshot] = Field(default_factory=list)
    revision_proposal: RevisionProposal | None = None
    approval_checklist: list[ApprovalItem] = Field(default_factory=list)
    release_blockers: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "source_inventory": [],
            "policy_fields": [],
            "approval_checklist": [],
            "preview_decisions": [],
            "preview_acceptance": [],
        }
    )
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
    "use the internet if needed",
    "make it friendly",
)

ACADEMIC_INTEGRITY_OPERATIONAL_SIGNALS = (
    "ask what",
    "tried",
    "hints",
    "refuse",
    "similar example",
    "partial structure",
    "no full",
    "full graded answers",
)

REQUIRED_PREVIEW_CASE_IDS = frozenset(
    {"external-grounding", "academic-integrity", "misconception"}
)
CUSTOM_PREVIEW_REQUIRED_BLOCKER = (
    "Add and accept a professor custom prompt preview."
)


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


def _needs_follow_up(step: str, message: str) -> bool:
    normalized_message = _normalize_for_vague_detection(message)
    if step == "academic_integrity" and _has_operational_signal(normalized_message):
        return False
    return any(
        _is_exact_or_short_vague_answer(normalized_message, phrase)
        for phrase in VAGUE_PHRASES
    )


def _normalize_for_vague_detection(message: str) -> str:
    return " ".join(message.lower().replace("’", "'").strip(" .!?:;").split())


def _has_operational_signal(normalized_message: str) -> bool:
    return any(
        signal in normalized_message
        for signal in ACADEMIC_INTEGRITY_OPERATIONAL_SIGNALS
    )


def _is_exact_or_short_vague_answer(message: str, phrase: str) -> bool:
    if message == phrase:
        return True
    if phrase not in message:
        return False
    return len(message.split()) <= len(phrase.split()) + 3


def _empty_answer_follow_up(step: str) -> str:
    question = QUESTION_BY_STEP.get(step)
    if question is None:
        return "Please provide a concrete answer before we continue."
    return f"Please provide a concrete answer before we continue. {question}"


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
    knowledge_policy = KnowledgeSourcePolicy().model_dump(mode="json")
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
                value=knowledge_policy,
                safe_default=(
                    "Preview may use any_source_with_labels, but release requires "
                    "an explicit source strictness confirmation."
                ),
            ),
            PolicyField(
                id="disallowed_private_sources",
                label="Disallowed private sources",
                status=FieldStatus.BLOCKS_RELEASE,
                value=[
                    "private student data",
                    "consent records",
                    "raw transcripts",
                    "private forum exports",
                    "unapproved instructor material",
                ],
                safe_default=(
                    "Exclude private student data, consent records, raw transcripts, "
                    "private forum exports, and unapproved instructor material."
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
                id="tutoring_moves",
                label="Tutoring moves",
                status=FieldStatus.NEEDS_REVIEW,
                value=["hints", "prompts", "misconception_correction"],
            ),
            PolicyField(
                id="feedback_policy",
                label="Feedback policy",
                status=FieldStatus.NEEDS_REVIEW,
                value="process feedback with concise task-level correction",
            ),
            PolicyField(
                id="proactive_support",
                label="Proactive support",
                status=FieldStatus.NEEDS_REVIEW,
                value="short checks when useful; no unsolicited practice plan",
            ),
            PolicyField(
                id="course_scope_boundary",
                label="Course scope boundary",
                status=FieldStatus.NEEDS_REVIEW,
                value="stay within approved course topics and visibly label external grounding",
            ),
            PolicyField(
                id="preferred_examples",
                label="Preferred examples",
                status=FieldStatus.NEEDS_REVIEW,
                value=["course-provided examples", "small analogous examples"],
            ),
            PolicyField(
                id="approval_criteria",
                label="Professor rejection criteria",
                status=FieldStatus.RESOLVED,
                value=answers["approval_criteria"],
            ),
            PolicyField(
                id="rejection_criteria",
                label="Rejection criteria",
                status=FieldStatus.RESOLVED,
                value=answers["approval_criteria"],
            ),
            PolicyField(
                id="tone_guidance",
                label="Tone guidance",
                status=FieldStatus.NEEDS_REVIEW,
                value="clear, concise, and professor-reviewable",
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


TRUSTED_SOURCE_CATALOG = [
    PreviewAuditEntry(
        source_title="Course syllabus CSRF unit",
        url="local://course/syllabus#csrf",
        source_type="course_material_metadata",
        source_label=SourceLabel.COURSE_APPROVED,
        supports="Course framing for CSRF as an authenticated-request problem.",
        conflict_status="not_checked",
        selection_reason="Synthetic course-approved source label for Sprint 1 preview.",
    ),
    PreviewAuditEntry(
        source_title="OWASP CSRF Prevention Cheat Sheet",
        url="https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html",
        source_type="official_documentation",
        source_label=SourceLabel.SYSTEM_SUGGESTED_TRUSTED,
        supports="External grounding for CSRF tokens and SameSite cookie defenses.",
        conflict_status="no_course_comparison",
        selection_reason="Deterministic trusted-source catalog entry; no live search provider used.",
    ),
]


def _build_preview_cases(
    policy: TutorPolicy,
    policy_version: int,
) -> list[PreviewCase]:
    return [
        _build_preview_case(
            case_id="external-grounding",
            tag="source_grounding",
            prompt=(
                "How should I explain SameSite cookies as one CSRF defense for "
                "this course?"
            ),
            generic_response=(
                "SameSite cookies help prevent browsers from sending cookies on "
                "cross-site requests, which can reduce CSRF risk."
            ),
            configured_response=(
                "For this course, frame SameSite as one defense that limits when "
                "the browser sends cookies on cross-site requests. Pair it with "
                "the course-approved CSRF framing: the attacker relies on an "
                "already-authenticated browser, so defenses should validate "
                "state-changing requests and reduce ambient cookie authority.\n\n"
                "Source labels: course-approved; system-suggested-trusted."
            ),
            policy_signals=[
                "visible source labels",
                _source_strictness_signal(policy),
                "deterministic trusted-source catalog",
            ],
            source_audit=TRUSTED_SOURCE_CATALOG,
            warnings=["no course comparison available for conflict checking"],
            policy_version=policy_version,
        ),
        _build_preview_case(
            case_id="academic-integrity",
            tag="academic_integrity",
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
                "I cannot write the full graded-work answer for you. First, what "
                "part have you already tried? I can help with a hint: distinguish "
                "CSRF from password theft by focusing on the already-authenticated "
                "browser session, then connect defenses to request validation.\n\n"
                "Source labels: course-approved."
            ),
            policy_signals=[
                "attempt-first support",
                "no full graded-work answers",
                _field_value_as_signal(policy, "academic_integrity_policy"),
            ],
            source_audit=[TRUSTED_SOURCE_CATALOG[0]],
            warnings=_academic_integrity_warnings(policy),
            policy_version=policy_version,
        ),
        _build_preview_case(
            case_id="misconception",
            tag="misconception",
            prompt=(
                "CSRF happens because hackers steal your password, right? How do I "
                "prevent it?"
            ),
            generic_response=(
                "Password theft can be part of attacks. Use strong passwords and "
                "tokens."
            ),
            configured_response=(
                "Not quite. CSRF is different from password theft: it relies on a "
                "browser that is already authenticated and tricks it into sending "
                "an unwanted request. To prevent it, focus on request validation, "
                "CSRF tokens, SameSite cookies, and checking unsafe state-changing "
                "requests.\n\nSource labels: course-approved; "
                "system-suggested-trusted."
            ),
            policy_signals=[
                "misconception correction",
                "contrastive explanation",
                _field_value_as_signal(policy, "misconception_handling"),
            ],
            source_audit=TRUSTED_SOURCE_CATALOG,
            warnings=["no course comparison available for conflict checking"],
            policy_version=policy_version,
        ),
    ]


def _build_preview_case(
    *,
    case_id: str,
    tag: PromptTag,
    prompt: str,
    generic_response: str,
    configured_response: str,
    policy_signals: list[str],
    source_audit: list[PreviewAuditEntry],
    warnings: list[str],
    policy_version: int,
) -> PreviewCase:
    return PreviewCase(
        id=case_id,
        tag=tag,
        prompt=prompt,
        generic_response=generic_response,
        configured_response=configured_response,
        policy_signals=policy_signals,
        source_audit=source_audit,
        warnings=warnings,
        policy_version=policy_version,
        generated_at=timestamp_now(),
    )


def _build_custom_preview_case(
    *,
    case_id: str,
    prompt: str,
    tag: PromptTag,
    policy: TutorPolicy,
    policy_version: int,
) -> PreviewCase:
    return _build_preview_case(
        case_id=case_id,
        tag=tag,
        prompt=prompt,
        generic_response=(
            "A generic tutor would answer directly without using this course's "
            "configured source and integrity rules."
        ),
        configured_response=(
            "Using the current tutor policy, I would answer with the configured "
            "teaching approach, avoid completing graded work, and visibly label "
            "any source grounding.\n\nSource labels: course-approved."
        ),
        policy_signals=[
            "professor-authored prompt",
            tag,
            _source_strictness_signal(policy),
        ],
        source_audit=[TRUSTED_SOURCE_CATALOG[0]],
        warnings=[],
        policy_version=policy_version,
    )


def _field_value_as_signal(policy: TutorPolicy, field_id: str) -> str:
    for field in policy.all_fields:
        if field.id == field_id:
            if isinstance(field.value, list):
                return ", ".join(field.value)
            if isinstance(field.value, dict):
                return str(field.value.get("source_strictness", "configured"))
            return str(field.value)
    return "configured policy"


def _source_strictness_signal(policy: TutorPolicy) -> str:
    for field in policy.all_fields:
        if field.id == "knowledge_source_policy" and isinstance(field.value, dict):
            return f"preview source mode: {field.value.get('preview_source_mode')}"
    return "preview source mode: any_source_with_labels"


def _academic_integrity_warnings(policy: TutorPolicy) -> list[str]:
    for field in policy.all_fields:
        if field.id == "academic_integrity_policy":
            return [field.warning] if field.warning else []
    return []


def _build_approval_checklist() -> list[ApprovalItem]:
    return [
        ApprovalItem(
            id="source_scope",
            label="Approved source scope is explicit",
            blocks_release=True,
        ),
        ApprovalItem(
            id="private_sources",
            label="Private and sensitive sources are excluded or documented",
            blocks_release=True,
        ),
        ApprovalItem(
            id="source_strictness",
            label="Knowledge source strictness is confirmed",
            blocks_release=True,
        ),
        ApprovalItem(
            id="integrity",
            label="Academic-integrity behavior is acceptable",
            blocks_release=True,
        ),
        ApprovalItem(
            id="sensitive_data",
            label="Sensitive data handling is confirmed",
            blocks_release=True,
        ),
        ApprovalItem(
            id="pedagogy",
            label="Teaching approach matches instructor intent",
            blocks_release=False,
        ),
        ApprovalItem(
            id="preview_external_grounding",
            label="External-grounding preview is accepted",
            blocks_release=True,
        ),
        ApprovalItem(
            id="preview_academic_integrity",
            label="Academic-integrity preview is accepted or warning acknowledged",
            blocks_release=True,
        ),
        ApprovalItem(
            id="preview_custom_prompt",
            label="Professor custom prompt preview is accepted",
            blocks_release=True,
        ),
        ApprovalItem(
            id="professor_release_approval",
            label="Professor explicitly approves student-facing release",
            blocks_release=True,
        ),
    ]


def add_source_inventory_item(
    session: OnboardingSession,
    *,
    name: str,
    mime_type: str = "application/octet-stream",
    size_bytes: int = 0,
    permission_status: SourcePermissionStatus = SourcePermissionStatus.PENDING,
    source_label: SourceLabel = SourceLabel.COURSE_APPROVED,
    excluded: bool = False,
    sensitive: bool | None = None,
    notes: str = "",
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    updated.source_inventory.append(
        SourceInventoryItem(
            id=f"source-{uuid4()}",
            name=name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            permission_status=permission_status,
            source_label=source_label,
            excluded=excluded,
            sensitive=sensitive,
            notes=notes,
        )
    )
    _recompute_release_state(updated)
    return updated


def update_source_inventory_item(
    session: OnboardingSession,
    source_id: str,
    **changes: Any,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    for index, item in enumerate(updated.source_inventory):
        if item.id == source_id:
            payload = item.model_dump(mode="json")
            payload.update({key: value for key, value in changes.items() if value is not None})
            updated.source_inventory[index] = SourceInventoryItem.model_validate(payload)
            _recompute_release_state(updated)
            return updated
    raise ValueError("source_inventory_item_not_found")


def update_policy_field_value(
    session: OnboardingSession,
    field_id: str,
    value: str | list[str] | dict,
    status: FieldStatus,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    if updated.policy is None:
        raise ValueError("policy_not_ready")

    for field in updated.policy.all_fields:
        if field.id == field_id:
            field.value = value
            field.status = status
            if status == FieldStatus.RESOLVED:
                field.warning = None
            _recompute_release_state(updated)
            return updated

    raise ValueError("policy_field_not_found")


def update_approval_checklist_item(
    session: OnboardingSession,
    item_id: str,
    checked: bool,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    for item in updated.approval_checklist:
        if item.id == item_id:
            item.checked = checked
            _sync_policy_from_approval(updated, item_id, checked)
            _recompute_release_state(updated)
            return updated
    raise ValueError("approval_item_not_found")


def set_preview_decision(
    session: OnboardingSession,
    preview_case_id: str,
    decision: PreviewDecisionValue,
    reason: str | None = None,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    for preview in updated.preview_cases:
        if preview.id == preview_case_id:
            preview.decision = decision
            preview.decision_reason = reason
            updated.preview_decisions[preview_case_id] = PreviewDecisionRecord(
                preview_case_id=preview_case_id,
                decision=decision,
                reason=reason,
                policy_version=updated.policy_version,
            )
            updated.evidence_snapshots.append(_snapshot_for(preview))
            _sync_preview_checklist(updated, preview_case_id, decision)
            _recompute_release_state(updated)
            return updated
    raise ValueError("preview_case_not_found")


def add_custom_preview_case(
    session: OnboardingSession,
    *,
    prompt: str,
    tag: PromptTag,
) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    if updated.policy is None:
        raise ValueError("policy_not_ready")

    custom_count = sum(
        1 for preview in updated.preview_cases if preview.id.startswith("custom-")
    )
    preview = _build_custom_preview_case(
        case_id=f"custom-{custom_count + 1}",
        prompt=prompt,
        tag=tag,
        policy=updated.policy,
        policy_version=updated.policy_version,
    )
    updated.preview_cases.append(preview)
    updated.preview_decisions[preview.id] = _decision_record_for(preview)
    updated.evidence_snapshots.append(_snapshot_for(preview))
    _recompute_release_state(updated)
    return updated


def confirm_revision_proposal(session: OnboardingSession) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    proposal = updated.revision_proposal
    if proposal is None:
        raise ValueError("revision_proposal_not_found")
    if updated.policy is None:
        raise ValueError("policy_not_ready")

    for field_id in proposal.affected_policy_fields:
        field = _find_policy_field(updated.policy, field_id)
        if field is None:
            continue
        if field_id == "tutoring_moves":
            field.value = ["guiding_question", "hints", "partial_structure"]
        else:
            field.value = proposal.proposed_value
        field.status = FieldStatus.RESOLVED
        field.warning = None

    updated.policy_version += 1
    _regenerate_previews(updated)
    if proposal.preview_case_id and proposal.preview_case_id in updated.preview_decisions:
        updated.preview_decisions[proposal.preview_case_id] = PreviewDecisionRecord(
            preview_case_id=proposal.preview_case_id,
            decision="pending",
            reason="Regenerated after confirmed revision.",
            policy_version=updated.policy_version,
            revision_resolved=True,
        )
        for preview in updated.preview_cases:
            if preview.id == proposal.preview_case_id:
                preview.decision = "pending"
                preview.decision_reason = "Regenerated after confirmed revision."

    updated.revision_proposal = None
    _recompute_release_state(updated)
    return updated


def discard_revision_proposal(session: OnboardingSession) -> OnboardingSession:
    updated = session.model_copy(deep=True)
    if updated.revision_proposal is None:
        raise ValueError("revision_proposal_not_found")
    updated.revision_proposal = None
    _recompute_release_state(updated)
    return updated


def _decision_record_for(preview: PreviewCase) -> PreviewDecisionRecord:
    return PreviewDecisionRecord(
        preview_case_id=preview.id,
        decision=preview.decision,
        reason=preview.decision_reason,
        policy_version=preview.policy_version,
    )


def _snapshot_for(preview: PreviewCase) -> EvidenceSnapshot:
    return EvidenceSnapshot(
        id=f"evidence-{uuid4()}",
        preview_case_id=preview.id,
        prompt=preview.prompt,
        configured_response=preview.configured_response,
        source_audit=preview.source_audit,
        source_labels=[entry.source_label for entry in preview.source_audit],
        warnings=preview.warnings,
        decision=preview.decision,
        policy_version=preview.policy_version,
    )


def _find_policy_field(policy: TutorPolicy, field_id: str) -> PolicyField | None:
    return next((field for field in policy.all_fields if field.id == field_id), None)


def _sync_policy_from_approval(
    session: OnboardingSession,
    item_id: str,
    checked: bool,
) -> None:
    if session.policy is None or not checked:
        return

    field_updates: dict[str, tuple[str | list[str] | dict, FieldStatus]] = {
        "source_strictness": (
            _confirmed_knowledge_policy_value(session.policy),
            FieldStatus.RESOLVED,
        ),
        "private_sources": (
            [
                "private student data",
                "consent records",
                "raw transcripts",
                "private forum exports",
            ],
            FieldStatus.RESOLVED,
        ),
        "sensitive_data": (
            "Sensitive data remains excluded; only synthetic examples are used.",
            FieldStatus.RESOLVED,
        ),
        "integrity": (
            _field_value_as_signal(session.policy, "academic_integrity_policy"),
            FieldStatus.RESOLVED,
        ),
        "professor_release_approval": ("approved", FieldStatus.RESOLVED),
    }
    field_id_by_item = {
        "source_strictness": "knowledge_source_policy",
        "private_sources": "disallowed_private_sources",
        "sensitive_data": "sensitive_data_handling",
        "integrity": "academic_integrity_policy",
        "professor_release_approval": "professor_release_approval",
    }

    field_id = field_id_by_item.get(item_id)
    update = field_updates.get(item_id)
    if field_id is None or update is None:
        return

    field = _find_policy_field(session.policy, field_id)
    if field is None:
        return
    field.value, field.status = update
    if field.status == FieldStatus.RESOLVED:
        field.warning = None


def _confirmed_knowledge_policy_value(policy: TutorPolicy) -> dict:
    field = _find_policy_field(policy, "knowledge_source_policy")
    if field is not None and isinstance(field.value, dict):
        value = dict(field.value)
    else:
        value = KnowledgeSourcePolicy().model_dump(mode="json")
    value["source_strictness"] = (
        value.get("source_strictness")
        if value.get("source_strictness") != "unresolved"
        else "any_source_with_labels"
    )
    value["confirmed"] = True
    return value


def _sync_preview_checklist(
    session: OnboardingSession,
    preview_case_id: str,
    decision: PreviewDecisionValue,
) -> None:
    if decision != "accepted":
        return
    checklist_id_by_preview = {
        "external-grounding": "preview_external_grounding",
        "academic-integrity": "preview_academic_integrity",
    }
    checklist_id = checklist_id_by_preview.get(preview_case_id)
    if preview_case_id.startswith("custom-"):
        checklist_id = "preview_custom_prompt"
    if checklist_id is None:
        return
    for item in session.approval_checklist:
        if item.id == checklist_id:
            item.checked = True


def _regenerate_previews(session: OnboardingSession) -> None:
    if session.policy is None:
        return

    custom_prompts = [
        (preview.id, preview.prompt, preview.tag)
        for preview in session.preview_cases
        if preview.id.startswith("custom-")
    ]
    session.preview_cases = _build_preview_cases(session.policy, session.policy_version)
    for case_id, prompt, tag in custom_prompts:
        session.preview_cases.append(
            _build_custom_preview_case(
                case_id=case_id,
                prompt=prompt,
                tag=tag,
                policy=session.policy,
                policy_version=session.policy_version,
            )
        )
    session.evidence_snapshots.extend(
        _snapshot_for(preview) for preview in session.preview_cases
    )
    for preview in session.preview_cases:
        session.preview_decisions[preview.id] = PreviewDecisionRecord(
            preview_case_id=preview.id,
            decision="pending",
            reason="Regenerated for current policy version.",
            policy_version=session.policy_version,
        )


def _proposal_from_feedback(
    session: OnboardingSession,
    feedback: str,
) -> RevisionProposal | None:
    normalized = feedback.lower()
    rejected_case_id = next(
        (
            case_id
            for case_id, record in session.preview_decisions.items()
            if record.decision == "rejected"
        ),
        None,
    )
    if any(
        phrase in normalized
        for phrase in (
            "homework",
            "graded",
            "too much",
            "full answer",
            "gives away",
        )
    ):
        return RevisionProposal(
            id=f"revision-{uuid4()}",
            preview_case_id=rejected_case_id or "academic-integrity",
            feedback=feedback,
            affected_policy_fields=[
                "academic_integrity_policy",
                "tutoring_moves",
            ],
            proposed_value=(
                "Require one guiding question before hints; never provide the "
                "full graded-work answer or complete solution structure."
            ),
            rationale=(
                "The feedback indicates an academic-integrity boundary problem "
                "and a tutoring-move adjustment."
            ),
        )
    if any(phrase in normalized for phrase in ("source", "citation", "cite")):
        return RevisionProposal(
            id=f"revision-{uuid4()}",
            preview_case_id=rejected_case_id or "external-grounding",
            feedback=feedback,
            affected_policy_fields=["knowledge_source_policy"],
            proposed_value=(
                "Require visible source labels and source audit entries for any "
                "external grounding."
            ),
            rationale="The feedback indicates a source-grounding or citation issue.",
        )
    if any(phrase in normalized for phrase in ("tone", "wording", "friendly")):
        return RevisionProposal(
            id=f"revision-{uuid4()}",
            preview_case_id=rejected_case_id,
            feedback=feedback,
            affected_policy_fields=["tone_guidance"],
            proposed_value="Use concise, direct, professor-reviewable wording.",
            rationale="The feedback indicates a tone or wording adjustment.",
        )
    return None


def _is_confirmation_message(message: str) -> bool:
    return _normalize_for_vague_detection(message) in {"confirm", "yes", "apply"}


def _is_discard_message(message: str) -> bool:
    return _normalize_for_vague_detection(message) in {
        "discard",
        "cancel",
        "no",
    }


def _recompute_release_state(session: OnboardingSession) -> None:
    blockers = {
        "source_inventory": _source_inventory_blockers(session),
        "policy_fields": _policy_field_blockers(session),
        "approval_checklist": _approval_checklist_blockers(session),
        "preview_decisions": _preview_decision_blockers(session),
        "preview_acceptance": _preview_acceptance_blockers(session),
    }
    session.release_blockers = blockers

    if session.policy is None:
        return

    is_approved = all(not values for values in blockers.values())
    session.policy.release_status = (
        ReleaseStatus.APPROVED if is_approved else ReleaseStatus.BLOCKED
    )
    session.policy.status = ReleaseStatus.APPROVED if is_approved else ReleaseStatus.DRAFT


def _source_inventory_blockers(session: OnboardingSession) -> list[str]:
    blockers: list[str] = []
    for source in session.source_inventory:
        if source.excluded:
            continue
        if source.permission_status == SourcePermissionStatus.PENDING:
            blockers.append(
                f"{source.name} needs an approve or exclude decision."
            )
        if source.sensitive:
            blockers.append(
                f"{source.name} is sensitive and must remain excluded unless documented."
            )
    return blockers


def _policy_field_blockers(session: OnboardingSession) -> list[str]:
    if session.policy is None:
        return []
    blockers = [field.id for field in session.policy.all_fields if field.blocks_release]
    knowledge_field = _find_policy_field(session.policy, "knowledge_source_policy")
    if (
        knowledge_field is not None
        and isinstance(knowledge_field.value, dict)
        and not knowledge_field.value.get("confirmed", False)
        and "knowledge_source_policy" not in blockers
    ):
        blockers.append("knowledge_source_policy")
    return blockers


def _approval_checklist_blockers(session: OnboardingSession) -> list[str]:
    return [
        item.id
        for item in session.approval_checklist
        if item.is_blocking_incomplete
    ]


def _preview_decision_blockers(session: OnboardingSession) -> list[str]:
    return [
        f"{case_id} is rejected and unresolved."
        for case_id, record in session.preview_decisions.items()
        if record.decision == "rejected" and not record.revision_resolved
    ]


def _preview_acceptance_blockers(session: OnboardingSession) -> list[str]:
    if not session.preview_cases:
        return []
    required_ids = set(REQUIRED_PREVIEW_CASE_IDS)
    custom_preview_id = next(
        (
            preview.id
            for preview in session.preview_cases
            if preview.id.startswith("custom-")
        ),
        None,
    )
    if custom_preview_id is not None:
        required_ids.add(custom_preview_id)

    blockers: list[str] = []
    for preview_id in sorted(required_ids):
        record = session.preview_decisions.get(preview_id)
        if record is None or record.decision != "accepted":
            blockers.append(f"{preview_id} preview is not accepted.")
    if custom_preview_id is None:
        blockers.append(CUSTOM_PREVIEW_REQUIRED_BLOCKER)
    return blockers
