from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_academic_factual_qa_atomic_m2_confirmation as runner
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit


def _hit(identifier: str, text: str, score: float) -> RetrievalHit:
    return RetrievalHit(
        chunk=DocumentChunk(
            id=identifier,
            document_id="source",
            text=text,
            ordinal=int(identifier[-1]),
            retrieval_allowed=True,
            display_allowed=True,
            metadata={"search_description": text},
        ),
        relevance_score=score,
    )


def test_coverage_selector_prefers_complementary_question_concepts() -> None:
    candidates = [
        _hit("chunk-1", "TCP congestion window", 1.0),
        _hit("chunk-2", "TCP congestion control", 0.95),
        _hit("chunk-3", "additive increase multiplicative decrease", 0.90),
        _hit("chunk-4", "network routing", 0.85),
    ]

    selected = runner._coverage_select(
        "How does TCP use additive increase and multiplicative decrease for congestion?",
        candidates,
        output_limit=3,
        coverage_limit=2,
    )

    assert [row.chunk.id for row in selected[:2]] == ["chunk-3", "chunk-1"]


def test_atomic_m2_selection_prefers_passing_control() -> None:
    passing = {"method_id": "M2", "passed": True}
    candidate = {"method_id": "M2C", "passed": True}

    assert runner._selected([passing, candidate]) == "M2"
    assert runner._selected([{**passing, "passed": False}, candidate]) == "M2C"
    assert runner._selected(
        [{**passing, "passed": False}, {**candidate, "passed": False}]
    ) is None


def test_atomic_m2_preflight_never_loads_hidden_gold(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    instrument = {
        "metadata": {
            "verified_at": "2026-08-30T18:00:00+08:00",
            "freshness_hours": 24,
        }
    }
    chunks = [object()] * 300
    cases = [object()] * 500
    monkeypatch.setattr(runner, "_instrument", lambda: instrument)
    monkeypatch.setattr(
        runner,
        "_validate_public",
        lambda _: ({}, {}, chunks, cases),
    )
    monkeypatch.setattr(runner, "_git_dirty", lambda: False)
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path / "unused-output")
    monkeypatch.setattr(runner, "RESULT_PATH", tmp_path / "unused-result.json")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-present")

    result = runner.preflight()

    assert result["authority_blockers"] == []
    assert result["hidden_gold_opened"] is False


def test_atomic_m2_hidden_gold_requires_durable_rankings(tmp_path: Path) -> None:
    with pytest.raises(
        runner.AtomicM2ConfirmationError,
        match="before public rankings are durable",
    ):
        runner._open_hidden_gold(
            {"hidden_gold": {}},
            rankings_path=tmp_path / "missing.json",
            source_sha256="synthetic",
            expected_case_ids=set(),
        )
