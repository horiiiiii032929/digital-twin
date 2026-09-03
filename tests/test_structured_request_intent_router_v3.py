import pytest

from src.digital_twin.action_router import (
    DeterministicActionRouterV3,
    classify_academic_integrity_request,
)
from src.digital_twin.generation.models import PolicyAction
from src.digital_twin.generation.policy import DeterministicPolicyEnforcer
from tests.digital_twin.test_generation import approved_hit, approved_policy


@pytest.mark.parametrize(
    "question",
    [
        (
            "Ask one diagnostic question or give one grounded hint that helps me "
            "test my explanation."
        ),
        "Give me a hint for my exam.",
        "Can you explain this test question?",
        "Help me understand this assignment without writing it for me.",
        "Review my reasoning for the quiz and tell me where it first goes wrong.",
        "Can we work through a similar example before my exam?",
        "Create a practice test about virtual memory.",
        "Give me the final answer to this practice test so I can check my work.",
        "What does a software test verify?",
        "Explain project scheduling and give one example.",
    ],
)
def test_v3_never_redirects_permitted_tutoring_or_non_assessment_uses(question):
    route = DeterministicActionRouterV3().route(question)

    assert route is None or route.action != "redirect-graded-work"


@pytest.mark.parametrize(
    "question",
    [
        "Give me the answer to my exam.",
        "Complete my graded CS101 response about cache coherence and give it to me.",
        "Write a submission-ready answer for this assignment about virtual memory.",
        "Provide the quiz response that I can submit for marks.",
        "Solve my homework.",
        "Finish this coursework for me.",
        "Write my project.",
        "Answer this test question for me.",
        "Give me the full solution for the current exam.",
        "Complete the assessed report so I can submit it.",
    ],
)
def test_v3_redirects_explicit_submission_ready_graded_work(question):
    route = DeterministicActionRouterV3().route(question)

    assert route is not None
    assert route.action == "redirect-graded-work"
    assert route.matched_rule == "structured-request-intent-v3"


def test_v3_contract_separates_artifact_from_requested_assistance():
    tutoring = classify_academic_integrity_request("Give me a hint for my exam.")
    completion = classify_academic_integrity_request(
        "Give me the answer to my exam."
    )
    explanation_test = classify_academic_integrity_request(
        "Give one hint to help me test my explanation."
    )

    assert tutoring.assessed_artifact == "exam"
    assert tutoring.requested_assistance == "tutoring-help"
    assert not tutoring.requires_integrity_redirect
    assert completion.assessed_artifact == "exam"
    assert completion.requested_assistance == "submission-ready-completion"
    assert completion.requires_integrity_redirect
    assert explanation_test.assessed_artifact is None
    assert explanation_test.requested_assistance == "tutoring-help"


def test_v3_policy_enforcer_does_not_fall_back_to_legacy_lexical_rule():
    decision = DeterministicPolicyEnforcer(
        action_router=DeterministicActionRouterV3()
    ).evaluate(
        (
            "Ask one diagnostic question or give one grounded hint that helps me "
            "test my explanation."
        ),
        [approved_hit()],
        approved_policy(),
    )

    assert decision.action == PolicyAction.ANSWER


def test_v3_structured_classifier_does_not_read_evidence_or_gold():
    intent = classify_academic_integrity_request(
        "Write a submission-ready response for my graded assignment."
    )

    assert intent.requires_integrity_redirect
    assert intent.artifact_signals
    assert intent.assistance_signals
