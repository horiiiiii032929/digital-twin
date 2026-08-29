from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import ValidationError
import pytest

from scripts.run_academic_factual_qa_t0_confirmation import (
    AtomicCheckpointLlmClient,
    CONDITIONS,
    VISUAL_CONDITIONS,
    ProductInput,
    T0OperationalExecutionError,
    _main_chunks,
    execute,
    preflight,
    validate_instrument,
)
from scripts.build_academic_factual_qa_visual_supplement import build_dataset
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmIdentityDriftError, LlmMessage, LlmResponse


def test_product_input_firewall_rejects_every_gold_field() -> None:
    assert ProductInput(course_id="course-1", question="What is paging?")
    for field, value in (
        ("required_source_ids", ["source-1"]),
        ("expected_action", "answer"),
        ("canonical_answer", "gold"),
        ("evidence", ["gold"]),
    ):
        with pytest.raises(ValidationError):
            ProductInput.model_validate(
                {"course_id": "course-1", "question": "Question?", field: value}
            )


def test_full_course_corpus_reconstructs_all_frozen_public_sections() -> None:
    checkpoint = validate_instrument()
    chunks = _main_chunks(checkpoint["manifest"])

    assert set(chunks) == {
        "operating-systems",
        "computer-networking",
        "data-structures",
        "python-programming",
    }
    assert sum(len(rows) for rows in chunks.values()) == 160
    assert all(chunk.source_checksum for rows in chunks.values() for chunk in rows)


def test_t0_preflight_stops_before_any_provider_call(tmp_path: Path) -> None:
    result = preflight(
        output=tmp_path / "t0.json",
        panel_ledger=tmp_path / "panel.json",
        audit_result=tmp_path / "audit.json",
        visual_result=tmp_path / "visual.json",
    )

    assert result["status"] == "blocked-not-authorized"
    assert "live-t0-not-authorized" in result["blockers"]
    assert "bounded-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["gold_opened"] is False


def test_network_free_t0_simulation_exercises_real_service_without_academic_claim(
    tmp_path: Path,
) -> None:
    build_dataset(write_assets=True)
    output = tmp_path / "t0-simulation.json"
    result = asyncio.run(
        execute(
            live=False,
            visual_result=tmp_path / "no-visual-result.json",
            output=output,
        )
    )

    assert result["status"] in {
        "simulation-completed-keep",
        "simulation-completed-refine",
    }
    assert result["execution_mode"] == "network-free-simulation"
    assert result["academic_interpretation_allowed"] is False
    assert result["paid_provider_calls"] == 0
    assert result["provider_calls"] <= 520
    assert set(result["condition_summaries"]) == {
        *CONDITIONS,
        *VISUAL_CONDITIONS,
    }
    assert result["gold_fields_in_product_input"] == 0
    assert result["gold_opened_only_after_persistence"] is True
    assert result["normalized_question_duplicate_count"] == 0
    assert result["paired_supported_retention"]["cluster_count"] == 100
    assert result["paired_supported_retention"]["replicates"] == 10_000
    assert all(
        summary["persistence_mismatch_count"] == 0
        for summary in result["condition_summaries"].values()
    )
    assert output.is_file()


def test_atomic_provider_checkpoint_replays_without_a_second_call(
    tmp_path: Path,
) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls = 0

        async def chat(self, messages, task):
            self.calls += 1
            return LlmResponse(
                content='{"answer":"grounded","citation_ids":["S1"]}',
                provider_model="deepseek-v4-flash",
                provider_revision="fp_a18b46594c_prod0820_fp8_kvcache_20260402",
                usage=GenerationUsage(
                    input_tokens=10,
                    output_tokens=5,
                    total_tokens=15,
                    approximate_cost_usd=0.001,
                ),
            )

    binding = validate_instrument()["provider_binding"]
    path = tmp_path / "provider-ledger.json"
    message = [LlmMessage(role="user", content="synthetic public prompt")]
    first_transport = FakeClient()
    first = AtomicCheckpointLlmClient(
        first_transport,
        binding=binding,
        role="control",
        path=path,
        max_calls=2,
        max_cost_usd=1.0,
        resume=False,
    )
    original = asyncio.run(first.chat(message, "grounded_tutor_answer"))
    second_transport = FakeClient()
    resumed = AtomicCheckpointLlmClient(
        second_transport,
        binding=binding,
        role="control",
        path=path,
        max_calls=2,
        max_cost_usd=1.0,
        resume=True,
    )
    replay = asyncio.run(resumed.chat(message, "grounded_tutor_answer"))

    assert original == replay
    assert first_transport.calls == 1
    assert second_transport.calls == 0
    assert resumed.snapshot()["replayed_calls"] == 1


def test_atomic_provider_checkpoint_records_identity_drift_and_stops(
    tmp_path: Path,
) -> None:
    class DriftClient:
        async def chat(self, messages, task):
            raise LlmIdentityDriftError(
                provider_model="deepseek-v4-pro",
                provider_revision="unexpected",
            )

    client = AtomicCheckpointLlmClient(
        DriftClient(),
        binding=validate_instrument()["provider_binding"],
        role="control",
        path=tmp_path / "provider-ledger.json",
        max_calls=2,
        max_cost_usd=1.0,
        resume=False,
    )

    with pytest.raises(LlmIdentityDriftError):
        asyncio.run(
            client.chat(
                [LlmMessage(role="user", content="synthetic public prompt")],
                "grounded_tutor_answer",
            )
        )
    assert client.snapshot()["status"] == "invalid-execution"
    assert client.terminal_failure["returned_provider_model"] == "deepseek-v4-pro"


def test_atomic_provider_checkpoint_stops_before_call_when_budget_is_exhausted(
    tmp_path: Path,
) -> None:
    class FailIfCalledClient:
        def __init__(self) -> None:
            self.calls = 0

        async def chat(self, messages, task):
            self.calls += 1
            raise AssertionError("budget stop must occur before provider transport")

    transport = FailIfCalledClient()
    client = AtomicCheckpointLlmClient(
        transport,
        binding=validate_instrument()["provider_binding"],
        role="control",
        path=tmp_path / "provider-ledger.json",
        max_calls=2,
        max_cost_usd=0.0,
        resume=False,
    )

    with pytest.raises(T0OperationalExecutionError, match="pre-call-budget-stop"):
        asyncio.run(
            client.chat(
                [LlmMessage(role="user", content="synthetic public prompt")],
                "grounded_tutor_answer",
            )
        )
    assert transport.calls == 0
    assert client.snapshot()["status"] == "invalid-execution"
    assert client.snapshot()["calls"] == 0
