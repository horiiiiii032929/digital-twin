from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest

import scripts.execute_academic_factual_qa_panel_review_v2 as panel_executor

from scripts.execute_academic_factual_qa_panel_review_v2 import (
    PanelExecutionError,
    ProviderBatchResult,
    ProviderCallFailure,
    _maximum_call_cost,
    _simulated_codex_artifact,
    build_preflight,
    estimate_input_tokens,
    load_assets,
    load_binding,
    parse_votes,
    prepare_codex_workspace,
    require_execution_authorized,
    response_schema,
    simulate_full,
    validate_codex_votes,
    execute_calibration,
)
from scripts.run_academic_factual_qa_panel_review_v2 import REVIEWER_IDS


def test_reviewer_binding_freezes_current_models_routing_and_peak_cost() -> None:
    binding = load_binding()
    reviewers = {row["reviewer_id"]: row for row in binding["reviewers"]}

    assert reviewers[REVIEWER_IDS[0]]["provider_model"] == "gpt-5.6-sol"
    assert reviewers[REVIEWER_IDS[0]]["reasoning_effort"] == "medium"
    assert reviewers[REVIEWER_IDS[1]]["provider_model"] == (
        "mistralai/mistral-small-2603"
    )
    assert reviewers[REVIEWER_IDS[1]]["routing"] == {
        "only": ["Mistral"],
        "order": ["Mistral"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
        "zdr": True,
    }
    assert reviewers[REVIEWER_IDS[2]]["documented_revision"] == (
        "DeepSeek-V4-Pro-0813"
    )
    maximum = sum(
        _maximum_call_cost(binding, reviewer_id) * 60
        for reviewer_id in REVIEWER_IDS[1:]
    )
    assert maximum == pytest.approx(1.5630336)
    assert maximum <= binding["cost_guard"]["conservative_peak_reservation_usd"]
    assert maximum < binding["cost_guard"]["emergency_hard_stop_usd"]


def test_every_frozen_batch_fits_the_conservative_input_limit() -> None:
    assets = load_assets()
    items = assets["packet"]["items"]
    maximum = assets["binding"]["execution_contract"][
        "maximum_input_tokens_per_call"
    ]

    estimates = [
        estimate_input_tokens(items[index : index + 4])
        for index in range(0, len(items), 4)
    ]

    assert max(estimates) <= maximum


def test_vote_response_parser_is_strict_and_order_stable() -> None:
    assets = load_assets()
    items = assets["packet"]["items"][:2]
    item_ids = [row["review_item_id"] for row in items]
    schema = response_schema(item_ids)
    assert schema["properties"]["votes"]["minItems"] == 2
    vote = {
        "case_semantically_valid": True,
        "expected_action": "answer",
        "question_answerable_from_supplied_sources": True,
        "atomic_claim_support": "fully-supported",
        "citation_support": "complete-valid",
        "boundary_reason": None,
        "ambiguity_detected": False,
        "evidence_ids": ["evidence-1"],
        "defect_types": [],
        "concise_rationale": "The visible source supports the candidate record.",
    }
    content = json.dumps(
        {
            "votes": [
                {"review_item_id": item_ids[1], **vote},
                {"review_item_id": item_ids[0], **vote},
            ]
        }
    )

    assert [row["review_item_id"] for row in parse_votes(content, items)] == item_ids
    with pytest.raises(PanelExecutionError, match="vote count"):
        parse_votes(json.dumps({"votes": []}), items)


def test_codex_workspace_contains_only_blinded_phase_packets(tmp_path: Path) -> None:
    assets = load_assets()
    workspace = tmp_path / "isolated-codex"

    result = prepare_codex_workspace(assets, workspace)

    assert result["status"] == "prepared-no-review-call"
    assert result["provider_calls"] == 0
    assert result["contains_hidden_truth"] is False
    assert result["files"] == [
        "REVIEW_INSTRUCTIONS.md",
        "calibration-packet.json",
        "confirmation-packet.json",
    ]
    serialized = "\n".join(path.read_text() for path in workspace.iterdir())
    for forbidden in (
        '"expected_action"',
        '"canonical_answer"',
        '"planted_mutation"',
        '"case_id"',
        '"cluster_id"',
    ):
        assert forbidden not in serialized


def test_codex_phase_artifacts_require_one_constant_isolated_task(tmp_path: Path) -> None:
    assets = load_assets()
    calibration = tmp_path / "calibration.json"
    confirmation = tmp_path / "confirmation.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=calibration)
    _simulated_codex_artifact(assets, item_kind="confirmation", path=confirmation)

    first = validate_codex_votes(
        calibration, packet=assets["packet"], item_kind="calibration"
    )
    second = validate_codex_votes(
        confirmation,
        packet=assets["packet"],
        item_kind="confirmation",
        expected_task_id=first["task_id"],
    )
    assert len(first["votes"]) == 40
    assert len(second["votes"]) == 200

    changed = json.loads(confirmation.read_text())
    changed["task_id"] = "different-task"
    without_hash = {key: value for key, value in changed.items() if key != "content_sha256"}
    from scripts.build_academic_factual_qa_confirmation_v2 import canonical_sha256

    changed["content_sha256"] = canonical_sha256(without_hash)
    confirmation.write_text(json.dumps(changed))
    with pytest.raises(PanelExecutionError, match="changed between phases"):
        validate_codex_votes(
            confirmation,
            packet=assets["packet"],
            item_kind="confirmation",
            expected_task_id=first["task_id"],
        )


def test_network_free_preflight_recognizes_calibration_only_authority(
    tmp_path: Path,
) -> None:
    result = build_preflight(
        load_assets(), live=False, codex_votes_path=tmp_path / "missing-votes.json"
    )

    assert result["status"] == "blocked-not-authorized"
    assert "calibration-execution-not-authorized" not in result["blockers"]
    assert "bounded-freeze-authorization-missing" not in result["blockers"]
    assert "instrument-not-frozen-for-execution" not in result["blockers"]
    assert "reviewer-metadata-not-current" in result["blockers"]
    assert "codex-calibration-votes-missing" in result["blockers"]
    assert result["provider_or_model_calls"] == 0
    assert result["credential_values_emitted"] is False


def test_execution_command_rechecks_authority_before_a_provider_call(
    tmp_path: Path,
) -> None:
    assets = load_assets()
    assets["instrument"]["status"] = "frozen-pending-execution"
    assets["instrument"]["execution_safety"][
        "calibration_execution_authorized"
    ] = False
    codex = tmp_path / "codex-calibration.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=codex)

    with pytest.raises(PanelExecutionError, match="not authorized"):
        require_execution_authorized(
            assets,
            phase="calibration",
            output_path=tmp_path / "ledger.json",
            codex_votes_path=codex,
            resume=False,
        )


def test_calibration_authority_does_not_require_confirmation_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assets = deepcopy(load_assets())
    assets["instrument"]["status"] = "frozen-pending-execution"
    for key in (
        "calibration_execution_authorized",
        "codex_review_authorized",
        "provider_review_authorized",
        "paid_execution_authorized",
    ):
        assets["instrument"]["execution_safety"][key] = True
    assert (
        assets["instrument"]["execution_safety"][
            "confirmation_execution_authorized"
        ]
        is False
    )
    for key in (
        "codex_review_authorized",
        "provider_review_authorized",
        "paid_execution_authorized",
    ):
        assets["binding"]["authorization"][key] = True
    assert assets["binding"]["authorization"]["confirmation_review_authorized"] is False
    monkeypatch.setattr(
        panel_executor,
        "BOUNDED_PILOT_AUTHORIZATIONS",
        {panel_executor.INSTRUMENT_ID: ("external_model_evaluation",)},
    )
    monkeypatch.setattr(panel_executor, "live_metadata_failures", lambda _: [])
    monkeypatch.setattr(panel_executor, "_working_tree_dirty", lambda: False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "present")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "present")

    result = build_preflight(
        assets,
        live=True,
        output_path=tmp_path / "unused-ledger.json",
        codex_votes_path=tmp_path / "missing-votes.json",
    )

    assert "calibration-execution-not-authorized" not in result["blockers"]
    assert "instrument-not-frozen-for-execution" not in result["blockers"]
    assert "bounded-freeze-authorization-missing" not in result["blockers"]
    assert result["blockers"] == ["codex-calibration-votes-missing"]


