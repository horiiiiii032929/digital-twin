import re

from src.digital_twin.generation.models import PolicyAction, PolicyDecision
from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.tutor_policy import FieldStatus, ReleaseStatus, TutorPolicy


_GRADED_CONTEXT = re.compile(
    r"\b(homework|assignment|quiz|exam|test|graded|coursework|project)\b",
    re.IGNORECASE,
)
_DIRECT_COMPLETION = re.compile(
    r"\b(full answer|final answer|complete solution|write (?:it|this|the answer)|"
    r"complete graded work|do (?:it|this|my)|solve (?:it|this|the problem)|"
    r"solve (?:my|the) (?:homework|assignment|quiz|exam|test|project)|"
    r"finish (?:my|the) (?:homework|assignment|quiz|exam|test|project)|"
    r"give me (?:the|a) answer)\b",
    re.IGNORECASE,
)


class DeterministicPolicyEnforcer:
    """Apply inspectable academic-integrity and evidence rules before generation."""

    implementation_id = "deterministic-policy-rules"
    version = "v1"

    def evaluate(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
    ) -> PolicyDecision:
        if not question.strip():
            return PolicyDecision(
                action=PolicyAction.INVALID_REQUEST,
                reason="The student question is empty.",
                matched_rules=["non-empty-question-required"],
            )
        if not policy_is_approved_for_generation(policy):
            return PolicyDecision(
                action=PolicyAction.POLICY_NOT_APPROVED,
                reason="The professor has not approved this tutor policy for release.",
                matched_rules=["professor-release-approval-required"],
            )
        if not hits:
            return PolicyDecision(
                action=PolicyAction.NO_EVIDENCE,
                reason="No approved retrieval evidence is available.",
                matched_rules=["approved-evidence-required"],
            )
        if _GRADED_CONTEXT.search(question) and _DIRECT_COMPLETION.search(question):
            policy_field = next(
                (
                    field
                    for field in policy.all_fields
                    if field.id == "academic_integrity_policy"
                ),
                None,
            )
            policy_rule = (
                "professor-policy:academic_integrity_policy"
                if policy_field is not None
                else "safe-default:no-full-graded-work-answer"
            )
            return PolicyDecision(
                action=PolicyAction.REDIRECT_GRADED_WORK,
                reason="The request asks for direct completion of graded work.",
                matched_rules=["attempt-first", policy_rule],
            )
        return PolicyDecision(
            action=PolicyAction.ANSWER,
            reason="Approved evidence is available and no integrity rule matched.",
        )


def policy_is_approved_for_generation(policy: TutorPolicy) -> bool:
    if (
        policy.status != ReleaseStatus.APPROVED
        or policy.release_status != ReleaseStatus.APPROVED
        or policy.blocker_ids
    ):
        return False
    approval = next(
        (
            field
            for field in policy.all_fields
            if field.id == "professor_release_approval"
        ),
        None,
    )
    knowledge = next(
        (field for field in policy.all_fields if field.id == "knowledge_source_policy"),
        None,
    )
    integrity = next(
        (
            field
            for field in policy.all_fields
            if field.id == "academic_integrity_policy"
        ),
        None,
    )
    return bool(
        approval is not None
        and approval.status == FieldStatus.RESOLVED
        and approval.value == "approved"
        and knowledge is not None
        and knowledge.status == FieldStatus.RESOLVED
        and isinstance(knowledge.value, dict)
        and knowledge.value.get("confirmed") is True
        and integrity is not None
        and integrity.status == FieldStatus.RESOLVED
    )
