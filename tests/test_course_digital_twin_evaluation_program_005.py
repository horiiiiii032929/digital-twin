from __future__ import annotations

from pathlib import Path

from scripts import run_course_digital_twin_evaluation_program as runner
from src.digital_twin.evaluation import build_atomic_final_rows
from src.digital_twin.evaluation.finite_program import load_program_manifest
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    validate_exact_reference_matchability,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_evaluation_program_005.json"
)


def test_action_router_successor_is_frozen_and_exactly_matchable() -> None:
    manifest = load_program_manifest(INSTRUMENT)
    result = runner.validate(INSTRUMENT)

    assert manifest.program_id == "course-digital-twin-evaluation-program-005"
    assert manifest.status == "frozen-authorized"
    assert manifest.provider_execution_authorized is True
    assert manifest.paid_execution_authorized is True
    assert result["status"] == "passed-build-only"
    assert result["development_required_reference_count"] == 452
    assert result["development_missing_reference_count"] == 0


def test_action_router_successor_adapter_smoke_is_network_free() -> None:
    result = runner.smoke(INSTRUMENT)

    assert result == {
        "program_id": "course-digital-twin-evaluation-program-005",
        "status": "passed-network-free-smoke",
        "response_count": 1,
        "scored_case_count": 1,
        "provider_calls": 0,
        "network_calls": 0,
        "gold_loaded_after_response_persistence": True,
    }


def test_final_atomic_corpus_is_non_overlapping_and_exactly_matchable() -> None:
    cases, gold, diagnostics, source = build_atomic_final_rows(
        ROOT / "data/processed/academic_factual_qa_open_10000_v1_sources.json",
        program_id="course-digital-twin-evaluation-program-005",
    )
    chunks_by_course, _ = _chunks_by_course_from_payload(source)
    chunks = [chunk for rows in chunks_by_course.values() for chunk in rows]
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


def _chunks_by_course_from_payload(source: dict):
    from src.digital_twin.grounding import DocumentChunk

    grouped: dict[str, list[DocumentChunk]] = {}
    by_id: dict[str, DocumentChunk] = {}
    for row in source["chunks"]:
        chunk = DocumentChunk.model_validate(row)
        grouped.setdefault(chunk.metadata["course_id"], []).append(chunk)
        by_id[chunk.id] = chunk
    return grouped, by_id
