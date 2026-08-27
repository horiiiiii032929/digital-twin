"""Provider-neutral question-wording boundary for factual-QA datasets."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question


class QuestionWordingRequestV1(BaseModel):
    """The only data a wording provider may receive."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    slice: str = Field(min_length=1)
    canonical_question: str = Field(min_length=1, max_length=500)


class QuestionWordingResponseV1(BaseModel):
    """A provider may return wording only—never truth or citations."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=500)


class QuestionWordingDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(?:accepted-model-wording|canonical-fallback)$")
    reason: str = Field(min_length=1)


@runtime_checkable
class QuestionWordingProviderV1(Protocol):
    provider_id: str
    model_id: str

    async def generate(
        self,
        requests: list[QuestionWordingRequestV1],
    ) -> list[QuestionWordingResponseV1]: ...


def wording_requests(cases: list[EvaluationCaseV1]) -> list[QuestionWordingRequestV1]:
    return [
        QuestionWordingRequestV1(
            case_id=row.case_id,
            course_id=row.course_id,
            slice=row.slice,
            canonical_question=row.question,
        )
        for row in cases
    ]


def _contains_token_sequence(needle: str, haystack: str) -> bool:
    expected = normalize_question(needle).split()
    observed = normalize_question(haystack).split()
    if not expected:
        return False
    return any(
        observed[index : index + len(expected)] == expected
        for index in range(len(observed) - len(expected) + 1)
    )


def apply_wording_responses(
    *,
    cases: list[EvaluationCaseV1],
    gold: list[EvaluationGoldV1],
    responses: list[QuestionWordingResponseV1],
) -> tuple[list[EvaluationCaseV1], list[QuestionWordingDecisionV1]]:
    """Apply safe wording variants while keeping all authoritative fields fixed."""

    gold_by_id = {row.case_id: row for row in gold}
    response_by_id: dict[str, QuestionWordingResponseV1] = {}
    duplicate_response_ids: set[str] = set()
    for row in responses:
        if row.case_id in response_by_id:
            duplicate_response_ids.add(row.case_id)
        response_by_id[row.case_id] = row

    accepted_questions: set[str] = set()
    output: list[EvaluationCaseV1] = []
    decisions: list[QuestionWordingDecisionV1] = []
    for case in cases:
        response = response_by_id.get(case.case_id)
        reason = "accepted"
        candidate = response.question.strip() if response is not None else ""
        if response is None:
            reason = "response-missing"
        elif case.case_id in duplicate_response_ids:
            reason = "response-id-duplicated"
        elif case.case_id not in gold_by_id:
            reason = "hidden-gold-identity-missing"
        elif _contains_token_sequence(
            gold_by_id[case.case_id].canonical_answer,
            candidate,
        ):
            reason = "canonical-answer-leak"
        elif normalize_question(candidate) in accepted_questions:
            reason = "normalized-question-duplicate"

        if reason == "accepted":
            selected = candidate
            status = "accepted-model-wording"
        else:
            selected = case.question
            status = "canonical-fallback"
        normalized = normalize_question(selected)
        if normalized in accepted_questions:
            raise ValueError("canonical fallback is not uniquely recoverable")
        accepted_questions.add(normalized)
        output.append(case.model_copy(update={"question": selected}))
        decisions.append(
            QuestionWordingDecisionV1(
                case_id=case.case_id,
                status=status,
                reason=reason,
            )
        )
    return output, decisions
