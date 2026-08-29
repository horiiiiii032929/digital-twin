from __future__ import annotations

import json

from jsonschema import Draft202012Validator
import pytest

from scripts import academic_factual_qa_open_10000_t0_adapter as adapter
from scripts import run_academic_factual_qa_open_product_checkpoint_006 as historical
from scripts import run_academic_factual_qa_open_product_checkpoint_007 as checkpoint


def test_finite_successor_binds_pairing_and_extractive_contract() -> None:
    result = checkpoint.validate()

    assert result["status"] == "passed-build-only"
    assert result["explicit_pairing_manifest_count"] == 2
    assert result["response_contract"] == "extractive-boundary-output-v1"
    assert result["claim_validator"] == (
        "contiguous-quote-atomic-claim-verifier-v1@1.0.0"
    )
    assert result["maximum_method_successors"] == 1
    assert result["provider_calls"] == 0
    assert result["final_execution_authorized"] is False


def test_extractive_provider_schema_enforces_runtime_claim_identifiers() -> None:
    schema = adapter.EXTRACTIVE_BOUNDARY_RESPONSE_SCHEMA
    Draft202012Validator.check_schema(schema)
    claim_id = schema["properties"]["claims"]["items"]["properties"]["claim_id"]
    citation_id = schema["properties"]["claims"]["items"]["properties"][
        "citation_ids"
    ]["items"]

    assert claim_id["pattern"] == "^claim-[a-z0-9-]+$"
    assert citation_id["pattern"] == "^S[1-9][0-9]*$"
    assert set(schema["properties"]["action"]["enum"]) == {
        "answer",
        "abstain",
        "clarify",
    }


def test_successor_does_not_mutate_checkpoint_006() -> None:
    before = historical.validate()
    checkpoint.validate()
    after = historical.validate()

    assert before == after
    assert historical.INSTRUMENT_ID.endswith("checkpoint-006")


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("pass", "completed-keep"),
        ("product-failure", "completed-refine"),
        ("provider-failure", "invalid-execution"),
        ("advisory-malformed", "completed-keep"),
        ("truth-defect", "needs-human-review"),
    ],
)
def test_successor_simulations_remain_finite(scenario: str, expected: str) -> None:
    result = checkpoint.simulate(scenario=scenario)

    assert result["status"] == expected
    assert result["network_accessed"] is False
    assert result["provider_calls"] == 0
    assert result["pairing_contract"] == "explicit-package-pairing-v1"


def test_clean_preflight_blocks_only_external_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(historical, "_repo_dirty", lambda: False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = checkpoint.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert result["provider_calls"] == 0
    assert result["maximum_method_successors"] == 1
    assert "freeze-external_model_evaluation-authorization-missing" in result[
        "blockers"
    ]
    assert "instrument-provider-execution-authorized-false" in result["blockers"]
    assert not any("pairing" in blocker for blocker in result["blockers"])


def test_pairing_manifests_are_hash_bound_to_distinct_packages() -> None:
    candidate = json.loads(checkpoint.CANDIDATE_PAIRING.read_text(encoding="utf-8"))
    control = json.loads(checkpoint.CONTROL_PAIRING.read_text(encoding="utf-8"))

    assert candidate["public_package"]["dataset_id"] != candidate[
        "hidden_gold_package"
    ]["dataset_id"]
    assert control["public_package"]["split"] != control["hidden_gold_package"][
        "split"
    ]
    assert candidate["case_count"] == 500
    assert control["case_count"] == 100
