"""Deterministic assembly for source-aligned evaluation questions.

Models may propose wording and provide advisory semantic reviews.  They cannot
change the case action, canonical answer, claims, citations, or source lineage.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.factual_qa_reference_questions import (
    ReferenceQuestionAuthorResponseV1,
    ReferenceQuestionReviewerResponseV1,
)
from src.digital_twin.evaluation.factual_qa_references import SourceClusterV2
from src.digital_twin.grounding.source_registration import semantic_anchors


AUTHOR_FAMILY = "openai-gpt-5.4-nano-source-visible-author-v1"
FALLBACK_FAMILY = "deterministic-context-complete-fallback-v1"


def _contains_sequence(*, needle: str, haystack: str) -> bool:
    expected = normalize_question(needle).split()
    observed = normalize_question(haystack).split()
    return bool(expected) and any(
        observed[index : index + len(expected)] == expected
        for index in range(len(observed) - len(expected) + 1)
    )


def _anchor_coverage(*, base_question: str, candidate: str) -> tuple[int, int]:
    anchors = semantic_anchors((base_question,), limit=4)
    required = min(2, len(anchors))
    candidate_tokens = set(normalize_question(candidate).split())
    observed = sum(
        normalize_question(anchor) in candidate_tokens for anchor in anchors
    )
    return observed, required


def context_complete_fallback(
    *,
    case: EvaluationCaseV1,
    cluster: SourceClusterV2,
    forbidden_answer: str | None = None,
) -> str:
    """Return a unique, source-visible fallback without altering case truth."""

    source_name = cluster.source_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    source_name = source_name.replace("_", " ").replace("-", " ")
    anchors = semantic_anchors((cluster.text,), limit=12)
    forbidden_tokens = set(normalize_question(forbidden_answer or "").split())
    anchors = [
        anchor
        for anchor in anchors
        if normalize_question(anchor) not in forbidden_tokens
    ][:6]
    context = ", ".join(anchors) or cluster.section_heading
    base = " ".join(case.question.rstrip("?.! ").split())
    lowered = base[:1].lower() + base[1:]
    return (
        f'In the {case.course_id.replace("-", " ")} source '
        f'"{source_name}: {cluster.section_heading}" concerning {context}, '
        f"{lowered}?"
    )


def _review_passes(
    *,
    case: EvaluationCaseV1,
    gold: EvaluationGoldV1,
    authored: ReferenceQuestionAuthorResponseV1,
    reviewed: ReferenceQuestionReviewerResponseV1,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    expected_spans = [normalize_question(row.answer_span) for row in gold.claims]
    recovered = [normalize_question(row) for row in reviewed.recovered_answer_spans]
    if reviewed.predicted_action != gold.expected_action:
        reasons.append("review-action-mismatch")
    if gold.expected_action == EvaluationAction.ANSWER:
        if recovered != expected_spans:
            reasons.append("review-answer-span-mismatch")
    elif recovered:
        reasons.append("review-boundary-returned-spans")
    if not reviewed.unambiguous:
        reasons.append("review-ambiguous")
    if not reviewed.natural_student_question:
        reasons.append("review-unnatural")
    if reviewed.gold_hint_leak:
        reasons.append("review-gold-hint")
    if gold.expected_action == EvaluationAction.ANSWER and _contains_sequence(
        needle=gold.canonical_answer,
        haystack=authored.question,
    ):
        reasons.append("deterministic-canonical-answer-leak")
    observed, required = _anchor_coverage(
        base_question=case.question,
        candidate=authored.question,
    )
    if observed < required:
        reasons.append("deterministic-anchor-loss")
    return not reasons, reasons


def assemble_source_aligned_wording(
    *,
    cases: list[EvaluationCaseV1],
    gold: list[EvaluationGoldV1],
    clusters: list[SourceClusterV2],
    authors: list[ReferenceQuestionAuthorResponseV1],
    reviewers: list[ReferenceQuestionReviewerResponseV1],
) -> dict[str, Any]:
    """Select reviewed wording or a deterministic fallback for every case."""

    case_by_id = {row.case_id: row for row in cases}
    gold_by_id = {row.case_id: row for row in gold}
    cluster_by_id = {row.cluster_id: row for row in clusters}
    author_by_id = {row.case_id: row for row in authors}
    reviewer_by_id = {row.case_id: row for row in reviewers}
    if len(case_by_id) != len(cases) or len(gold_by_id) != len(gold):
        raise ValueError("source-aligned cases or gold contain duplicate IDs")
    if set(case_by_id) != set(gold_by_id):
        raise ValueError("source-aligned public and gold IDs differ")
    if any(row.cluster_id not in cluster_by_id for row in cases):
        raise ValueError("source-aligned case references an unknown cluster")

    preliminary: dict[str, tuple[str, str, list[str]]] = {}
    for case_id in sorted(case_by_id):
        case = case_by_id[case_id]
        authored = author_by_id.get(case_id)
        reviewed = reviewer_by_id.get(case_id)
        reasons: list[str] = []
        if authored is None:
            reasons.append("author-output-unavailable")
        if reviewed is None:
            reasons.append("review-output-unavailable")
        if authored is not None and reviewed is not None:
            passed, review_reasons = _review_passes(
                case=case,
                gold=gold_by_id[case_id],
                authored=authored,
                reviewed=reviewed,
            )
            reasons.extend(review_reasons)
            if passed:
                preliminary[case_id] = (authored.question, AUTHOR_FAMILY, [])
                continue
        fallback = context_complete_fallback(
            case=case,
            cluster=cluster_by_id[case.cluster_id],
            forbidden_answer=gold_by_id[case_id].canonical_answer,
        )
        preliminary[case_id] = (fallback, FALLBACK_FAMILY, reasons)

    normalized = [normalize_question(row[0]) for row in preliminary.values()]
    duplicate_values = {
        value for value, count in Counter(normalized).items() if count > 1
    }
    if duplicate_values:
        for case_id, (question, family, reasons) in list(preliminary.items()):
            if normalize_question(question) not in duplicate_values:
                continue
            case = case_by_id[case_id]
            fallback = context_complete_fallback(
                case=case,
                cluster=cluster_by_id[case.cluster_id],
                forbidden_answer=gold_by_id[case_id].canonical_answer,
            )
            preliminary[case_id] = (
                fallback,
                FALLBACK_FAMILY,
                [*reasons, "normalized-candidate-duplicate"],
            )

    final_normalized = [normalize_question(row[0]) for row in preliminary.values()]
    if len(final_normalized) != len(set(final_normalized)):
        raise ValueError("deterministic source-aligned fallbacks are not unique")

    output_cases: list[EvaluationCaseV1] = []
    decisions: list[dict[str, Any]] = []
    fallback_count = 0
    for case_id in sorted(case_by_id):
        question, family, reasons = preliminary[case_id]
        case = case_by_id[case_id]
        reference = gold_by_id[case_id]
        if not question.endswith("?"):
            raise ValueError("assembled source-aligned question is not interrogative")
        if reference.expected_action == EvaluationAction.ANSWER and _contains_sequence(
            needle=reference.canonical_answer,
            haystack=question,
        ):
            raise ValueError("assembled source-aligned question leaks its answer")
        fallback = family == FALLBACK_FAMILY
        fallback_count += int(fallback)
        output_cases.append(
            case.model_copy(update={"question": question, "author_family": family})
        )
        decisions.append(
            {
                "case_id": case_id,
                "wording_provenance": family,
                "used_fallback": fallback,
                "advisory_rejection_reasons": sorted(set(reasons)),
            }
        )
    return {
        "status": "completed-go-deeper",
        "case_count": len(output_cases),
        "model_wording_count": len(output_cases) - fallback_count,
        "fallback_wording_count": fallback_count,
        "normalized_duplicate_count": 0,
        "cases": [row.model_dump(mode="json") for row in output_cases],
        "decisions": decisions,
    }


__all__ = [
    "AUTHOR_FAMILY",
    "FALLBACK_FAMILY",
    "assemble_source_aligned_wording",
    "context_complete_fallback",
]
