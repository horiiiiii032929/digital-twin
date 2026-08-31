from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import run_governed_full_autonomy_v2_1_provider_integration as runner


def test_provider_integration_instrument_is_bounded_and_unselected() -> None:
    payload = runner.validate()
    instrument = payload["instrument"]
    candidate = payload["candidate"]

    assert instrument["status"] == "completed-go-deeper-authorization-revoked"
    assert instrument["execution"] == {
        "provider_execution_authorized": False,
        "paid_execution_authorized": False,
        "authorized_at": "2026-08-31T13:35:00Z",
        "authorization_scope": (
            "User authorized governed-full-autonomy-v2-1-provider-integration-001 "
            "up to USD 1; authority was consumed once and revoked after completion."
        ),
        "authorization_revoked_at": "2026-08-31T13:42:00Z",
        "automatic_release_promotion": False,
        "maximum_calls": 12,
        "maximum_cost_usd": 1.0,
        "maximum_retries": 0,
        "exclusive_output": (
            "reports/generated/"
            "governed-full-autonomy-v2-1-provider-integration-001/result.json"
        ),
    }
    assert candidate["selection"]["selected_for_release"] is False
    assert candidate["system"]["t0_rollback_available"] is True
    assert candidate["system"]["t1_v1_control_available"] is True


def test_network_free_simulation_exercises_actual_reactive_and_proactive_services() -> None:
    result = runner.simulate()

    assert result["status"] == "completed-go-deeper"
    assert result["hard_gates_passed"] is True
    assert result["reactive_turn_count"] == 2
    assert result["proactive_job_count"] == 1
    assert result["total_calls"] == 4
    assert result["selected_for_release"] is False
    assert all(result["gates"].values())


def test_live_preflight_is_blocked_after_authority_is_revoked(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-preflight-key")
    monkeypatch.setattr(
        runner,
        "_model_metadata",
        lambda model, api_key: {"id": model, "owned_by": "system"},
    )
    monkeypatch.setattr(
        runner,
        "_git",
        lambda *arguments: (
            "" if arguments == ("status", "--porcelain") else "candidate-head"
        ),
    )
    monkeypatch.setattr(
        runner,
        "_sha256_at_revision",
        lambda path, revision: (
            runner._load(runner.CANDIDATE_PATH)["system"]["release_profile_sha256"]
            if path == runner.PROFILE_PATH
            else runner._load(runner.CANDIDATE_PATH)["source_hashes"][
                {
                    "compose.local-r1.yml": "compose_local_r1_sha256",
                    "src/digital_twin/student/tutoring_graph.py": (
                        "reactive_graph_sha256"
                    ),
                    "src/digital_twin/student/autonomy_runtime.py": (
                        "proactive_runtime_sha256"
                    ),
                }[path.relative_to(runner.ROOT).as_posix()]
            ]
        ),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(runner, "OUTPUT_PATH", tmp_path / "unused-result.json")

    result = runner.live_preflight()

    assert result["status"] == "blocked-not-authorized"
    assert result["provider_calls"] == 0
    assert result["checks"]["provider_execution_authorized"] is False
    assert result["checks"]["paid_execution_authorized"] is False


def test_execute_fails_before_constructing_a_provider_request(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "live_preflight",
        lambda: {"status": "blocked-not-authorized", "provider_calls": 0},
    )

    with pytest.raises(RuntimeError, match="blocked-not-authorized"):
        runner.execute()
