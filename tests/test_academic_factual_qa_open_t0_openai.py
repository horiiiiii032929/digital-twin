from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_academic_factual_qa_open_10000 as runner


CASES = Path(
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_cases_002.json"
)
CANDIDATE = Path(
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_candidate_manifest_002.json"
)
HISTORICAL = Path(
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_candidate_manifest.json"
)


def _preflight(tmp_path: Path, manifest: Path) -> dict[str, object]:
    return runner.preflight(
        stage="development",
        cases_path=CASES,
        manifest_path=manifest,
        output=tmp_path / "responses.sqlite3",
        provider_ledger=tmp_path / "provider.sqlite3",
        state_path=tmp_path / "state.sqlite3",
        resume=False,
    )


def test_openai_product_manifests_pin_the_candidate_and_control() -> None:
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    control = json.loads(
        Path(
            "research/05_evaluation/instruments/"
            "academic_factual_qa_open_10000_v1_t0_openai_control_manifest_002.json"
        ).read_text(encoding="utf-8")
    )

    for manifest in (candidate, control):
        assert manifest["generator"] == "openai-gpt-5.4-mini-live-atomic"
        assert manifest["model_bindings"]["generator"] == (
            "gpt-5.4-mini-2026-03-17"
        )
        assert "deepseek" not in json.dumps(manifest).casefold()
        assert "openrouter" not in json.dumps(manifest).casefold()
    assert "structured" in candidate["evidence_gate"]
    assert "any-hit" in control["evidence_gate"]


def test_product_preflight_requires_only_openai_and_paid_authority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(runner, "_repo_dirty", lambda: False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = _preflight(tmp_path, CANDIDATE)

    assert result["status"] == "blocked-not-authorized"
    assert "openai-credential-missing" in result["blockers"]
    assert "provider-binding-paid-execution-authorized-false" in result["blockers"]
    assert (
        "provider-binding-product-development-execution-authorized-false"
        in result["blockers"]
    )
    assert all("deepseek" not in blocker for blocker in result["blockers"])
    assert all("mistral" not in blocker for blocker in result["blockers"])
    assert all("openrouter" not in blocker for blocker in result["blockers"])
    assert result["provider_calls"] == 0
    assert result["reference_answers_loaded"] is False


def test_active_preflight_rejects_historical_non_openai_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(runner, "_repo_dirty", lambda: False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")

    result = _preflight(tmp_path, HISTORICAL)

    assert "active-generator-not-openai-gpt-5.4-mini" in result["blockers"]
    assert "active-generator-model-identity-drifted" in result["blockers"]
