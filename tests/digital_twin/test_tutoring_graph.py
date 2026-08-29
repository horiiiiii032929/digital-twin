from src.digital_twin.student.tutoring_graph import (
    DeterministicIntentSelector,
    DeterministicTurnInterpreter,
    TutoringIntent,
    initial_learner_state,
)
from src.digital_twin.student.models import Conversation


def test_ambiguous_request_clarifies_even_without_retrieved_evidence() -> None:
    conversation = Conversation(
        id="conversation-ambiguity",
        student_id="student-ambiguity",
        course_id="course-ambiguity",
        release_id="release-ambiguity",
    )
    signals = DeterministicTurnInterpreter().interpret("Explain that")

    selected = DeterministicIntentSelector().select(
        signals,
        initial_learner_state(conversation),
        [],
    )

    assert selected == TutoringIntent.CLARIFY_REQUEST
