from __future__ import annotations

import asyncio
from collections import Counter

import pytest

from scripts import run_factual_qa_v3_scale_checkpoint_1000 as stage
from scripts import run_factual_qa_v3_scale_completion_10000 as completion


class InsufficientCreditError(RuntimeError):
    status_code = 402


class PauseOnceTransport:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.paused = False

    async def call(self, **kwargs):
        if not self.paused:
            self.paused = True
            raise InsufficientCreditError("insufficient credit")
        return await self.delegate.call(**kwargs)


class AlwaysInsufficientCreditTransport:
    async def call(self, **kwargs):
        raise InsufficientCreditError("insufficient credit")


@pytest.fixture()
def configured_stage(monkeypatch: pytest.MonkeyPatch):
    for name, value in completion.CONFIGURATION.items():
        monkeypatch.setattr(stage, name, value)
    return stage


def test_completion_selects_exact_remaining_9000_cases(configured_stage) -> None:
    assets = configured_stage.load_assets(completion.CONFIGURATION["INSTRUMENT_PATH"])

    assert len(assets["truth_packages"]) == 9000
    assert {item["checkpoint_stage"] for item in assets["truth_packages"]} == {
        "scale-10000"
    }
    assert Counter(
        item["expected_action"] for item in assets["truth_packages"]
    ) == {
        "answer": 7200,
        "abstain": 900,
        "clarify": 450,
        "refuse": 450,
    }
    assert assets["previous_summary"]["cumulative_case_count"] == 1000


def test_completion_preflight_reports_revoked_authorization_and_balance(
    configured_stage, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assets = configured_stage.load_assets(completion.CONFIGURATION["INSTRUMENT_PATH"])
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(configured_stage, "_working_tree_dirty", lambda: False)

    preflight = configured_stage.build_preflight(
        assets,
        output_path=tmp_path / "unused.sqlite3",
        live_balances={"deepseek-official-api": 9.25, "openrouter": 3.23},
    )

    assert preflight["status"] == "blocked-not-authorized"
    assert preflight["provider_execution_authorized"] is False
    assert preflight["instrument_frozen"] is False
    assert preflight["new_case_count"] == 9000
    assert preflight["cumulative_case_count"] == 10000
    assert preflight["further_scale_authorized"] is False
    assert preflight["maximum_provider_calls"] == 19894
    assert preflight["provider_balances_sufficient"] is False
    assert preflight["provider_balance_failures"] == ["openrouter"]


def test_completion_mutations_are_balanced_and_invalid(configured_stage) -> None:
    assets = configured_stage.load_assets(completion.CONFIGURATION["INSTRUMENT_PATH"])
    mutations = configured_stage._build_mutations(assets)

    assert len(mutations) == 1800
    assert all(not item["deterministic"]["passed"] for item in mutations)
    assert Counter(item["mutation_type"] for item in mutations) == {
        "missing-citation": 300,
        "truncated-citation": 300,
        "paraphrased-citation": 300,
        "extra-supported-claim": 300,
        "invalid-claim-binding": 300,
        "invalid-source-binding": 300,
    }


def test_sqlite_journal_round_trip_preserves_resume_state(
    configured_stage, tmp_path
) -> None:
    assets = configured_stage.load_assets(completion.CONFIGURATION["INSTRUMENT_PATH"])
    output = tmp_path / "checkpoint.sqlite3"
    state = configured_stage._initial_state(assets, simulation=True)
    configured_stage._write_initial(output, state)
    state["canaries"]["author"] = {"status": "complete"}
    state["accounting"]["calls_attempted"] = 1
    state["accounting"]["calls_with_provider_response"] = 1
    state["accounting"]["latency_ms"].append(1.25)
    configured_stage._checkpoint(output, state, ("canary", "author"))

    loaded = configured_stage._load_resume(output, assets, simulation=True)

    assert loaded == state


def test_live_preflight_accepts_only_an_exact_credit_pause_resume(
    configured_stage, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assets = configured_stage.load_assets(completion.CONFIGURATION["INSTRUMENT_PATH"])
    output = tmp_path / "paused.sqlite3"
    state = configured_stage._initial_state(assets, simulation=False)
    state["status"] = "paused-insufficient-credit"
    state["pause_reason"] = "provider-reported-insufficient-credit"
    state["pause_role"] = "independent_reviewer"
    configured_stage._write_initial(output, state)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setattr(configured_stage, "_working_tree_dirty", lambda: False)

    preflight = configured_stage.build_preflight(
        assets,
        output_path=output,
        live_balances={"deepseek-official-api": 9.25, "openrouter": 9.0},
        resume=True,
    )

    assert preflight["resume_requested"] is True
    assert preflight["resume_checkpoint_valid"] is True
    assert preflight["output_ready"] is True


def test_credit_pause_is_durable_and_full_simulation_resumes(
    configured_stage, tmp_path
) -> None:
    assets = configured_stage.load_assets(completion.CONFIGURATION["INSTRUMENT_PATH"])
    output = tmp_path / "simulation.sqlite3"
    transports = configured_stage._simulation_transports(assets["instrument"])
    transports["author"] = PauseOnceTransport(transports["author"])

    paused = asyncio.run(
        configured_stage.execute(
            assets,
            transports=transports,
            output_path=output,
            simulation=True,
        )
    )
    durable = configured_stage._load_resume(output, assets, simulation=True)

    assert paused["status"] == "paused-insufficient-credit"
    assert durable["status"] == "paused-insufficient-credit"
    assert durable["accounting"]["calls_attempted"] == 1
    assert durable["accounting"]["calls_with_provider_response"] == 0

    result = asyncio.run(
        configured_stage.execute(
            assets,
            transports=transports,
            output_path=output,
            simulation=True,
            resume=True,
        )
    )

    assert result["status"] == "completed-keep"
    assert result["summary"]["machine_gates_passed"] is True
    assert result["summary"]["metrics"]["new_case_count"] == 9000
    assert result["summary"]["metrics"]["cumulative_case_count"] == 10000
    assert result["summary"]["metrics"]["provider_calls"] == 19803
    assert result["accounting"]["calls_attempted"] == 19803
    assert result["credit_pause_count"] == 1
    assert len(result["credit_pause_events"]) == 1
    assert result["summary"]["metrics"]["deterministic_acceptance_rate"] == 1
    assert result["summary"]["metrics"]["mutation_sensitivity"] == 1
    assert result["further_scale_authorized"] is False


def test_third_credit_pause_exceeds_bounded_continuation_limit(
    configured_stage, tmp_path
) -> None:
    assets = configured_stage.load_assets(completion.CONFIGURATION["INSTRUMENT_PATH"])
    output = tmp_path / "credit-limit.sqlite3"
    state = configured_stage._initial_state(assets, simulation=True)
    configured_stage._write_initial(output, state)

    for expected_count in (1, 2, 3):
        outcome = asyncio.run(
            configured_stage._safe_call(
                role="author",
                transport=AlwaysInsufficientCreditTransport(),
                system="health",
                prompt="health",
                task="health",
                schema=configured_stage.HEALTH_SCHEMA,
                validator=configured_stage._health_validator,
                state=state,
                instrument=assets["instrument"],
                output_path=output,
                stop_after_calls=None,
                checkpoint_callback=configured_stage._checkpoint,
            )
        )
        assert state["credit_pause_count"] == expected_count

    assert outcome["status"] == "provider-error"
    assert state["status"] == "invalid-execution"
    assert state["invalid_reason"] == "credit-resume-continuation-limit-reached"
