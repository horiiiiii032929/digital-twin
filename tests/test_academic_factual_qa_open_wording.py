from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts import run_academic_factual_qa_open_wording as wording
from src.digital_twin.evaluation.provider_json import DirectProviderJsonTransport
from src.digital_twin.repository_freeze import RepositoryFreezeError


def _load(name: str) -> dict[str, object]:
    return json.loads(
        Path("research/05_evaluation/instruments", name).read_text(encoding="utf-8")
    )


def test_wording_binding_is_exact_first_party_and_unauthorized() -> None:
    binding = _load("academic_factual_qa_open_10000_wording_binding_001.json")
    providers = binding["providers"]

    assert providers["wording-author"]["provider_model"] == (
        "gpt-5.4-mini-2026-03-17"
    )
    assert providers["wording-reviewer"]["provider_model"] == "mistral-small-2603"
    assert all(row["first_party_endpoint"] for row in providers.values())
    assert "openrouter" not in json.dumps(binding).casefold()
    assert not any(binding["authorization"].values())


def test_build_only_validation_and_full_simulation_make_no_calls() -> None:
    validated = wording.validate()
    simulated = wording.simulate()

    assert validated["status"] == "passed-build-only"
    assert validated["case_count"] == 500
    assert validated["gold_loaded"] is False
    assert validated["provider_calls"] == 0
    assert simulated["status"] == "simulated-network-free"
    assert simulated["accepted_wording_count"] == 500
    assert simulated["normalized_duplicate_count"] == 0
    assert simulated["provider_calls"] == 0


def test_provider_execution_function_cannot_open_hidden_gold() -> None:
    execution_source = inspect.getsource(wording.execute)
    scoring_source = inspect.getsource(wording.score)

    assert "_hidden_gold" not in execution_source
    assert "_hidden_gold" in scoring_source
    assert execution_source.index("_public_cases") < execution_source.index(
        "ProviderCallLedgerV1"
    )


def test_preflight_fails_closed_before_paid_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wording, "_repo_dirty", lambda: False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    result = wording.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert result["provider_calls"] == 0
    assert "binding-paid-execution-authorized-false" in result["blockers"]
    assert "instrument-paid-execution-authorized-false" in result["blockers"]
    assert "freeze-external_model_evaluation-authorization-missing" in result["blockers"]
    assert result["t0_product_execution_authorized"] is False
    assert result["final_execution_authorized"] is False


def test_execute_is_blocked_by_repository_freeze() -> None:
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        import asyncio

        asyncio.run(wording.execute(resume=False))


def test_direct_openai_request_disables_storage_and_reserves_retry_cost() -> None:
    binding = _load("academic_factual_qa_open_10000_wording_binding_001.json")
    author = binding["providers"]["wording-author"]
    transport = DirectProviderJsonTransport(author)
    schema = wording._items_schema(kind="author", count=1)

    payload = transport._payload(
        system="Return the schema.",
        prompt="One public question.",
        task="network-free-test",
        schema=schema,
    )
    one_attempt = (
        ((len("One public question.") + 3) // 4)
        * author["pricing_usd_per_million_input_tokens"]
        + author["max_output_tokens"]
        * author["pricing_usd_per_million_output_tokens"]
    ) / 1_000_000

    assert payload["store"] is False
    assert transport.estimated_cost(prompt="One public question.") == pytest.approx(
        one_attempt * 2
    )


def test_batch_parser_rejects_missing_or_reordered_cases() -> None:
    with pytest.raises(wording.WordingCheckpointError, match="IDs or order drifted"):
        wording._parse_author(
            {
                "items": [
                    {"case_id": "case-002", "question": "Second question?"},
                    {"case_id": "case-001", "question": "First question?"},
                ]
            },
            ["case-001", "case-002"],
        )
