from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.build_academic_factual_qa_open_development_v2 import (
    DEVELOPMENT_CASES_PATH,
    DEVELOPMENT_CONTROL_CASES_PATH,
    DEVELOPMENT_CONTROL_GOLD_PATH,
    DEVELOPMENT_GOLD_PATH,
    build_packages,
    preflight,
    validate_direct_provider_contracts,
)
from scripts.academic_factual_qa_open_10000_t0_adapter import (
    LiveT0AdapterError,
    _generator_transport,
)
from src.digital_twin.evaluation import SystemUnderTestManifestV1
from src.digital_twin.evaluation import provider_json
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    OpenAiCompatibleJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonError,
)


BINDING_PATH = Path(
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_direct_provider_binding_001.json"
)


def _providers() -> dict[str, dict[str, Any]]:
    return json.loads(BINDING_PATH.read_text(encoding="utf-8"))["providers"]


def test_development_v2_is_complete_separate_and_byte_stable() -> None:
    first = build_packages()
    second = build_packages()

    assert first["status"] == "passed-build-only"
    assert first["case_count"] == 500
    assert first["control_case_count"] == 100
    assert first["answerable_count"] == 400
    assert first["boundary_count"] == 100
    assert first["normalized_duplicate_count"] == 0
    assert first["provider_calls"] == 0
    assert first["final_cases_constructed"] == 0
    assert {
        key: value["content_sha256"] for key, value in first["packages"].items()
    } == {
        key: value["content_sha256"] for key, value in second["packages"].items()
    }

    cases = first["packages"]["cases"]["cases"]
    gold = first["packages"]["gold"]["gold"]
    assert len({row["case_id"] for row in cases}) == 500
    assert {row["case_id"] for row in cases} == {row["case_id"] for row in gold}
    assert all(
        "canonical_answer" not in row
        and "expected_action" not in row
        and "claims" not in row
        for row in cases
    )
    answerable = [row for row in gold if row["expected_action"] == "answer"]
    boundary = [row for row in gold if row["expected_action"] != "answer"]
    assert all(row["claims"] for row in answerable)
    assert all(not row["claims"] and row["boundary_reason"] for row in boundary)


def test_control_is_exact_twenty_cluster_subset() -> None:
    packages = build_packages()["packages"]
    cases = packages["cases"]["cases"]
    control = packages["control_cases"]["cases"]

    assert len(control) == 100
    assert len({row["cluster_id"] for row in control}) == 20
    assert {row["case_id"] for row in control} <= {
        row["case_id"] for row in cases
    }


def test_direct_provider_contract_is_network_free_and_has_no_router() -> None:
    result = validate_direct_provider_contracts()
    providers = _providers()

    assert result["status"] == "simulated-network-free"
    assert result["strict_schema_requested"] is True
    assert result["provider_calls"] == 0
    assert {row["provider"] for row in providers.values()} == {
        "openai",
        "mistral",
    }
    assert all(row["first_party_endpoint"] for row in providers.values())
    assert "openrouter" not in json.dumps(providers).casefold()
    assert "deepseek" not in json.dumps(providers).casefold()


def test_t0_adapter_selects_direct_openai_only_from_explicit_manifest() -> None:
    historical = SystemUnderTestManifestV1.model_validate(
        json.loads(
            Path(
                "research/05_evaluation/instruments/"
                "academic_factual_qa_open_10000_v1_t0_candidate_manifest.json"
            ).read_text(encoding="utf-8")
        )
    )
    _, historical_transport = _generator_transport(historical)
    direct_manifest = historical.model_copy(
        update={"generator": "openai-gpt-5.4-mini-live-atomic"}
    )
    direct_binding, direct_transport = _generator_transport(direct_manifest)

    assert isinstance(historical_transport, OpenAiCompatibleJsonTransport)
    assert isinstance(direct_transport, DirectProviderJsonTransport)
    assert direct_binding["provider"] == "openai"
    assert direct_binding["api_url"] == "https://api.openai.com/v1/responses"
    assert direct_binding["provider_model"] == "gpt-5.4-mini-2026-03-17"

    unsupported = historical.model_copy(update={"generator": "implicit-latest"})
    with pytest.raises(LiveT0AdapterError, match="generator drifted"):
        _generator_transport(unsupported)


def test_paid_preflight_remains_blocked_without_constructing_final_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setattr(
        "scripts.build_academic_factual_qa_open_development_v2._repo_dirty",
        lambda: False,
    )

    result = preflight()

    assert result["status"] == "blocked-not-authorized"
    assert result["provider_calls"] == 0
    assert result["final_product_execution_authorized"] is False
    assert "openai_api_key-missing" in result["blockers"]
    assert "mistral_api_key-missing" in result["blockers"]
    assert "direct-binding-provider-execution-authorized-false" in result["blockers"]
    assert (
        "instrument-development-product-execution-authorized-false"
        in result["blockers"]
    )


def test_paid_preflight_rejects_dirty_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.build_academic_factual_qa_open_development_v2._repo_dirty",
        lambda: True,
    )

    assert "repository-dirty" in preflight()["blockers"]


class _FakeResponse:
    def __init__(
        self,
        value: dict[str, Any],
        *,
        status_code: int = 200,
    ) -> None:
        self._value = value
        self.status_code = status_code
        self.is_error = status_code >= 400
        self.headers = {"x-request-id": "request-001"}

    def json(self) -> dict[str, Any]:
        return self._value


