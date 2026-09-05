from __future__ import annotations

from collections import Counter

from scripts import build_true_visual_omni_confirmation_002 as builder
from scripts import run_true_visual_omni_confirmation_002 as runner


def test_fresh_visual_packages_are_deterministic_and_gold_is_separate() -> None:
    first = builder.build()
    second = builder.build()

    assert first == second
    assert len(first["public"]["cases"]) == 60
    assert len(first["gold"]["cases"]) == 60
    assert len(first["sources"]["assets"]) == 30
    assert all("expected_action" not in row for row in first["public"]["cases"])
    assert all("canonical_answer" not in row for row in first["public"]["cases"])
    assert Counter(row["visual_family"] for row in first["sources"]["assets"]) == {
        "packet-layout": 10,
        "protocol-flow": 10,
        "architecture-chart": 10,
    }


def test_visual_confirmation_contract_and_network_free_simulation() -> None:
    validation = runner.validate()
    simulation = runner.simulate()

    assert validation["status"] == "passed"
    assert validation["source_disjoint"] is True
    assert validation["gold_loaded_by_execution"] is False
    assert simulation["status"] == "passed-network-free-simulation"
    assert simulation["provider_calls"] == 0
    assert simulation["gold_opening_order_enforced"] is True


def test_ordinary_text_regression_is_measured() -> None:
    assert runner._ordinary_text_path_regression() is True

