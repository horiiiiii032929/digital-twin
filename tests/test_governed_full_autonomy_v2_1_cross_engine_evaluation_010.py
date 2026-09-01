from __future__ import annotations

import json

from scripts import (
    build_governed_full_autonomy_v2_1_cross_engine_evaluation_010 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_cross_engine_evaluation_010 as runner,
)


def test_cross_engine_program_is_finite_identical_and_terminal() -> None:
    result = builder.validate()

    assert result["status"] == (
        "passed-terminal-completed-refine-provider-unauthorized"
    )
    assert result["engine_ids"] == ["e0", "e1", "e2", "e3", "e4", "e5"]
    assert result["condition_count"] == 4
    assert result["development_factual_cases"] == 500
    assert result["development_control_cases"] == 100
    assert result["autonomy_cases_per_engine"] == 820
    assert result["paid_execution_authorized"] is False
    assert result["provider_calls"] == 0
    assert result["factual_rankings"]["candidate_sha256"]
    assert result["factual_rankings"]["control_sha256"]
    assert result["factual_rankings"]["sealed_sha256"]
    assert result["factual_rankings"]["known_candidate_sha256"]
    assert result["factual_rankings"]["known_control_sha256"]


def test_sealed_and_known_packages_are_frozen_before_paid_execution() -> None:
    program = builder.load_program()
    cases, gold, chunks = builder.sealed_inputs()

    assert len(cases) == len(gold) == 1_000
    assert len(chunks) == 600
    assert builder._file_sha(builder.SEALED_PUBLIC) == program.sealed_public_sha256
    assert builder._file_sha(builder.KNOWN_PUBLIC) == program.known_public_sha256
    assert len(builder.known_rankings(control=False)["ranked_chunk_ids"]) == 10_000
    assert len(builder.known_rankings(control=True)["ranked_chunk_ids"]) == 1_000


def test_factual_control_freezes_twenty_complete_clusters() -> None:
    cases, _gold, _chunks = builder.factual_inputs()
    selected = set(builder.factual_control_case_ids())
    rows = [row for row in cases if row.case_id in selected]

    assert len(rows) == 100
    assert len({row.cluster_id for row in rows}) == 20
    assert all(
        sum(row.cluster_id == cluster_id for row in rows) == 5
        for cluster_id in {row.cluster_id for row in rows}
    )


def test_active_program_excludes_expensive_or_retired_engine_paths() -> None:
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))
    serialized = json.dumps(instrument["engines"]).casefold()

    assert "gpt-5.6-sol" not in serialized
    assert "openrouter" not in serialized
    assert "gemma" not in serialized
    assert "claude" not in serialized
    assert instrument["engines"][4]["provider"] == "deepseek-direct"
    assert instrument["engines"][4]["input_price_usd_per_million"] == 0.44
    assert instrument["engines"][4]["output_price_usd_per_million"] == 1.32


def test_program_simulation_has_one_way_stage_progression() -> None:
    result = builder.simulate()

    assert result["status"] == "passed-network-free-program-simulation"
    assert len(result["stages"]) == 6
    assert result["finite_stop_rules"]["harness_correction_max"] == 1
    assert result["finite_stop_rules"]["sealed_set_tuning"] is False
    assert result["quality_claim"] is False


def test_live_preflight_rejects_revoked_terminal_authority(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setattr(runner, "_git_dirty", lambda: False)
    monkeypatch.setattr(runner, "PROGRAM_RESULT", tmp_path / "result.json")
    result = runner.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert "program-paid-execution-not-authorized" in result["blockers"]
    assert "program-not-frozen-for-execution" in result["blockers"]
    assert result["provider_calls"] == 0


def test_independent_actual_product_simulation_ignores_self_reported_flags() -> None:
    result = runner.simulate(limit=4)

    assert result["status"] == "passed-independent-network-free-simulation"
    assert result["case_count"] == 4
    assert result["summary"]["safe_grounded_autonomous_success"] == 1.0
    assert result["provider_calls"] == 0