def _openai_value(
    *, model: str = "gpt-5.4-mini-2026-03-17", content: str = '{"ok": true}'
) -> dict[str, Any]:
    return {
        "status": "completed",
        "model": model,
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": content}],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def _mistral_value(*, content: str = '{"ok": true}') -> dict[str, Any]:
    return {
        "model": "mistral-small-2603",
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 4},
    }


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[_FakeResponse],
    captured: list[dict[str, Any]],
) -> None:
    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: Any) -> _FakeResponse:
            captured.append(kwargs["json"])
            return responses.pop(0)

    monkeypatch.setattr(
        provider_json.httpx,
        "AsyncClient",
        lambda **kwargs: FakeClient(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_key", "response_value"),
    [
        ("openai-gpt-5.4-mini", _openai_value()),
        ("mistral-small-4", _mistral_value()),
    ],
)
async def test_direct_transport_uses_strict_schema_and_exact_identity(
    monkeypatch: pytest.MonkeyPatch,
    provider_key: str,
    response_value: dict[str, Any],
) -> None:
    binding = _providers()[provider_key]
    monkeypatch.setenv(binding["credential_environment_variable"], "test-key")
    captured: list[dict[str, Any]] = []
    _install_fake_client(monkeypatch, [_FakeResponse(response_value)], captured)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["ok"],
        "properties": {"ok": {"type": "boolean"}},
    }

    result = await DirectProviderJsonTransport(binding).call(
        system="Return JSON.",
        prompt="Return ok=true.",
        task="test",
        schema=schema,
    )

    assert result.content == {"ok": True}
    assert result.provider_model == binding["provider_model"]
    assert result.attempt_count == 1
    assert result.recovered_transport_failures == []
    assert "json_schema" in json.dumps(captured[0])


@pytest.mark.asyncio
async def test_direct_transport_retries_only_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = _providers()["openai-gpt-5.4-mini"]
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: list[dict[str, Any]] = []
    _install_fake_client(
        monkeypatch,
        [
            _FakeResponse({"error": {"message": "rate limited"}}, status_code=429),
            _FakeResponse(_openai_value()),
        ],
        captured,
    )

    result = await DirectProviderJsonTransport(binding).call(
        system="Return JSON.",
        prompt="Return ok=true.",
        task="test-retry",
        schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["ok"],
            "properties": {"ok": {"type": "boolean"}},
        },
    )

    assert result.attempt_count == 2
    assert result.recovered_transport_failures == [
        "direct provider retryable HTTP 429"
    ]
    assert len(captured) == 2


@pytest.mark.asyncio
async def test_direct_retry_is_durable_in_provider_accounting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    binding = _providers()["openai-gpt-5.4-mini"]
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: list[dict[str, Any]] = []
    _install_fake_client(
        monkeypatch,
        [
            _FakeResponse({"error": {"message": "temporary"}}, status_code=500),
            _FakeResponse(_openai_value()),
        ],
        captured,
    )
    transport = DirectProviderJsonTransport(binding)
    ledger = ProviderCallLedgerV1(
        tmp_path / "direct-provider.sqlite3",
        run_binding={"binding": binding},
        maximum_calls=1,
        maximum_cost_usd=1,
        resume=False,
    )

    await transport.call_with_ledger(
        ledger=ledger,
        request_key="case-001",
        provider_role="test",
        system="Return JSON.",
        prompt="Return ok=true.",
        task="test-accounting",
        schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["ok"],
            "properties": {"ok": {"type": "boolean"}},
        },
    )
    ledger.mark_complete()
    snapshot = ledger.snapshot()
    ledger.close()

    assert snapshot["provider_calls"] == 1
    assert snapshot["provider_attempts"] == 2
    assert snapshot["recovered_transport_failures"] == 1
    assert snapshot["failed_calls"] == 0


@pytest.mark.asyncio
async def test_direct_transport_does_not_retry_schema_or_identity_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = _providers()["openai-gpt-5.4-mini"]
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: list[dict[str, Any]] = []
    _install_fake_client(
        monkeypatch,
        [_FakeResponse(_openai_value(content='{"ok": "not-boolean"}'))],
        captured,
    )
    transport = DirectProviderJsonTransport(binding)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["ok"],
        "properties": {"ok": {"type": "boolean"}},
    }

    with pytest.raises(ProviderJsonError, match="violates schema"):
        await transport.call(
            system="Return JSON.",
            prompt="Return ok=true.",
            task="test-schema-failure",
            schema=schema,
        )
    assert len(captured) == 1

    captured.clear()
    _install_fake_client(
        monkeypatch,
        [_FakeResponse(_openai_value(model="gpt-identity-drift"))],
        captured,
    )
    with pytest.raises(ProviderJsonError, match="model identity drifted"):
        await transport.call(
            system="Return JSON.",
            prompt="Return ok=true.",
            task="test-identity-failure",
            schema=schema,
        )
    assert len(captured) == 1


def test_build_only_validation_does_not_write_outputs() -> None:
    existing = {
        path: path.exists()
        for path in (
            DEVELOPMENT_CASES_PATH,
            DEVELOPMENT_GOLD_PATH,
            DEVELOPMENT_CONTROL_CASES_PATH,
            DEVELOPMENT_CONTROL_GOLD_PATH,
        )
    }

    build_packages()
    validate_direct_provider_contracts()

    assert {path: path.exists() for path in existing} == existing
