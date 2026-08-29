"""Independent validation for source-linked factual-QA questions.

Question authors may see the source and deterministic target while reviewers
must recover the action and answer spans from the source without seeing that
target.  Deterministic comparison remains the decision authority.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question


class ReferenceQuestionAuthorResponseV1(BaseModel):
    """One source-visible question proposed by the author model."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    question: str = Field(min_length=12, max_length=500)

    @field_validator("question")
    @classmethod
    def question_must_be_interrogative(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized.endswith("?"):
            raise ValueError("reference question must end with a question mark")
        return normalized


class ReferenceQuestionReviewerResponseV1(BaseModel):
    """A blind answer-recovery judgment over one proposed question."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    predicted_action: EvaluationAction
    recovered_answer_spans: list[str] = Field(max_length=2)
    unambiguous: bool
    natural_student_question: bool
    gold_hint_leak: bool
    rationale: str = Field(min_length=1, max_length=400)

    @field_validator("recovered_answer_spans")
    @classmethod
    def spans_must_be_nonempty(cls, value: list[str]) -> list[str]:
        output = [" ".join(row.split()) for row in value]
        if any(not row for row in output):
            raise ValueError("recovered answer spans cannot be empty")
        return output


def _normalized_sequence(*, needle: str, haystack: str) -> bool:
    expected = normalize_question(needle).split()
    observed = normalize_question(haystack).split()
    return bool(expected) and any(
        observed[index : index + len(expected)] == expected
        for index in range(len(observed) - len(expected) + 1)
    )


def score_reference_questions(
    *,
    base_cases: list[EvaluationCaseV1],
    gold: list[EvaluationGoldV1],
    cluster_modalities: dict[str, str],
    authors: list[ReferenceQuestionAuthorResponseV1],
    reviewers: list[ReferenceQuestionReviewerResponseV1],
    target_allocation: dict[str, dict[str, int]],
) -> dict[str, Any]:
    """Validate every case and select complete clusters prospectively.

    Selection is deterministic by cluster ID.  A cluster is eligible only when
    all five questions pass, and course/modality quotas are never relaxed.
    """

    case_by_id = {row.case_id: row for row in base_cases}
    gold_by_id = {row.case_id: row for row in gold}
    author_by_id = {row.case_id: row for row in authors}
    reviewer_by_id = {row.case_id: row for row in reviewers}
    expected_ids = set(case_by_id)
    if not (
        len(case_by_id)
        == len(gold_by_id)
        == len(author_by_id)
        == len(reviewer_by_id)
        == len(expected_ids)
    ):
        raise ValueError("reference-question identities are duplicated or incomplete")
    if set(gold_by_id) != expected_ids:
        raise ValueError("reference-question public and gold identities differ")
    if set(author_by_id) != expected_ids or set(reviewer_by_id) != expected_ids:
        raise ValueError("reference-question model coverage is incomplete")

    normalized_questions = [
        normalize_question(author_by_id[case_id].question)
        for case_id in sorted(expected_ids)
    ]
    duplicate_counts = Counter(normalized_questions)
    duplicate_questions = {
        value for value, count in duplicate_counts.items() if count > 1
    }

    decisions: list[dict[str, Any]] = []
    accepted_by_cluster: dict[str, bool] = {}
    output_cases: dict[str, EvaluationCaseV1] = {}
    for case_id in sorted(expected_ids):
        case = case_by_id[case_id]
        expected = gold_by_id[case_id]
        authored = author_by_id[case_id]
        reviewed = reviewer_by_id[case_id]
        expected_spans = [row.answer_span for row in expected.claims]
        recovered_spans = reviewed.recovered_answer_spans
        action_match = reviewed.predicted_action == expected.expected_action
        span_match = (
            [normalize_question(row) for row in recovered_spans]
            == [normalize_question(row) for row in expected_spans]
        )
        if expected.expected_action != EvaluationAction.ANSWER:
            span_match = recovered_spans == []
        canonical_leak = (
            expected.expected_action == EvaluationAction.ANSWER
            and _normalized_sequence(
                needle=expected.canonical_answer,
                haystack=authored.question,
            )
        )
        exact_duplicate = normalize_question(authored.question) in duplicate_questions
        passed = all(
            (
                action_match,
                span_match,
                reviewed.unambiguous,
                reviewed.natural_student_question,
                not reviewed.gold_hint_leak,
                not canonical_leak,
                not exact_duplicate,
            )
        )
        reasons = []
        if not action_match:
            reasons.append("action-mismatch")
        if not span_match:
            reasons.append("answer-span-mismatch")
        if not reviewed.unambiguous:
            reasons.append("ambiguous")
        if not reviewed.natural_student_question:
            reasons.append("unnatural")
        if reviewed.gold_hint_leak or canonical_leak:
            reasons.append("gold-hint-leak")
        if exact_duplicate:
            reasons.append("exact-duplicate")
        decisions.append(
            {
                "case_id": case_id,
                "cluster_id": case.cluster_id,
                "passed": passed,
                "reasons": reasons,
            }
        )
        accepted_by_cluster[case.cluster_id] = (
            accepted_by_cluster.get(case.cluster_id, True) and passed
        )
        output_cases[case_id] = case.model_copy(
            update={
                "question": authored.question,
                "author_family": "openai-gpt-5.4-mini-source-visible-author-v1",
            }
        )

    selected_clusters: list[str] = []
    shortfalls: dict[str, int] = {}
    cluster_to_case: dict[str, EvaluationCaseV1] = {}
    for row in sorted(base_cases, key=lambda value: value.case_id):
        cluster_to_case.setdefault(row.cluster_id, row)
    for course_id in sorted(target_allocation):
        for modality in sorted(target_allocation[course_id]):
            required = target_allocation[course_id][modality]
            eligible = [
                cluster_id
                for cluster_id in sorted(accepted_by_cluster)
                if accepted_by_cluster[cluster_id]
                and cluster_to_case[cluster_id].course_id == course_id
                and cluster_modalities[cluster_id] == modality
            ]
            selected_clusters.extend(eligible[:required])
            if len(eligible) < required:
                shortfalls[f"{course_id}:{modality}"] = required - len(eligible)

    selected_set = set(selected_clusters)
    selected_cases = [
        output_cases[case_id]
        for case_id in sorted(output_cases)
        if output_cases[case_id].cluster_id in selected_set
    ]
    selected_gold = [
        gold_by_id[case_id]
        for case_id in sorted(gold_by_id)
        if case_by_id[case_id].cluster_id in selected_set
    ]
    passed_case_count = sum(row["passed"] for row in decisions)
    passed_cluster_count = sum(accepted_by_cluster.values())
    status = (
        "completed-go-deeper"
        if not shortfalls
        and len(selected_clusters) == 100
        and len(selected_cases) == 500
        and len(selected_gold) == 500
        else "completed-refine"
    )
    return {
        "status": status,
        "candidate_case_count": len(base_cases),
        "candidate_cluster_count": len(accepted_by_cluster),
        "passed_case_count": passed_case_count,
        "failed_case_count": len(base_cases) - passed_case_count,
        "passed_cluster_count": passed_cluster_count,
        "selected_cluster_count": len(selected_clusters),
        "selected_case_count": len(selected_cases),
        "normalized_duplicate_count": len(duplicate_questions),
        "allocation_shortfalls": shortfalls,
        "decisions": decisions,
        "selected_cases": [row.model_dump(mode="json") for row in selected_cases],
        "selected_gold": [row.model_dump(mode="json") for row in selected_gold],
    }
