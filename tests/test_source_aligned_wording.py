from __future__ import annotations

import json
from pathlib import Path

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.factual_qa_reference_questions import (
    ReferenceQuestionAuthorResponseV1,
    ReferenceQuestionReviewerResponseV1,
)
from src.digital_twin.evaluation.factual_qa_references import SourceClusterV2
from src.digital_twin.evaluation.source_aligned_wording import (
    FALLBACK_FAMILY,
    assemble_source_aligned_wording,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"


def _rows() -> tuple[
    list[EvaluationCaseV1],
    list[EvaluationGoldV1],
    list[SourceClusterV2],
]:
    cases = json.loads(
        (DATASET_ROOT / "academic-factual-qa-source-aligned-confirmation-001-cases.json")
        .read_text(encoding="utf-8")
    )
    gold = json.loads(
        (DATASET_ROOT / "academic-factual-qa-source-aligned-confirmation-001-gold.json")
        .read_text(encoding="utf-8")
    )
    sources = json.loads(
        (DATASET_ROOT / "academic-factual-qa-source-aligned-confirmation-001-sources.json")
        .read_text(encoding="utf-8")
    )
    return (
        [EvaluationCaseV1.model_validate(row) for row in cases["cases"]],
        [EvaluationGoldV1.model_validate(row) for row in gold["gold"]],
        [SourceClusterV2.model_validate(row) for row in sources["clusters"]],
    )


def test_deterministic_fallbacks_are_complete_unique_and_truth_preserving() -> None:
    cases, gold, clusters = _rows()
    result = assemble_source_aligned_wording(
        cases=cases,
        gold=gold,
        clusters=clusters,
        authors=[],
        reviewers=[],
    )

    assert result["status"] == "completed-go-deeper"
    assert result["case_count"] == 500
    assert result["fallback_wording_count"] == 500
    questions = [row["question"] for row in result["cases"]]
    assert len({normalize_question(row) for row in questions}) == 500
    assert all(row.endswith("?") for row in questions)
    assert {row["author_family"] for row in result["cases"]} == {FALLBACK_FAMILY}


def test_reviewed_model_wording_is_accepted_and_bad_wording_falls_back() -> None:
    cases, gold, clusters = _rows()
    selected_cases = cases[:2]
    selected_gold = {row.case_id: row for row in gold if row.case_id in {case.case_id for case in selected_cases}}
    authors = [
        ReferenceQuestionAuthorResponseV1(
            case_id=selected_cases[0].case_id,
            question=selected_cases[0].question,
        ),
        ReferenceQuestionAuthorResponseV1(
            case_id=selected_cases[1].case_id,
            question="What unrelated thing should happen?",
        ),
    ]
    reviewers = []
    for author in authors:
        reference = selected_gold[author.case_id]
        reviewers.append(
            ReferenceQuestionReviewerResponseV1(
                case_id=author.case_id,
                predicted_action=reference.expected_action,
                recovered_answer_spans=[row.answer_span for row in reference.claims],
                unambiguous=True,
                natural_student_question=True,
                gold_hint_leak=False,
                rationale="Synthetic exact semantic recovery.",
            )
        )
    cluster_ids = {row.cluster_id for row in selected_cases}
    result = assemble_source_aligned_wording(
        cases=selected_cases,
        gold=list(selected_gold.values()),
        clusters=[row for row in clusters if row.cluster_id in cluster_ids],
        authors=authors,
        reviewers=reviewers,
    )

    assert result["model_wording_count"] == 1
    assert result["fallback_wording_count"] == 1
    assert result["decisions"][1]["advisory_rejection_reasons"] == [
        "deterministic-anchor-loss"
    ]
