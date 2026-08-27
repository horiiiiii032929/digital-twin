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


class QuestionWordingReviewRequestV1(BaseModel):
    """Public-only comparison supplied to the independent wording reviewer."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    canonical_question: str = Field(min_length=1, max_length=500)
    candidate_question: str = Field(min_length=1, max_length=500)


class QuestionWordingReviewResponseV1(BaseModel):
    """Advisory judgment that cannot alter deterministic source truth."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    accept: bool
    faithfulness: str = Field(pattern=r"^(?:faithful|meaning-shift|unclear)$")
    naturalness: str = Field(pattern=r"^(?:acceptable|awkward)$")
    rationale: str = Field(min_length=1, max_length=240)


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


def wording_review_requests(
    *,
    cases: list[EvaluationCaseV1],
    responses: list[QuestionWordingResponseV1],
) -> list[QuestionWordingReviewRequestV1]:
    """Create reviewer inputs without source text, answers, actions, or lineage."""

    case_by_id = {row.case_id: row for row in cases}
    if len(case_by_id) != len(cases):
        raise ValueError("public cases contain duplicate IDs")
    response_by_id: dict[str, QuestionWordingResponseV1] = {}
    for row in responses:
        if row.case_id in response_by_id:
            raise ValueError("wording responses contain duplicate IDs")
        if row.case_id not in case_by_id:
            raise ValueError("wording response references an unknown public case")
        response_by_id[row.case_id] = row
    if set(response_by_id) != set(case_by_id):
        raise ValueError("wording responses are incomplete")
    return [
        QuestionWordingReviewRequestV1(
            case_id=case.case_id,
            canonical_question=case.question,
            candidate_question=response_by_id[case.case_id].question,
        )
        for case in cases
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


def apply_reviewed_wording_responses(
    *,
    cases: list[EvaluationCaseV1],
    gold: list[EvaluationGoldV1],
    responses: list[QuestionWordingResponseV1],
    reviews: list[QuestionWordingReviewResponseV1],
) -> tuple[list[EvaluationCaseV1], list[QuestionWordingDecisionV1]]:
    """Apply only reviewer-accepted variants, then enforce deterministic safety."""

    review_by_id: dict[str, QuestionWordingReviewResponseV1] = {}
    duplicate_review_ids: set[str] = set()
    for row in reviews:
        if row.case_id in review_by_id:
            duplicate_review_ids.add(row.case_id)
        review_by_id[row.case_id] = row
    eligible: list[QuestionWordingResponseV1] = []
    for row in responses:
        review = review_by_id.get(row.case_id)
        if (
            review is not None
            and row.case_id not in duplicate_review_ids
            and review.accept
            and review.faithfulness == "faithful"
            and review.naturalness == "acceptable"
        ):
            eligible.append(row)
    output, decisions = apply_wording_responses(
        cases=cases,
        gold=gold,
        responses=eligible,
    )
    eligible_ids = {row.case_id for row in eligible}
    revised = [
        decision
        if decision.case_id in eligible_ids
        else decision.model_copy(update={"reason": "review-rejected-or-missing"})
        for decision in decisions
    ]
    return output, revised
