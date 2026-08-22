from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.run_factual_qa_v3_scale_checkpoint_1000 import (
    INSTRUMENT_ID,
    _build_mutations,
    build_preflight,
    load_assets,
    validate_instrument,
)
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


@pytest.fixture(scope="module")
def assets() -> dict:
    return load_assets()


def test_checkpoint_selects_and_authorizes_only_the_additional_900_cases(
    assets: dict,
) -> None:
    instrument = validate_instrument()

    assert instrument["instrument_id"] == INSTRUMENT_ID
    assert instrument["status"] == "frozen-pending-execution"
    assert instrument["execution"]["provider_execution_authorized"] is True
    assert len(assets["truth_packages"]) == 900
    assert {item["checkpoint_stage"] for item in assets["truth_packages"]} == {
        "checkpoint-1000"
    }
    assert assets["previous_summary"]["case_count"] == 100

    require_bounded_pilot_operation_allowed(INSTRUMENT_ID)


def test_checkpoint_preflight_requires_live_metadata_before_execution(
    assets: dict, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(
        "scripts.run_factual_qa_v3_scale_checkpoint_1000._working_tree_dirty",
        lambda: False,
    )

    preflight = build_preflight(assets, output_path=tmp_path / "unused.json")

    assert preflight["status"] == "blocked-provider-freshness"
    assert preflight["new_case_count"] == 900
    assert preflight["cumulative_case_count"] == 1000
    assert preflight["scale_10000_authorized"] is False


def test_checkpoint_mutations_are_balanced_and_deterministically_invalid(
    assets: dict,
) -> None:
    mutations = _build_mutations(assets)

    assert len(mutations) == 180
    assert all(not item["deterministic"]["passed"] for item in mutations)
    assert {
        mutation_type: sum(
            item["mutation_type"] == mutation_type for item in mutations
        )
        for mutation_type in {item["mutation_type"] for item in mutations}
    } == {
        "missing-citation": 30,
        "truncated-citation": 30,
        "paraphrased-citation": 30,
        "extra-supported-claim": 30,
        "invalid-claim-binding": 30,
        "invalid-source-binding": 30,
    }


def test_checkpoint_authorization_does_not_authorize_9000(assets: dict) -> None:
    authorized = deepcopy(assets["instrument"])
    authorized["status"] = "frozen-pending-execution"
    authorized["execution"]["provider_execution_authorized"] = True

    assert authorized["decision_rule"]["authorize_remaining_9000"] is False
    assert authorized["execution"]["automatic_stage_promotion"] is False
