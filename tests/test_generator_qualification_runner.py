import pytest
from pathlib import Path

from src.digital_twin.grounding import GenerationUsage
from src.digital_twin.llm import LlmResponse
from scripts.run_generator_qualification import (
    GeneratorQualificationError,
    _actual_action,
    _term_present,
    build_preflight,
    execute,
    validate_assets,
)


def test_generator_qualification_assets_are_frozen_and_balanced():
    assets = validate_assets()

    assert len(assets["datasets"]["development"]["dataset"]["cases"]) == 48
    assert assets["datasets"]["heldout"]["dataset"] is None
    assert assets["datasets"]["heldout"]["case_count"] == 104
    assert assets["freeze"]["heldout_access_state"] == "sealed-unopened"
    assert assets["instrument"]["candidate_binding"]["litellm_model"] == (
        "deepseek/deepseek-v4-flash"
    )


def test_generator_stability_instrument_freezes_subset_and_revision():
    assets = validate_assets(
        Path(
            "research/05_evaluation/instruments/"
            "generator_qualification_v1_development_stability_001.json"
        )
    )
    protocol = assets["instrument"]["stability_protocol"]

    assert len(protocol["case_ids"]) == 12
    assert len(set(protocol["case_ids"])) == 12
    assert protocol["repeats"] == 3
    assert (
        assets["instrument"]["candidate_binding"]["expected_provider_revision"]
        == "fp_a18b46594c_prod0820_fp8_kvcache_20260402"
    )
    assert assets["datasets"]["heldout"]["dataset"] is None


def test_generator_heldout_instrument_freezes_selected_p2_and_hash():
    assets = validate_assets(
        Path(
            "research/05_evaluation/instruments/"
            "generator_qualification_v1_heldout_001.json"
        )
    )
    instrument = assets["instrument"]

    assert [item["condition_id"] for item in instrument["prompt_candidates"]] == ["P2"]
    assert (
        instrument["dataset"]["heldout_sha256"]
        == assets["datasets"]["heldout"]["sha256"]
    )
    assert instrument["authorization"]["scope"].startswith("one-time P2")
    assert assets["datasets"]["heldout"]["dataset"] is None


def test_generator_qualification_preflight_never_emits_credential(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-secret-value")

    preflight = build_preflight(validate_assets())

    assert preflight["status"] == "ready-for-development-execution"
    assert preflight["credential_present"] is True
    assert preflight["credential_value_emitted"] is False
    assert "synthetic-secret-value" not in str(preflight)
    assert preflight["heldout_execution_enabled"] is False


def test_generator_qualification_rejects_unsafe_presented_evidence():
    from scripts.run_generator_qualification import _validate_case

    assets = validate_assets()
    case = assets["datasets"]["development"]["dataset"]["cases"][0]
    unsafe = {
        **case,
        "candidate_evidence": [dict(item) for item in case["candidate_evidence"]],
    }
    unsafe["candidate_evidence"][-2]["presented"] = True

    with pytest.raises(GeneratorQualificationError, match="unsafe evidence"):
        _validate_case(unsafe)


def test_generator_qualification_analysis_handles_inflection_and_action_scope():
    assert _term_present("rotated", "The marker rotates after authentication.")
    assert (
        _actual_action(
            "answer",
            "There are two meanings. Which context are you asking about?",
            scenario_type="ambiguity",
        )
        == "clarify"
    )
    assert (
        _actual_action(
            "answer",
            "The current token is indigo. Can you confirm which token you use?",
            scenario_type="permission_version",
        )
        == "answer"
    )


@pytest.mark.asyncio
async def test_generator_qualification_execution_adapter_records_revision(monkeypatch):
    class FixtureClient:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, messages, task):
            assert task == "grounded_tutor_answer"
            return LlmResponse(
                content=(
                    '{"answer":"The session marker is rotated after '
                    'authentication.","citation_ids":["S1"]}'
                ),
                provider_model="deepseek-v4-flash",
                provider_revision="fp-fixture-v1",
                usage=GenerationUsage(
                    input_tokens=100,
                    output_tokens=20,
                    total_tokens=120,
                    approximate_cost_usd=0.0001,
                ),
            )

    monkeypatch.setattr(
        "scripts.run_generator_qualification.LiteLlmClient",
        FixtureClient,
    )
    assets = validate_assets()
    assets["datasets"]["development"]["dataset"] = {
        **assets["datasets"]["development"]["dataset"],
        "cases": [assets["datasets"]["development"]["dataset"]["cases"][0]],
    }

    result = await execute(
        assets,
        split="development",
        prompt_conditions=["P0"],
    )

    assert result["case_attempts"] == 1
    assert result["deterministic_check_passes"] == 1
    assert result["provider_revisions"] == ["fp-fixture-v1"]
    assert result["cumulative_cost_usd"] == pytest.approx(0.0001)
