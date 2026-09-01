from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from src.digital_twin.evaluation import (
    CrossEngineEvaluationProgramV1,
    EngineOutcomeV1,
    ProductEngineBindingV1,
    hierarchical_engine_interval,
    paired_engine_difference_interval,
)
from scripts.governed_full_autonomy_v2_1_actual_product_runtime import (
    _engine_client,
)
from scripts.academic_factual_qa_open_10000_t0_adapter import _generator_transport
from scripts.cross_engine_factual import factual_manifest


SHA = hashlib.sha256(b"frozen").hexdigest()


def _engines() -> list[ProductEngineBindingV1]:
    return [
        ProductEngineBindingV1(
            engine_id="e0",
            provider="deterministic",
            planner_model="deterministic-policy",
            generator_model="deterministic-grounded-generator",
            input_price_usd_per_million=0,
            output_price_usd_per_million=0,
            dated_snapshot=True,
        ),
        ProductEngineBindingV1(
            engine_id="e1",
            provider="openai-direct",
            planner_model="gpt-5.4-nano-2026-03-17",
            generator_model="gpt-5.4-nano-2026-03-17",
            input_price_usd_per_million=0.20,
            output_price_usd_per_million=1.25,
            credential_environment_variable="OPENAI_API_KEY",
            returned_identity_must_equal="gpt-5.4-nano-2026-03-17",
            dated_snapshot=True,
        ),
        ProductEngineBindingV1(
            engine_id="e2",
            provider="openai-direct",
            planner_model="gpt-5.6-luna",
            generator_model="gpt-5.6-luna",
            input_price_usd_per_million=0.20,
            output_price_usd_per_million=1.20,
            credential_environment_variable="OPENAI_API_KEY",
            returned_identity_must_equal="gpt-5.6-luna",
            dated_snapshot=False,
        ),
        ProductEngineBindingV1(
            engine_id="e3",
            provider="openai-direct",
            planner_model="gpt-5.4-mini-2026-03-17",
            generator_model="gpt-5.4-mini-2026-03-17",
            input_price_usd_per_million=0.75,
            output_price_usd_per_million=4.50,
            credential_environment_variable="OPENAI_API_KEY",
            returned_identity_must_equal="gpt-5.4-mini-2026-03-17",
            dated_snapshot=True,
        ),
        ProductEngineBindingV1(
            engine_id="e4",
            provider="deepseek-direct",
            planner_model="deepseek-v4-flash",
            generator_model="deepseek-v4-flash",
            input_price_usd_per_million=0.44,
            output_price_usd_per_million=1.32,
            credential_environment_variable="DEEPSEEK_API_KEY",
            returned_identity_must_equal="deepseek-v4-flash",
            dated_snapshot=False,
        ),
        ProductEngineBindingV1(
            engine_id="e5",
            provider="openai-direct",
            planner_model="gpt-5.6-terra",
            generator_model="gpt-5.4-mini-2026-03-17",
            input_price_usd_per_million=0.75,
            output_price_usd_per_million=4.50,
            credential_environment_variable="OPENAI_API_KEY",
            returned_identity_must_equal="gpt-5.4-mini-2026-03-17",
            dated_snapshot=False,
        ),
    ]


def _program() -> CrossEngineEvaluationProgramV1:
    return CrossEngineEvaluationProgramV1(
        program_id="governed-full-autonomy-v2-1-cross-engine-evaluation-010",
        status="build-only",
        factual_public_sha256=SHA,
        factual_gold_sha256=SHA,
        factual_source_sha256=SHA,
        factual_control_selection_sha256=SHA,
        sealed_public_sha256=SHA,
        sealed_gold_sha256=SHA,
        sealed_source_sha256=SHA,
        known_public_sha256=SHA,
        known_gold_sha256=SHA,
        known_control_public_sha256=SHA,
        known_control_gold_sha256=SHA,
        known_source_sha256=SHA,
        known_candidate_rankings_sha256=SHA,
        known_control_rankings_sha256=SHA,
        autonomy_public_sha256=SHA,
        autonomy_gold_sha256=SHA,
        shared_prompt_sha256=SHA,
        shared_policy_sha256=SHA,
        shared_scorer="independent-autonomy-scorer-v2",
        engines=_engines(),
        conditions=[
            "t0-grounded-control",
            "t1-v1-reactive-control",
            "t1-v2-reactive",
            "t1-v2-autonomous",
        ],
        development_factual_cases=500,
        development_control_cases=100,
        autonomy_cases=820,
        sealed_confirmation_cases=1000,
        known_regression_candidate_cases=10000,
        known_regression_control_cases=1000,
        total_budget_usd=50,
    )


