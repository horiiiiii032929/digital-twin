"""Deterministic pre-generation routing for release-critical boundaries."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


RoutedAction = Literal["clarify", "no-evidence", "redirect-graded-work"]
AssessedArtifactKind = Literal[
    "homework",
    "assignment",
    "quiz",
    "exam",
    "test",
    "coursework",
    "project",
    "graded-deliverable",
]
RequestedAssistanceKind = Literal[
    "submission-ready-completion",
    "tutoring-help",
    "unspecified",
]


_DEICTIC_ACTION_QUESTION = re.compile(
    r"\b(?:what\s+does\s+[\"'“”]?(?:it|this|that|these|those)[\"'“”]?\s+"
    r"(?:do|refer\s+to|mean)|how\s+does\s+[\"'“”]?(?:it|this|that)"
    r"[\"'“”]?\s+work)\b",
    re.IGNORECASE,
)
_GRADED_CONTEXT = re.compile(
    r"\b(homework|assignment|quiz|exam|test|graded|coursework|project)\b",
    re.IGNORECASE,
)
_DIRECT_COMPLETION = re.compile(
    r"\b(full answer|final answer|complete solution|write (?:it|this|the answer)|"
    r"complete graded work|do (?:it|this|my)|solve (?:it|this|the problem)|"
    r"solve (?:my|the) (?:homework|assignment|quiz|exam|test|project)|"
    r"finish (?:my|the) (?:homework|assignment|quiz|exam|test|project)|"
    r"give me (?:the|a) answer|answer to submit)\b",
    re.IGNORECASE,
)
_UNSUPPORTED_FUTURE = re.compile(
    r"\b(?:next academic year|unreleased|future version|2035 revision|"
    r"will be added|not yet published)\b",
    re.IGNORECASE,
)
_CROSS_COURSE = re.compile(
    r"\b(?:another|other) course\b|\boutside (?:this|the) course\b",
    re.IGNORECASE,
)
_EXPLICIT_MULTI_EVIDENCE = re.compile(
    r"\b(?:which two|both statements|two statements|connect .+ with|"
    r"relationship between|together establish)\b",
    re.IGNORECASE,
)
_DIRECT_COMPLETION_V2 = re.compile(
    r"\b(?:submission[- ]ready|ready\s+to\s+submit|answer\s+I\s+can\s+submit|"
    r"(?:give|provide|write|complete|finish|solve|answer|do)\b.{0,100}\b"
    r"(?:answer|solution|response|submission|homework|assignment|quiz|exam|test|"
    r"coursework|project|for\s+me|to\s+submit))\b",
    re.IGNORECASE,
)
_UNRESOLVED_REFERENCE_V2 = re.compile(
    r"\b(?:explain|define|compare|solve|answer|describe|summarize)\s+"
    r"(?:it|this|that|these|those|the\s+above)\b|"
    r"\bwhich\s+(?:one|option)\s+(?:is|should)\b",
    re.IGNORECASE,
)
_CROSS_SCOPE_V2 = re.compile(
    r"\b(?:another|other|different)\s+(?:course|module|subject)\b|"
    r"\b(?:outside|not\s+in)\s+(?:this|the|my)\s+(?:course|module)\b|"
    r"\bfrom\s+an?\s+unrelated\s+(?:course|module|subject)\b",
    re.IGNORECASE,
)
_UNAVAILABLE_SOURCE_V2 = re.compile(
    r"\b(?:unpublished|withdrawn|draft-only|restricted|permission denied|"
    r"not released|future release|next release|answer key not provided)\b",
    re.IGNORECASE,
)

_PRACTICE_ASSESSMENT = re.compile(
    r"\b(?:practice|sample|mock|self[- ]check)\s+(?:test|quiz|exam|assignment)\b",
    re.IGNORECASE,
)
_ASSESSED_ARTIFACT = re.compile(
    r"\b(homework|assignment|quiz|exam|coursework|project)\b",
    re.IGNORECASE,
)
_ASSESSED_TEST = re.compile(
    r"\b(?:(?:my|the|this|that|current|graded|upcoming|take[- ]home|course)\s+test|"
    r"test\s+(?:question|paper|answer|response|submission))\b",
    re.IGNORECASE,
)
_GRADED_DELIVERABLE = re.compile(
    r"\b(?:graded|assessed)\b.{0,48}\b(?:work|task|answer|response|solution|"
    r"submission|write[- ]?up|code|essay|report)\b|"
    r"\b(?:work|task|answer|response|solution|submission|write[- ]?up|code|"
    r"essay|report)\b.{0,48}\b(?:for\s+(?:marks?|a\s+grade)|graded|assessed)\b",
    re.IGNORECASE,
)
_SUBMISSION_READY = re.compile(
    r"\b(?:submission[- ]ready|ready\s+to\s+submit|to\s+submit|"
    r"submit\s+(?:it|this)|for\s+(?:marks?|a\s+grade)|"
    r"answer\s+I\s+can\s+submit)\b",
    re.IGNORECASE,
)
_FULL_DELIVERABLE = re.compile(
    r"\b(?:full|final|complete)\s+(?:answer|solution|response|submission|"
    r"write[- ]?up|code|essay|report)\b",
    re.IGNORECASE,
)
_COMPLETE_POSSESSED_ARTIFACT = re.compile(
    r"\b(?:do|complete|finish|solve|write|answer)\s+"
    r"(?:my|the|this|that|current|graded|upcoming)\s+"
    r"(?:homework|assignment|quiz|exam|test|coursework|project)\b",
    re.IGNORECASE,
)
_COMPLETE_GRADED_DELIVERABLE = re.compile(
    r"\b(?:do|complete|finish|solve|write|answer)\s+"
    r"(?:(?:my|the|this|that|current)\s+)?(?:graded|assessed)\b.{0,48}\b"
    r"(?:work|task|answer|response|solution|submission|write[- ]?up|code|"
    r"essay|report)\b",
    re.IGNORECASE,
)
_COMPLETE_ASSESSMENT_ITEM = re.compile(
    r"\b(?:answer|solve|complete|write)\s+(?:my|the|this|that)\s+"
    r"(?:quiz|exam|test|assignment|homework|coursework|project)\s+"
    r"(?:question|problem|response|answer|solution)\b",
    re.IGNORECASE,
)
_ANSWER_FOR_ARTIFACT = re.compile(
    r"\b(?:give|provide|write)\s+(?:me\s+)?(?:the\s+|a\s+|an\s+)?"
    r"(?:full\s+|final\s+|complete\s+)?(?:answer|solution|response|submission)"
    r"\s+(?:for|to)\s+(?:my|the|this|that|current|graded|upcoming)\s+"
    r"(?:homework|assignment|quiz|exam|test|coursework|project)\b|"
    r"\b(?:answer|solution|response)\s+to\s+"
    r"(?:my|the|this|that|current|graded|upcoming)\s+"
    r"(?:homework|assignment|quiz|exam|test|coursework|project)\b",
    re.IGNORECASE,
)
_TUTORING_HELP = re.compile(
    r"\b(?:hint|explain|explanation|understand|walk\s+me\s+through|"
    r"diagnostic\s+question|feedback|check\s+my|review\s+my|"
    r"test\s+my\s+(?:understanding|explanation|reasoning)|"
    r"help\s+me\s+(?:learn|understand|reason))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ActionRouteV1:
    """One inspectable boundary decision made before retrieval-backed generation."""

    action: RoutedAction
    reason: str
    matched_rule: str


@dataclass(frozen=True)
class AcademicIntegrityRequestIntentV1:
    """Structured, inspectable intent used only for integrity routing.

    Refusal requires both an assessed artifact and a request for a completed,
    submission-ready deliverable.  A shared lexical window is deliberately not
    used because verbs such as ``test`` can describe tutoring activity rather
    than an assessed artifact.
    """

    assessed_artifact: AssessedArtifactKind | None
    requested_assistance: RequestedAssistanceKind
    artifact_signals: tuple[str, ...]
    assistance_signals: tuple[str, ...]

    @property
    def requires_integrity_redirect(self) -> bool:
        return (
            self.assessed_artifact is not None
            and self.requested_assistance == "submission-ready-completion"
        )


def classify_academic_integrity_request(
    question: str,
) -> AcademicIntegrityRequestIntentV1:
    """Classify assessed artifact and requested help as separate dimensions."""

    normalized = " ".join(question.split())
    artifact_view = _PRACTICE_ASSESSMENT.sub(" ", normalized)
    artifact_match = _ASSESSED_ARTIFACT.search(artifact_view)
    test_match = _ASSESSED_TEST.search(artifact_view)
    graded_match = _GRADED_DELIVERABLE.search(artifact_view)

    artifact: AssessedArtifactKind | None = None
    artifact_signals: list[str] = []
    if artifact_match is not None:
        artifact = artifact_match.group(1).lower()  # type: ignore[assignment]
        artifact_signals.append(f"artifact:{artifact}")
    elif test_match is not None:
        artifact = "test"
        artifact_signals.append("artifact:test")
    elif graded_match is not None:
        artifact = "graded-deliverable"
        artifact_signals.append("artifact:graded-deliverable")

    completion_signals: list[str] = []
    for signal, pattern in (
        ("submission-ready", _SUBMISSION_READY),
        ("full-deliverable", _FULL_DELIVERABLE),
        ("complete-assessed-artifact", _COMPLETE_POSSESSED_ARTIFACT),
        ("complete-graded-deliverable", _COMPLETE_GRADED_DELIVERABLE),
        ("complete-assessment-item", _COMPLETE_ASSESSMENT_ITEM),
        ("answer-for-assessed-artifact", _ANSWER_FOR_ARTIFACT),
    ):
        if pattern.search(normalized):
            completion_signals.append(signal)

    if artifact is not None and completion_signals:
        assistance: RequestedAssistanceKind = "submission-ready-completion"
        assistance_signals = completion_signals
    elif _TUTORING_HELP.search(normalized):
        assistance = "tutoring-help"
        assistance_signals = ["tutoring-help"]
    else:
        assistance = "unspecified"
        assistance_signals = []

    return AcademicIntegrityRequestIntentV1(
        assessed_artifact=artifact,
        requested_assistance=assistance,
        artifact_signals=tuple(artifact_signals),
        assistance_signals=tuple(assistance_signals),
    )


class DeterministicActionRouterV1:
    """Route explicit safety and ambiguity boundaries without model judgment."""

    implementation_id = "deterministic-tutor-action-router-v1"
    version = "v1"

    def route(self, question: str) -> ActionRouteV1 | None:
        normalized = question.strip()
        if not normalized:
            return None
        if _GRADED_CONTEXT.search(normalized) and _DIRECT_COMPLETION.search(normalized):
            return ActionRouteV1(
                action="redirect-graded-work",
                reason="The request asks for direct completion of graded work.",
                matched_rule="attempt-first",
            )
        if _DEICTIC_ACTION_QUESTION.search(normalized):
            return ActionRouteV1(
                action="clarify",
                reason="The request contains an unresolved referent.",
                matched_rule="explicit-referent-required",
            )
        if _CROSS_COURSE.search(normalized):
            return ActionRouteV1(
                action="no-evidence",
                reason="The request explicitly asks beyond the active course scope.",
                matched_rule="active-course-only",
            )
        if _UNSUPPORTED_FUTURE.search(normalized):
            return ActionRouteV1(
                action="no-evidence",
                reason="The request asks about an unsupported future or unpublished state.",
                matched_rule="published-evidence-only",
            )
        return None


class DeterministicActionRouterV2:
    """Production hard-boundary router with broader, source-agnostic phrasing.

    V1 remains immutable historical evidence. V2 only expands deterministic
    safety/authority coverage; it does not infer factual answers or inspect gold.
    """

    implementation_id = "deterministic-tutor-action-router-v2"
    version = "v2"

    def route(self, question: str) -> ActionRouteV1 | None:
        normalized = " ".join(question.split())
        if not normalized:
            return None
        if _GRADED_CONTEXT.search(normalized) and (
            _DIRECT_COMPLETION.search(normalized)
            or _DIRECT_COMPLETION_V2.search(normalized)
        ):
            return ActionRouteV1(
                action="redirect-graded-work",
                reason="The request seeks a submission-ready response to graded work.",
                matched_rule="attempt-first-v2",
            )
        if _DEICTIC_ACTION_QUESTION.search(normalized) or _UNRESOLVED_REFERENCE_V2.search(
            normalized
        ):
            return ActionRouteV1(
                action="clarify",
                reason="The request does not identify the concept or alternative to address.",
                matched_rule="explicit-referent-required-v2",
            )
        if _CROSS_COURSE.search(normalized) or _CROSS_SCOPE_V2.search(normalized):
            return ActionRouteV1(
                action="no-evidence",
                reason="The request explicitly targets material outside the active course.",
                matched_rule="active-course-only-v2",
            )
        if _UNSUPPORTED_FUTURE.search(normalized) or _UNAVAILABLE_SOURCE_V2.search(
            normalized
        ):
            return ActionRouteV1(
                action="no-evidence",
                reason="The requested source state is not current and authorized.",
                matched_rule="current-authorized-evidence-only-v2",
            )
        return None


class DeterministicActionRouterV3:
    """Structured request-intent router for the active release profile.

    V1 and V2 remain available as historical controls. V3 owns the complete
    academic-integrity classification contract, so callers must not apply the
    legacy lexical fallback after a V3 non-match.
    """

    implementation_id = "deterministic-tutor-action-router-v3"
    version = "v3"
    owns_academic_integrity = True

    def route(self, question: str) -> ActionRouteV1 | None:
        normalized = " ".join(question.split())
        if not normalized:
            return None
        integrity = classify_academic_integrity_request(normalized)
        if integrity.requires_integrity_redirect:
            return ActionRouteV1(
                action="redirect-graded-work",
                reason=(
                    "The request identifies assessed work and asks for a "
                    "submission-ready completion."
                ),
                matched_rule="structured-request-intent-v3",
            )
        if _DEICTIC_ACTION_QUESTION.search(normalized) or _UNRESOLVED_REFERENCE_V2.search(
            normalized
        ):
            return ActionRouteV1(
                action="clarify",
                reason="The request does not identify the concept or alternative to address.",
                matched_rule="explicit-referent-required-v3",
            )
        if _CROSS_COURSE.search(normalized) or _CROSS_SCOPE_V2.search(normalized):
            return ActionRouteV1(
                action="no-evidence",
                reason="The request explicitly targets material outside the active course.",
                matched_rule="active-course-only-v3",
            )
        if _UNSUPPORTED_FUTURE.search(normalized) or _UNAVAILABLE_SOURCE_V2.search(
            normalized
        ):
            return ActionRouteV1(
                action="no-evidence",
                reason="The requested source state is not current and authorized.",
                matched_rule="current-authorized-evidence-only-v3",
            )
        return None


def requires_clarification(question: str) -> bool:
    route = DeterministicActionRouterV1().route(question)
    return route is not None and route.action == "clarify"


def deterministic_boundary_action(question: str) -> str | None:
    route = DeterministicActionRouterV1().route(question)
    if route is None:
        return None
    return {
        "redirect-graded-work": "refuse",
        "clarify": "clarify",
        "no-evidence": "abstain",
    }[route.action]


def required_atomic_claim_count(question: str) -> int:
    """Return the bounded claim count implied by the public question only."""

    return 2 if _EXPLICIT_MULTI_EVIDENCE.search(question) else 1
