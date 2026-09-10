"""Bounded student-authored retrieval context, with explicit episode boundaries."""
import re

from src.digital_twin.action_router import DeterministicActionRouterV3
from src.digital_twin.student.models import Message


def continuation_question(current: str, messages: list[Message], labels: tuple[str, ...]) -> Message | None:
    """Reuse one prior student question only for an explicit continuation.

    Tutor prose is never used as an evidence query. This is a conservative
    heuristic baseline, not a semantic reference resolver.
    """
    router = DeterministicActionRouterV3()
    if router.route_without_reference_clarification(current) is not None:
        return None
    if not re.search(r"^(?:my (?:attempt|answer)\b|so\b|then\b|i (?:think|believe)\b|because\b|what about\b|why\b|how does that\b|can you (?:explain|clarify)\b)", current.strip(), re.I):
        return None
    # Exactly the last completed exchange; never search across an intervening
    # change of topic or a refused/private/graded exchange.
    if len(messages) < 2 or messages[-1].role != "tutor" or messages[-2].role != "student":
        return None
    previous, tutor = messages[-2], messages[-1]
    if tutor.action not in {"answer", "question"}:
        return None
    if router.route_without_reference_clarification(previous.content) is not None:
        return None
    def mentioned(text):
        folded = " " + " ".join(re.findall(r"\w+", text.casefold())) + " "
        return {label for label in labels if " " + " ".join(re.findall(r"\w+", label.casefold())) + " " in folded}
    named_now, named_before = mentioned(current), mentioned(previous.content)
    if named_now and not named_now.issubset(named_before):
        return None
    return previous
