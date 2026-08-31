"""Deterministic pre-generation routing for release-critical boundaries."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


RoutedAction = Literal["clarify", "no-evidence", "redirect-graded-work"]


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


@dataclass(frozen=True)
class ActionRouteV1:
    """One inspectable boundary decision made before retrieval-backed generation."""

    action: RoutedAction
    reason: str
    matched_rule: str


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
