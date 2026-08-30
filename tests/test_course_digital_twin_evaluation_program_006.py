from __future__ import annotations

from pathlib import Path

from scripts import run_course_digital_twin_evaluation_program as runner
from scripts.course_digital_twin_program_factual import (
    select_descriptive_retrieval_candidate,
)
from scripts.academic_factual_qa_open_10000_t0_adapter import (
    LiveT0AdapterError,
    _ManagedAdapter,
)
from src.digital_twin.evaluation import build_atomic_final_rows
from src.digital_twin.evaluation.finite_program import load_program_manifest
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    RetrievalMethodSummary,
    validate_exact_reference_matchability,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_006 = ROOT / (
    "research/05_evaluation/instruments/course_digital_twin_evaluation_program_006.json"
)
INSTRUMENT_007 = ROOT / (
    "research/05_evaluation/instruments/course_digital_twin_evaluation_program_007.json"
)
INSTRUMENT_008 = ROOT / (
    "research/05_evaluation/instruments/course_digital_twin_evaluation_program_008.json"
)
INSTRUMENT_009 = ROOT / (
    "research/05_evaluation/instruments/course_digital_twin_evaluation_program_009.json"
)
INSTRUMENT_010 = ROOT / (
    "research/05_evaluation/instruments/course_digital_twin_evaluation_program_010.json"
)


def test_program_006_is_terminal_and_preserved() -> None:
    manifest = load_program_manifest(INSTRUMENT_006)
    result = runner.validate(INSTRUMENT_006)

    assert manifest.program_id == "course-digital-twin-evaluation-program-006"
    assert manifest.status == "terminated"
    assert manifest.provider_execution_authorized is False
    assert manifest.paid_execution_authorized is False
    assert result["status"] == "passed-build-only"


def test_question_targeted_successor_is_completed_and_exactly_matchable() -> None:
    manifest = load_program_manifest(INSTRUMENT_007)
    result = runner.validate(INSTRUMENT_007)

    assert manifest.program_id == "course-digital-twin-evaluation-program-007"
    assert manifest.status == "completed"
    assert manifest.provider_execution_authorized is False
    assert manifest.paid_execution_authorized is False
    assert (
        manifest.product_candidate_generator
        == "openai-gpt-5.4-question-targeted-extraction-v2"
    )
    assert manifest.product_candidate_evidence_gate == "any-hit-evidence-gate-v1"
    assert (
        manifest.product_candidate_model_role == "independent-question-action-verifier"
    )
    assert result["status"] == "passed-build-only"
    assert result["development_required_reference_count"] == 452
    assert result["development_missing_reference_count"] == 0


def test_question_targeted_successor_adapter_smoke_is_network_free() -> None:
    result = runner.smoke(INSTRUMENT_007)

    assert result == {
        "program_id": "course-digital-twin-evaluation-program-007",
        "status": "passed-network-free-smoke",
        "response_count": 1,
        "scored_case_count": 1,
        "provider_calls": 0,
        "network_calls": 0,
        "gold_loaded_after_response_persistence": True,
    }


def test_question_stratified_program_008_is_completed_and_exactly_matchable() -> None:
    manifest = load_program_manifest(INSTRUMENT_008)
    result = runner.validate(INSTRUMENT_008)

    assert manifest.program_id == "course-digital-twin-evaluation-program-008"
    assert manifest.status == "completed"
    assert manifest.provider_execution_authorized is False
    assert manifest.paid_execution_authorized is False
    assert "reference_aggregate_007_cases" in manifest.development_cases_path
    assert result["status"] == "passed-build-only"
    assert result["development_required_reference_count"] == 450
    assert result["development_missing_reference_count"] == 0


def test_question_stratified_program_008_adapter_smoke_is_network_free() -> None:
    result = runner.smoke(INSTRUMENT_008)

    assert result == {
        "program_id": "course-digital-twin-evaluation-program-008",
        "status": "passed-network-free-smoke",
        "response_count": 1,
        "scored_case_count": 1,
        "provider_calls": 0,
        "network_calls": 0,
        "gold_loaded_after_response_persistence": True,
    }