def test_full_network_free_execution_simulation_reaches_bounded_audit(
    tmp_path: Path,
) -> None:
    result = asyncio.run(simulate_full(load_assets(), tmp_path / "simulation"))

    assert result["status"] == "ready-researcher-audit"
    assert result["provider_calls"] == 120
    assert len(result["provider_call_records"]) == 120
    assert result["reported_cost_usd"] == pytest.approx(0.12)
    assert result["aggregate"]["unanimous_case_count"] == 200
    assert result["aggregate"]["researcher_packet_case_count"] == 20


class _MalformedTransport:
    async def call(self, **_: object) -> ProviderBatchResult:
        return ProviderBatchResult(
            content="{}",
            provider_model="mistralai/mistral-small-2603",
            provider_revision=None,
            provider_name="Mistral",
            input_tokens=100,
            output_tokens=10,
            cost_usd=0.001,
            latency_ms=1.0,
        )


class _ProviderErrorTransport:
    async def call(self, **_: object) -> ProviderBatchResult:
        raise ProviderCallFailure(
            "provider-http-error",
            {
                "http_status": 400,
                "request_id": "request-public-id",
                "provider_error_code": "invalid_schema",
                "provider_error_message": "Schema feature is unsupported.",
                "latency_ms": 2.0,
                "cost_accounting_status": "unavailable-provider-error",
            },
        )


def test_malformed_provider_batch_is_recorded_once_without_retry(
    tmp_path: Path,
) -> None:
    assets = load_assets()
    codex = tmp_path / "codex-calibration.json"
    ledger = tmp_path / "ledger.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=codex)

    result = asyncio.run(
        execute_calibration(
            assets,
            codex_votes_path=codex,
            output_path=ledger,
            transport=_MalformedTransport(),
            simulation=True,
            resume=False,
        )
    )

    assert result["status"] == "invalid-execution"
    assert result["provider_calls"] == 1
    assert len(result["provider_call_records"]) == 1
    assert result["malformed_response_count"] == 1
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 10
    assert result["reported_cost_usd"] == pytest.approx(0.001)
    assert result["provider_call_records"][0]["cost_accounting_status"] == "complete"
    assert result["provider_call_records"][0]["response_content_sha256"]


def test_provider_http_failure_preserves_sanitized_diagnostics_without_retry(
    tmp_path: Path,
) -> None:
    assets = load_assets()
    codex = tmp_path / "codex-calibration.json"
    ledger = tmp_path / "ledger.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=codex)

    result = asyncio.run(
        execute_calibration(
            assets,
            codex_votes_path=codex,
            output_path=ledger,
            transport=_ProviderErrorTransport(),
            simulation=True,
            resume=False,
        )
    )

    assert result["status"] == "invalid-execution"
    assert result["provider_calls"] == 1
    record = result["provider_call_records"][0]
    assert record["category"] == "provider-http-error"
    assert record["http_status"] == 400
    assert record["request_id"] == "request-public-id"
    assert record["provider_error_code"] == "invalid_schema"
    assert record["cost_accounting_status"] == "unavailable-provider-error"
