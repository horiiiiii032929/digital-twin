import json
from pathlib import Path
import sqlite3

from scripts import run_course_digital_twin_autonomous_long_run_001 as runner


def test_long_run_program_is_finite_and_preserves_known_final() -> None:
    result = runner.validate()

    assert result["status"] == "passed-frozen-pending-execution"
    assert runner.EXECUTION_ATTEMPT_ID.endswith("attempt-002")
    assert result["stage_count"] == 4
    assert result["global_emergency_cost_usd"] == 200.0
    assert result["known_10000_plus_1000_preserved"] is True
    assert result["same_case_quality_rerun_allowed"] is False


def test_long_run_simulation_has_no_network_or_repeated_authorization() -> None:
    result = runner.simulate()

    assert result["status"] == "passed-network-free-simulation"
    assert result["quality_failure_stops_dependent_autonomy"] is True
    assert result["orthogonal_release_and_publication_continue"] is True
    assert result["known_10000_plus_1000_rerun"] is False
    assert result["provider_calls"] == 0
    assert result["network_calls"] == 0


def test_recorded_program_stage_supports_read_only_resume(tmp_path: Path) -> None:
    ledger_path = tmp_path / runner.LEDGER_NAME
    connection = sqlite3.connect(ledger_path)
    connection.execute(
        "CREATE TABLE stages ("
        "stage_id TEXT PRIMARY KEY,status TEXT NOT NULL,"
        "result_json TEXT NOT NULL,updated_at TEXT NOT NULL)"
    )
    result = {"status": "completed-keep", "decision": "Keep"}
    connection.execute(
        "INSERT INTO stages VALUES (?,?,?,?)",
        ("grounding-selection-500-plus-100", "completed-keep", json.dumps(result), "now"),
    )
    connection.commit()
    connection.close()

    assert runner._recorded_program_stage(
        tmp_path, "grounding-selection-500-plus-100"
    ) == result


def test_local_release_regression_paths_exist() -> None:
    assert all((runner.ROOT / path).is_file() for path in runner.LOCAL_RELEASE_TESTS)