def test_program_009_freezes_descriptive_continuation_without_claiming_keep() -> None:
    manifest = load_program_manifest(INSTRUMENT_009)
    result = runner.validate(INSTRUMENT_009)

    assert manifest.program_id == "course-digital-twin-evaluation-program-009"
    assert manifest.status == "terminated"
    assert manifest.provider_execution_authorized is False
    assert manifest.paid_execution_authorized is False
    assert manifest.descriptive_factual_continuation is True
    assert manifest.total_budget_usd == 49.95
    assert all(row.independent_after_factual_failure for row in manifest.stages)
    assert result["status"] == "passed-build-only"
    assert result["development_missing_reference_count"] == 0


def test_program_010_corrects_bulk_cost_and_latency_without_changing_truth() -> None:
    manifest = load_program_manifest(INSTRUMENT_010)
    result = runner.validate(INSTRUMENT_010)

    assert manifest.program_id == "course-digital-twin-evaluation-program-010"
    assert manifest.status == "frozen-authorized"
    assert manifest.total_budget_usd == 47.3
    assert manifest.final_construction_verifier_role == "product-answer-generator"
    assert manifest.provider_concurrency == 4
    assert manifest.descriptive_factual_continuation is True
    assert result["status"] == "passed-build-only"
    assert result["development_missing_reference_count"] == 0


def test_descriptive_continuation_uses_best_observed_retriever() -> None:
    def summary(
        method_id: str,
        *,
        complete: float,
        recall: float,
    ) -> RetrievalMethodSummary:
        return RetrievalMethodSummary(
            method_id=method_id,
            case_count=100,
            complete_evidence_at_3=complete,
            evidence_recall_at_5=recall,
            boundary_accuracy=1.0,
            severe_release_count=0,
            course_violation_count=0,
            source_version_violation_count=0,
            latency_p95_ms=10.0,
            reranked_case_count=0,
            passed=False,
        )

    selected = select_descriptive_retrieval_candidate(
        [
            summary("bm25-v1", complete=0.84, recall=0.90),
            summary("openai-small-hybrid-v2", complete=0.8974, recall=0.9551),
            summary("hierarchical-deterministic-v1", complete=0.71, recall=0.86),
        ]
    )

    assert selected is not None
    assert selected.method_id == "openai-small-hybrid-v2"


def test_evaluation_v2_scores_per_case_provider_failures() -> None:
    class _Ledger:
        @staticmethod
        def snapshot() -> dict[str, int | str]:
            return {"status": "running", "failed_calls": 3}

    adapter = object.__new__(_ManagedAdapter)
    adapter.provider_ledger = _Ledger()
    adapter.maximum_quarantined_failures = None

    adapter.validate_completion()

    adapter.maximum_quarantined_failures = 1
    try:
        adapter.validate_completion()
    except LiveT0AdapterError:
        pass
    else:
        raise AssertionError("legacy strict mode must still reject excess failures")


def test_final_atomic_corpus_is_non_overlapping_and_exactly_matchable() -> None:
    cases, gold, diagnostics, source = build_atomic_final_rows(
        ROOT / "data/processed/academic_factual_qa_open_10000_v1_sources.json",
        program_id="course-digital-twin-evaluation-program-007",
    )
    chunks = [_chunk_from_row(row) for row in source["chunks"]]
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)
    by_source: dict[tuple[str, int, str], list[tuple[int, int]]] = {}
    for chunk in chunks:
        key = (
            str(chunk.source_artifact_id),
            chunk.source_version,
            str(chunk.source_checksum),
        )
        by_source.setdefault(key, []).append(
            (int(chunk.metadata["char_start"]), int(chunk.metadata["char_end"]))
        )
    for rows in by_source.values():
        ordered = sorted(rows)
        assert all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:]))

    assert len(cases) == len(gold) == 10_000
    assert diagnostics["registered_region_count"] == len(chunks)
    assert diagnostics["merged_overlap_count"] > 0
    assert matchability["missing_reference_count"] == 0


def _chunk_from_row(row: dict):
    from src.digital_twin.grounding import DocumentChunk

    return DocumentChunk.model_validate(row)
