from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_academic_factual_qa_source_aligned_retrieval as runner


def test_source_aligned_retrieval_validates_exact_matchability() -> None:
    result = runner.validate()

    assert result["status"] == "passed-build-only"
    assert result["case_count"] == 500
    assert result["answerable_count"] == 400
    assert result["boundary_count"] == 100
    assert result["registered_region_count"] == 350
    assert result["matchability"] == {
        "required_reference_count": 450,
        "matched_reference_count": 450,
        "missing_reference_count": 0,
    }
    assert result["automatic_progression_on_pass"] is True


def test_source_aligned_retrieval_simulations_are_terminal() -> None:
    passed = runner.simulate("pass")
    failed = runner.simulate("quality-failure")

    assert passed["status"] == "completed-keep"
    assert passed["selected_method"] == "M2"
    assert failed["status"] == "completed-refine"
    assert failed["selected_method"] == "none"
    assert passed["provider_calls"] == failed["provider_calls"] == 0


def test_source_aligned_retrieval_selects_simplest_near_best() -> None:
    summaries = [
        {
            "method_id": method_id,
            "complete_evidence_at_3": complete,
            "evidence_recall_at_5": recall,
            "latency_p95_ms": latency,
            "passed": passed,
        }
        for method_id, complete, recall, latency, passed in (
            ("M0", 0.89, 0.99, 1.0, False),
            ("M1", 0.951, 0.96, 10.0, True),
            ("M2", 0.95, 0.98, 20.0, True),
            ("M3", 0.96, 0.99, 15.0, True),
            ("M4", 0.90, 0.95, 15.0, True),
            ("M5", 0.97, 0.99, 30.0, True),
        )
    ]

    assert runner._select(summaries) == "M1"


def test_source_aligned_retrieval_preflight_never_requests_stage_approval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-present")
    monkeypatch.setattr(runner, "_git_dirty", lambda: False)
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path / "unused-output")
    monkeypatch.setattr(runner, "RESULT_PATH", tmp_path / "unused-result.json")

    result = runner.preflight()

    assert result["status"] == "ready"
    assert result["technical_blockers"] == []
    assert result["authority_blockers"] == []
    assert result["model_or_provider_called"] is False
    assert result["hidden_gold_opened"] is False


def test_source_aligned_retrieval_preflight_does_not_load_hidden_gold(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = runner._verify_package

    def reject_gold(binding: dict[str, object], *, rows_key: str):
        if rows_key == "gold":
            raise AssertionError("preflight must not load hidden gold")
        return original(binding, rows_key=rows_key)

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-present")
    monkeypatch.setattr(runner, "_verify_package", reject_gold)
    monkeypatch.setattr(runner, "_git_dirty", lambda: False)
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path / "unused-output")
    monkeypatch.setattr(runner, "RESULT_PATH", tmp_path / "unused-result.json")

    assert runner.preflight()["status"] == "ready"


def test_hidden_gold_cannot_open_before_rankings_are_durable(
    tmp_path: Path,
) -> None:
    instrument = runner._instrument()

    with pytest.raises(
        runner.SourceAlignedRetrievalError,
        match="before public rankings are durable",
    ):
        runner._open_hidden_gold_after_rankings(
            instrument,
            public_rankings_path=tmp_path / "missing-rankings.json",
            expected_case_ids=set(),
            source_sha256="synthetic",
        )
