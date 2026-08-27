from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from scripts import run_academic_factual_qa_open_wording_v2 as wording
from src.digital_twin.repository_freeze import RepositoryFreezeError


def _binding() -> dict[str, object]:
    return json.loads(
        Path(
            "research/05_evaluation/instruments/"
            "academic_factual_qa_open_10000_openai_binding_002.json"
        ).read_text(encoding="utf-8")
    )


def test_active_wording_checkpoint_uses_only_exact_openai_snapshots() -> None:
    binding = _binding()
    providers = binding["providers"]

    assert providers["high-volume-generator"]["provider_model"] == (
        "gpt-5.4-mini-2026-03-17"
    )
    assert providers["semantic-reviewer"]["provider_model"] == (
        "gpt-5.4-2026-03-05"
    )
    assert {row["provider"] for row in providers.values()} == {"openai"}
    assert {row["credential_environment_variable"] for row in providers.values()} == {
        "OPENAI_API_KEY"
    }
    assert all(row["request_store"] is False for row in providers.values())
    assert not any(binding["authorization"].values())


def test_active_wording_validation_and_simulation_are_network_free() -> None:
    validated = wording.validate()
    simulated = wording.simulate()

    assert validated["status"] == "passed-build-only"
    assert validated["reviewer_provider"] == "openai"
    assert validated["openai_store"] is False
    assert validated["reviewer_store"] is False
    assert validated["gold_loaded"] is False
    assert simulated["case_count"] == 500
    assert simulated["provider_calls"] == 0
    assert simulated["network_accessed"] is False


def test_active_wording_preflight_requires_one_credential_and_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wording.legacy, "_repo_dirty", lambda: False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = wording.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert "openai_api_key-missing" in result["blockers"]
    assert all("deepseek" not in item for item in result["blockers"])
    assert all("mistral" not in item for item in result["blockers"])
    assert all("openrouter" not in item for item in result["blockers"])
    assert result["provider_calls"] == 0


def test_active_wording_execution_remains_frozen() -> None:
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        asyncio.run(wording.execute(resume=False))
