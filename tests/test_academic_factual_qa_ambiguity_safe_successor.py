from __future__ import annotations

import json
from pathlib import Path

from scripts import build_academic_factual_qa_ambiguity_safe_successor as builder
from scripts import run_academic_factual_qa_ambiguity_safe_comparison as comparison
from scripts.validate_reference_uniqueness_controls import validate as validate_controls
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.semantic_evidence_atoms import (
    SourceSemanticEvidenceAtomGateV2,
    SourceSemanticEvidenceAtomRetrieverV1,
)
from src.digital_twin.student.models import AuditEvent
from src.digital_twin.student.tutoring_graph import (
    TutoringIntent,
    retrieval_boundary_intent,
)


ROOT = Path(__file__).resolve().parents[1]


def test_planted_reference_controls_cover_all_six_classes() -> None:
    result = validate_controls()

    assert result["status"] == "passed"
    assert result["passed_count"] == 6
    assert {row["control_class"] for row in result["outcomes"]} == {
        "unique",
        "alternate-valid",
        "partial",
        "conflicting",
        "unrelated",
        "ambiguous",
    }


def test_fresh_successor_is_byte_stable_unique_and_source_disjoint() -> None:
    result = builder.build_byte_stable_packages()

    assert result["byte_stable"] is True
    assert result["case_count"] == 500
    assert result["reference_uniqueness"] == {"unique": 400}
    assert result["source_range_disjoint_from_all_prior_development"] is True
    assert result["provider_calls"] == 0


def test_comparison_is_simulated_and_blocked_after_authority_revocation() -> None:
    validated = comparison.validate(comparison.DEFAULT_INSTRUMENT)
    simulated = comparison.simulate(comparison.DEFAULT_INSTRUMENT)
    preflight = comparison.preflight(comparison.DEFAULT_INSTRUMENT)

    assert validated["planted_control_count"] == 6
    assert simulated["status"] == "passed-network-free-simulation"
    assert preflight["status"] == "blocked-not-authorized"
    assert preflight["hidden_gold_loaded"] is False

    invalid_preflight = comparison.preflight(
        ROOT
        / "research/05_evaluation/instruments/"
        "academic_factual_qa_ambiguity_safe_comparison_001.json"
    )
    assert invalid_preflight["status"] == "blocked-not-authorized"


def test_known_sixteen_ambiguous_failures_now_clarify_without_rescoring() -> None:
    source = json.loads(
        (
            ROOT
            / "research/05_evaluation/datasets/"
            "academic-factual-qa-source-semantic-atoms-successor-001-sources.json"
        ).read_text(encoding="utf-8")
    )
    cases = json.loads(
        (
            ROOT
            / "research/05_evaluation/datasets/"
            "academic-factual-qa-source-semantic-atoms-successor-001-cases.json"
        ).read_text(encoding="utf-8")
    )["cases"]
    adjudications = json.loads(
        (
            ROOT
            / "research/05_evaluation/instruments/"
            "academic_factual_qa_source_semantic_atom_failure_adjudications_001.json"
        ).read_text(encoding="utf-8")
    )["adjudications"]
    failed_ids = {row["case_id"] for row in adjudications}
    chunks_by_course: dict[str, list[DocumentChunk]] = {}
    for raw in source["chunks"]:
        chunk = DocumentChunk.model_validate(raw)
        chunks_by_course.setdefault(str(chunk.metadata["course_id"]), []).append(chunk)

    decisions = []
    for case in cases:
        if case["case_id"] not in failed_ids:
            continue
        retriever = SourceSemanticEvidenceAtomRetrieverV1(
            chunks_by_course[case["course_id"]]
        )
        decisions.append(
            SourceSemanticEvidenceAtomGateV2().assess(
                case["question"], retriever.retrieve(case["question"], limit=5)
            )
        )

    assert len(decisions) == 16
    assert all(not row.sufficient for row in decisions)
    assert all(row.recommended_action == "clarify" for row in decisions)


def test_evidence_recommendation_maps_to_product_clarification_intent() -> None:
    event = AuditEvent(
        id="event-1",
        event_type="evidence-sufficiency-assessed",
        details={"recommended_action": "clarify"},
    )

    assert retrieval_boundary_intent([event]) == TutoringIntent.CLARIFY_REQUEST


def test_comparison_reads_grounded_success_from_metric_namespace() -> None:
    score = {
        "aggregate": {
            "metrics": {"fully_grounded_factual_success": 0.9775}
        }
    }

    assert comparison._fully_grounded_success(score) == 0.9775
