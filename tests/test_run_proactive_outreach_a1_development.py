import copy
import json

import pytest

from scripts.run_proactive_outreach_a1_development import (
    ProactiveDevelopmentError,
    execute,
    load_instrument,
    validate_preflight,
)


def test_frozen_instrument_has_finite_network_free_contract():
    instrument = load_instrument()

    assert len(instrument["p0_mechanism_checks"]) == 12
    assert len(instrument["p1_shadow_cases"]) == 20
    assert instrument["execution"]["network_free_execution_authorized"] is True
    assert instrument["execution"]["provider_calls_authorized"] is False
    assert instrument["execution"]["real_student_delivery_authorized"] is False
    assert instrument["implementation"]["active_mode_selected"] is False


def test_preflight_is_exclusive_and_can_require_clean_tree(tmp_path):
    instrument = load_instrument()
    output = tmp_path / "result.json"

    ready = validate_preflight(instrument, output=output, require_clean=False)
    output.write_text("occupied", encoding="utf-8")
    blocked = validate_preflight(instrument, output=output, require_clean=False)

    assert ready["status"] == "ready"
    assert blocked["status"] == "blocked"
    assert "exclusive-output-already-exists" in blocked["blockers"]


def test_network_free_development_execution_passes_every_frozen_gate(
    tmp_path, monkeypatch
):
    instrument = load_instrument()
    output = tmp_path / "result.json"
    monkeypatch.setattr(
        "scripts.run_proactive_outreach_a1_development._git_revision",
        lambda: "a" * 40,
    )

    result = execute(instrument, output=output)

    assert result["status"] == "completed-go-deeper"
    assert result["metrics"] == instrument["hard_gates"]
    assert all(item["passed"] for item in result["p0_checks"])
    assert all(item["action_correct"] for item in result["p1_case_results"])
    assert result["provider_calls"] == 0
    assert result["external_deliveries"] == 0
    assert result["selected_for_release"] is False
    assert output.exists()


def test_instrument_validation_rejects_duplicate_case_ids(tmp_path):
    instrument = copy.deepcopy(load_instrument())
    instrument["p1_shadow_cases"][1]["id"] = instrument["p1_shadow_cases"][0]["id"]
    path = tmp_path / "instrument.json"
    path.write_text(json.dumps(instrument), encoding="utf-8")

    with pytest.raises(ProactiveDevelopmentError, match="20 unique"):
        load_instrument(path)
