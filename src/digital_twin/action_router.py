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