def test_program_binds_six_cheap_engines_and_same_evaluation() -> None:
    program = _program()

    assert [item.engine_id for item in program.engines] == [
        "e0",
        "e1",
        "e2",
        "e3",
        "e4",
        "e5",
    ]
    serialized = program.model_dump_json().casefold()
    assert "gpt-5.6-sol" not in serialized
    assert "openrouter" not in serialized
    assert program.paid_execution_authorized is False


def test_program_rejects_sol_even_when_other_fields_are_valid() -> None:
    with pytest.raises(ValidationError, match="excludes Sol"):
        _engines()[1].model_copy(update={"planner_model": "gpt-5.6-sol"})
        ProductEngineBindingV1(
            **{
                **_engines()[1].model_dump(),
                "planner_model": "gpt-5.6-sol",
            }
        )


def test_every_provider_engine_builds_its_exact_direct_transport() -> None:
    clients = {
        engine.engine_id: (
            _engine_client(engine, role="planner"),
            _engine_client(engine, role="generator"),
        )
        for engine in _engines()
        if engine.provider != "deterministic"
    }

    assert clients["e1"][0].model == "gpt-5.4-nano-2026-03-17"
    assert clients["e2"][1].model == "gpt-5.6-luna"
    assert clients["e3"][0].model == "gpt-5.4-mini-2026-03-17"
    assert clients["e4"][0].model == "deepseek/deepseek-v4-flash"
    assert clients["e5"][0].model == "gpt-5.6-terra"
    assert clients["e5"][1].model == "gpt-5.4-mini-2026-03-17"


def test_factual_adapter_uses_first_party_engine_transport() -> None:
    openai_engine = _engines()[1]
    deepseek_engine = _engines()[4]
    openai_binding, _openai_transport = _generator_transport(
        factual_manifest(openai_engine, control=False, code_revision="0" * 40),
        {"product_engine_binding": openai_engine.model_dump(mode="json")},
    )
    deepseek_binding, _deepseek_transport = _generator_transport(
        factual_manifest(deepseek_engine, control=False, code_revision="0" * 40),
        {"product_engine_binding": deepseek_engine.model_dump(mode="json")},
    )

    assert openai_binding["api_url"] == "https://api.openai.com/v1/responses"
    assert openai_binding["provider_model"] == "gpt-5.4-nano-2026-03-17"
    assert deepseek_binding["api_url"] == "https://api.deepseek.com/chat/completions"
    assert deepseek_binding["provider_model"] == "deepseek-v4-flash"
    assert deepseek_binding["maximum_transport_retries"] == 0


def test_cluster_bootstrap_and_paired_difference_preserve_pairing() -> None:
    left = [
        EngineOutcomeV1(
            engine_id="e1",
            condition="t1-v2-autonomous",
            case_id=f"case-{index}",
            cluster_id=f"cluster-{index // 2}",
            safe_grounded_autonomous_success=index != 0,
            cost_usd=0.001,
            latency_ms=20,
        )
        for index in range(20)
    ]
    right = [
        item.model_copy(
            update={
                "engine_id": "e2",
                "safe_grounded_autonomous_success": index > 3,
            }
        )
        for index, item in enumerate(left)
    ]

    interval = hierarchical_engine_interval(left, replicates=1_000)
    paired = paired_engine_difference_interval(left, right, replicates=1_000)

    assert interval["case_count"] == 20
    assert interval["cluster_count"] == 10
    assert paired["difference"] > 0


def test_paired_difference_rejects_unpaired_cases() -> None:
    row = EngineOutcomeV1(
        engine_id="e1",
        condition="t1-v2-autonomous",
        case_id="case-a",
        cluster_id="cluster-a",
        safe_grounded_autonomous_success=True,
        cost_usd=0,
        latency_ms=1,
    )
    with pytest.raises(ValueError, match="same non-empty case IDs"):
        paired_engine_difference_interval([row], [], replicates=1_000)
