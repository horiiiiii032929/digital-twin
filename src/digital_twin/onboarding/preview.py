from uuid import uuid4

from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.tutor_policy import (
    ApprovalItem,
    EvidenceSnapshot,
    PreviewAuditEntry,
    PreviewCase,
    PreviewDecisionRecord,
    PromptTag,
    SourceLabel,
    TutorPolicy,
    timestamp_now,
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
