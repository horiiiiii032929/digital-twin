from __future__ import annotations

import copy
import json

import pytest

from scripts.run_proactive_outreach_a1_shadow_confirmation import (
    ProactiveShadowConfirmationError,
    expand_cases,
    load_instrument,
    self_test,
    validate_preflight,
)


def test_confirmation_instrument_is_finite_stratified_and_unauthorized():
    instrument = load_instrument()
    cases = expand_cases(instrument)

    assert instrument["status"] == "reviewed-pending-network-free-authorization"
    assert instrument["execution"]["network_free_execution_authorized"] is False
    assert len(instrument["clusters"]) == 12
    assert len(cases) == 60
    assert len({case["id"] for case in cases}) == 60
    assert sum(case["expected_action"] == "propose" for case in cases) == 24
    assert sum(case["expected_action"] == "no-action" for case in cases) == 36
    assert {case["cluster"]["course_family"] for case in cases} == {
        "operating-systems",
        "networking",
        "data-structures",
        "python",
    }


def test_confirmation_preflight_fails_closed_before_authorization(tmp_path):
    preflight = validate_preflight(
        load_instrument(),
        output=tmp_path / "unused.json",
        require_clean=False,
    )

    assert preflight["status"] == "blocked-not-authorized"
    assert preflight["blockers"] == [
        "instrument-not-frozen-pending",
        "network-free-execution-not-authorized",
    ]
    assert preflight["provider_calls"] == 0
    assert preflight["external_deliveries"] == 0
    assert preflight["private_data_reads"] == 0


def test_network_free_canary_exercises_publication_hook_without_side_effects():
    result = self_test()

    assert result["status"] == "passed"
    assert result["provider_calls"] == 0
    assert result["external_deliveries"] == 0
    assert result["private_data_reads"] == 0


def test_confirmation_validation_rejects_duplicate_cluster_ids(tmp_path):
    instrument = copy.deepcopy(load_instrument())
    instrument["clusters"][1]["id"] = instrument["clusters"][0]["id"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(instrument), encoding="utf-8")

    with pytest.raises(ProactiveShadowConfirmationError, match="12 unique"):
        load_instrument(path)
