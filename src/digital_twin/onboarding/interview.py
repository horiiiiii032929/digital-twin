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
