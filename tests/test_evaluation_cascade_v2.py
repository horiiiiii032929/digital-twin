import pytest

from src.digital_twin.evaluation import (
    ModelCandidateManifestV2,
    TransportRetryBudgetV2,
    reconcile_case_batch,
)


def _validate(row):
    value = row.get("value")
    if not isinstance(value, str) or not value:
        raise ValueError("value is required")
    return {"case_id": row["case_id"], "value": value}


def test_reconciles_reordered_rows_by_case_id():
    result = reconcile_case_batch(
        expected_case_ids=["a", "b", "c"],
        provider_rows=[
            {"case_id": "c", "value": "3"},
            {"case_id": "a", "value": "1"},
            {"case_id": "b", "value": "2"},
        ],
        validate_semantics=_validate,
    )

    assert result.exact_id_set is True
    assert [row.case_id for row in result.rows] == ["a", "b", "c"]
    assert [row.payload["value"] for row in result.rows if row.payload] == [
        "1",
        "2",
        "3",
    ]


def test_quarantines_duplicate_missing_unknown_and_semantic_rows():
    result = reconcile_case_batch(
        expected_case_ids=["a", "b", "c", "d"],
        provider_rows=[
            {"case_id": "a", "value": "1"},
            {"case_id": "a", "value": "again"},
            {"case_id": "c", "value": ""},
            {"case_id": "d", "value": "4"},
            {"case_id": "unknown", "value": "x"},
        ],
        validate_semantics=_validate,
    )

    assert result.exact_id_set is False
    assert result.quarantined_count == 3
    assert [row.quarantine.reason if row.quarantine else None for row in result.rows] == [
        "duplicate-id",
        "missing-id",
        "semantic-invalid",
        None,
    ]
    assert result.unknown_case_ids == ["unknown"]


def test_transport_retry_budget_is_transport_only_one_per_request_and_two_percent():
    budget = TransportRetryBudgetV2(planned_calls=200)

    assert budget.maximum_retries == 4
    assert budget.allow(request_key="a", failure_kind="timeout") is True
    assert budget.allow(request_key="a", failure_kind="timeout") is False
    assert budget.allow(request_key="b", failure_kind="malformed-json") is False
    assert budget.allow(request_key="b", failure_kind="http-429") is True
    assert budget.allow(request_key="c", failure_kind="http-5xx") is True
    assert budget.allow(request_key="d", failure_kind="timeout") is True
    assert budget.allow(request_key="e", failure_kind="timeout") is False


def test_candidate_manifest_requires_exact_returned_identity():
    payload = {
        "candidate_id": "luna-low",
        "provider_model": "gpt-5.6-luna",
        "expected_returned_model": "gpt-5.6-luna",
        "reasoning_effort": "low",
        "max_output_tokens": 600,
        "request_store": False,
        "prompt_id": "strict-evidence-grounded-prompt-v3",
        "retriever_id": "qwen3-hybrid-v1",
        "evidence_gate_id": "structured-lexical-coverage-evidence-gate-v1",
        "policy_id": "structured-professor-policy-v1",
        "code_revision": "abcdef0",
        "pricing_verified_at": "2026-08-29T00:00:00+08:00",
        "input_price_usd_per_million": 0.2,
        "output_price_usd_per_million": 1.2,
    }

    assert ModelCandidateManifestV2.model_validate(payload).provider == "openai"
    payload["expected_returned_model"] = "gpt-5.6"
    with pytest.raises(ValueError, match="identity"):
        ModelCandidateManifestV2.model_validate(payload)
