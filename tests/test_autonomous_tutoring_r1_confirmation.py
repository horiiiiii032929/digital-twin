from scripts.run_autonomous_tutoring_r1_confirmation import (
    INSTRUMENT_PATH,
    build_trajectory_contract,
    preflight,
    validate,
    _load,
)


def test_confirmation_contract_is_source_disjoint_and_finite() -> None:
    instrument = _load(INSTRUMENT_PATH)
    rows = build_trajectory_contract(instrument)

    assert len(rows) == 50
    assert len({row["source_family_id"] for row in rows}) == 50
    assert sum(len(row["turns"]) for row in rows) == 200
    assert len(
        {turn["case_id"] for row in rows for turn in row["turns"]}
    ) == 200
    assert sum(
        any(turn.get("forced_provider_failure") for turn in row["turns"])
        for row in rows
    ) == 5
    assert sum(
        any(turn.get("restart_before_turn") for turn in row["turns"])
        for row in rows
    ) == 5


def test_confirmation_stays_unauthorized_before_model_selection() -> None:
    validated = validate()
    ready = preflight()

    assert validated["status"] == "passed-build-only"
    assert validated["provider_calls"] == 0
    assert ready["status"] == "blocked-not-authorized"
    assert "paid-execution-not-authorized" in ready["blockers"]
