from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.run_factual_qa_v3_reviewer_qualification import (
    ROOT,
    MUTATION_TYPES,
    build_pairs,
    build_preflight,
    deterministic_valid,
    _maximum_reserved_cost,
    validate_instrument,
)


def test_openrouter_revision_may_be_absent_when_exact_model_is_pinned() -> None:
    instrument = validate_instrument()

    assert instrument["model_role"]["provider_model"] == "mistralai/mistral-small-2603"
    assert instrument["model_role"]["provider_routing"]["allow_fallbacks"] is False


def test_review_qualification_instrument_is_bounded_and_frozen() -> None:
    instrument = validate_instrument()
    assert instrument["status"] == "frozen-pending-execution"
    assert instrument["execution"]["total_provider_call_limit"] == 49
    assert instrument["execution"]["retry_attempts"] == 0
    assert instrument["execution"]["cost_stop_usd"] == 0.5
    assert instrument["decision_rule"]["scale_to_10000_authorized_by_this_run"] is False


def test_pairs_are_new_balanced_and_deterministically_labeled() -> None:
    pairs = build_pairs()
    assert len(pairs) == 24
    assert len({pair["pair_id"] for pair in pairs}) == 24
    assert Counter(pair["mutation_type"] for pair in pairs) == Counter(MUTATION_TYPES)
    assert {pair["source"]["modality"] for pair in pairs} == {"text", "code", "table", "diagram"}
    assert all(deterministic_valid(pair, pair["clean_case"]) for pair in pairs)
    assert all(not deterministic_valid(pair, pair["mutated_case"]) for pair in pairs)


def test_run_006_historical_fixture_values_remain_stable() -> None:
    pairs = build_pairs()

    first = pairs[0]
    paraphrased = next(
        pair for pair in pairs if pair["mutation_type"] == "paraphrased-citation"
    )
    assert first["source"]["source_truth"] == (
        "Marker M01 uses threshold 101 units. "
        "Marker A01 uses threshold 201 units."
    )
    assert first["distractor"]["source_truth"] == (
        "Distractor D01 uses threshold 301 units."
    )
    assert paraphrased["mutated_case"]["citations"][0]["quote"] == (
        "The threshold for M09 is 109."
    )
    invalid_claim = next(
        pair for pair in pairs if pair["mutation_type"] == "invalid-claim-binding"
    )
    assert invalid_claim["mutated_case"]["selected_claim_ids"] == [
        "invalid-claim-17"
    ]


def test_preflight_blocks_unfrozen_instrument_without_calls(tmp_path: Path) -> None:
    instrument = validate_instrument()
    instrument["status"] = "reviewed-pending-execution-authorization"
    preflight = build_preflight(instrument, tmp_path / "unused.json")
    assert preflight["status"] == "blocked"
    assert preflight["instrument_frozen"] is False
    assert preflight["external_call_enabled"] is False
    assert preflight["scale_to_10000_authorized"] is False


def test_instrument_json_has_no_private_source_path() -> None:
    serialized = json.dumps(validate_instrument()).casefold()
    assert "academia_vault" not in serialized
    assert "student_data\": true" not in serialized


def test_maximum_reservation_is_below_frozen_cost_stop() -> None:
    instrument = validate_instrument()
    reservation = _maximum_reserved_cost(
        instrument["model_role"], system="s" * 1000, prompts=["p" * 8000] * 49
    )

    assert reservation < instrument["execution"]["cost_stop_usd"]


def test_qwen37plus_qualification_is_new_bounded_and_price_gated() -> None:
    path = (
        ROOT
        / "research/05_evaluation/instruments/"
        "factual_qa_v3_reviewer_qualification_007.json"
    )
    instrument = validate_instrument(path)
    pairs = build_pairs(instrument["instrument_id"])

    assert instrument["status"] == "frozen-pending-execution"
    assert instrument["model_role"]["provider_model"] == "qwen/qwen3.7-plus"
    assert instrument["execution"]["cost_stop_usd"] == 0.1
    assert instrument["execution"]["total_provider_call_limit"] == 49
    assert len(pairs) == 24
    assert all(pair["pair_id"].startswith("rq007-") for pair in pairs)
    assert not ({pair["pair_id"] for pair in pairs} & {pair["pair_id"] for pair in build_pairs()})
    assert all(deterministic_valid(pair, pair["clean_case"]) for pair in pairs)
    assert all(not deterministic_valid(pair, pair["mutated_case"]) for pair in pairs)

    reservation = _maximum_reserved_cost(
        instrument["model_role"], system="s" * 1000, prompts=["p" * 8000] * 49
    )
    assert reservation < instrument["execution"]["cost_stop_usd"]
