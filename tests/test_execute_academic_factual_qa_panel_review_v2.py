from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest

import scripts.execute_academic_factual_qa_panel_review_v2 as panel_executor

from scripts.execute_academic_factual_qa_panel_review_v2 import (
    ATTEMPT_003_PATH,
    ATTEMPT_004_PATH,
    PanelExecutionError,
    ProviderBatchResult,
    ProviderCallFailure,
    _failure_is_retryable,
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
from scripts.run_academic_factual_qa_panel_review_v2 import (
    GEMINI_REVIEWER_IDS,
    REVIEWER_IDS,
    TWO_REVIEWER_IDS,
    aggregate_panel,
    build_simulated_ledger,
)


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


def test_attempt_003_binding_pins_gemini_standard_endpoint_and_cost() -> None:
    assets = load_assets(ATTEMPT_003_PATH)
    binding = assets["binding"]
    reviewers = {row["reviewer_id"]: row for row in binding["reviewers"]}

    assert assets["attempt_id"] == panel_executor.ATTEMPT_003_ID
    assert assets["reviewer_ids"] == GEMINI_REVIEWER_IDS
    gemini = reviewers[GEMINI_REVIEWER_IDS[1]]
    assert gemini["provider_model"] == "google/gemini-3.7-flash"
    assert gemini["documented_revision"] == "google/gemini-3.7-flash-20260813"
    assert gemini["endpoint_tag"] == "google-ai-studio"
    assert gemini["routing"] == {
        "only": ["google-ai-studio"],
        "order": ["google-ai-studio"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }
    assert gemini["provider_policy"]["retentionDays"] == 55
    maximum = sum(
        _maximum_call_cost(binding, reviewer_id) * 10
        for reviewer_id in GEMINI_REVIEWER_IDS[1:]
    )
    assert maximum == pytest.approx(0.4064256)
    assert maximum <= binding["cost_guard"]["conservative_peak_reservation_usd"]


def test_attempt_004_binding_has_only_codex_and_gemini_with_bounded_retries() -> None:
    assets = load_assets(ATTEMPT_004_PATH)
    binding = assets["binding"]

    assert assets["reviewer_ids"] == TWO_REVIEWER_IDS
    assert binding["execution_contract"]["maximum_primary_provider_calls"] == 10
    assert binding["execution_contract"]["maximum_transport_retries"] == 2
    assert binding["execution_contract"]["maximum_retries_per_batch"] == 1
    assert binding["execution_contract"]["maximum_provider_calls"] == 12
    assert binding["cost_guard"]["conservative_peak_reservation_usd"] == (
        pytest.approx(0.211968)
    )
    serialized = json.dumps(binding, sort_keys=True).lower()
    assert "deepseek" not in serialized
    assert {
        row.get("credential_environment_variable")
        for row in binding["reviewers"]
        if row.get("credential_environment_variable")
    } == {"OPENROUTER_API_KEY"}


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ProviderCallFailure("provider-timeout", {}), True),
        (ProviderCallFailure("provider-connection-failure", {}), True),
        (ProviderCallFailure("provider-empty-content", {}), True),
        (ProviderCallFailure("provider-http-error", {"http_status": 429}), True),
        (ProviderCallFailure("provider-http-error", {"http_status": 503}), True),
        (ProviderCallFailure("provider-http-error", {"http_status": 400}), False),
        (PanelExecutionError("provider response is not JSON"), False),
        (PanelExecutionError("provider runtime identity drifted"), False),
    ],
)
def test_attempt_004_retry_eligibility_is_transport_only(
    error: Exception, expected: bool
) -> None:
    contract = load_assets(ATTEMPT_004_PATH)["binding"]["execution_contract"]
    assert _failure_is_retryable(error, contract) is expected


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
        "evidence_ids": [],
        "defect_types": [],
        "concise_rationale": "The visible source supports the candidate record.",
    }
    content = json.dumps(
        {
            "votes": [
                {
                    "review_item_id": item_ids[1],
                    **vote,
                    "evidence_ids": [items[1]["provided_sources"][0]["evidence_id"]],
                },
                {
                    "review_item_id": item_ids[0],
                    **vote,
                    "evidence_ids": [items[0]["provided_sources"][0]["evidence_id"]],
                },
            ]
        }
    )

    assert [row["review_item_id"] for row in parse_votes(content, items)] == item_ids
    with pytest.raises(PanelExecutionError, match="vote count"):
        parse_votes(json.dumps({"votes": []}), items)


def test_gemini_schema_defers_unsupported_constraints_to_local_validation() -> None:
    schema = response_schema(["review-1", "review-2"], gemini_compatible=True)
    serialized = json.dumps(schema)

    for forbidden in ("uniqueItems", "minItems", "maxItems", "minLength", "maxLength"):
        assert forbidden not in serialized


def test_local_vote_validation_rejects_duplicate_defects_and_unknown_evidence() -> None:
    items = load_assets(ATTEMPT_003_PATH)["packet"]["items"][:1]
    item_id = items[0]["review_item_id"]
    vote = {
        "review_item_id": item_id,
        "case_semantically_valid": False,
        "expected_action": "answer",
        "question_answerable_from_supplied_sources": True,
        "atomic_claim_support": "unsupported",
        "citation_support": "invalid",
        "boundary_reason": None,
        "ambiguity_detected": False,
        "evidence_ids": ["unknown-evidence"],
        "defect_types": ["citation"],
        "concise_rationale": "The visible citation does not support the answer.",
    }
    with pytest.raises(PanelExecutionError, match="unknown visible evidence"):
        parse_votes(json.dumps({"votes": [vote]}), items)

    vote["evidence_ids"] = [items[0]["provided_sources"][0]["evidence_id"]]
    vote["defect_types"] = ["citation", "citation"]
    with pytest.raises(PanelExecutionError, match="defect types must be unique"):
        parse_votes(json.dumps({"votes": [vote]}), items)


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


def test_network_free_preflight_preserves_revoked_invalid_attempt(
    tmp_path: Path,
) -> None:
    result = build_preflight(
        load_assets(), live=False, codex_votes_path=tmp_path / "missing-votes.json"
    )

    assert result["status"] == "blocked-not-authorized"
    assert "calibration-execution-not-authorized" in result["blockers"]
    assert "bounded-freeze-authorization-missing" in result["blockers"]
    assert "instrument-not-frozen-for-execution" in result["blockers"]
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


def test_attempt_003_simulation_runs_two_canaries_then_stops_after_calibration(
    tmp_path: Path,
) -> None:
    result = asyncio.run(
        simulate_full(load_assets(ATTEMPT_003_PATH), tmp_path / "simulation-003")
    )

    assert result["status"] == "completed-go-deeper"
    assert result["provider_calls"] == 20
    assert [
        row["reviewer_id"] for row in result["provider_call_records"][:2]
    ] == list(GEMINI_REVIEWER_IDS[1:])
    assert set(result["calibration"]) == set(GEMINI_REVIEWER_IDS)
    assert all(row["passed"] for row in result["calibration"].values())
    assert result["aggregate"] is None


def test_attempt_004_simulation_reruns_all_40_gemini_controls(
    tmp_path: Path,
) -> None:
    output = tmp_path / "simulation-004"
    result = asyncio.run(simulate_full(load_assets(ATTEMPT_004_PATH), output))

    assert result["status"] == "completed-go-deeper"
    assert result["provider_calls"] == 10
    assert result["transport_retry_count"] == 0
    assert result["recovered_transport_failure_count"] == 0
    assert set(result["calibration"]) == set(TWO_REVIEWER_IDS)
    assert all(row["passed"] for row in result["calibration"].values())
    assert sum(
        row["reviewer_id"] == TWO_REVIEWER_IDS[1] for row in result["votes"]
    ) == 40
    assert all(
        "attempt-003" not in json.dumps(row)
        for row in result["provider_call_records"]
    )


def test_two_reviewer_confirmation_aggregation_applies_frozen_agreement_gates() -> None:
    packet, ledger = build_simulated_ledger("pass", reviewer_ids=TWO_REVIEWER_IDS)
    result = aggregate_panel(
        ledger=ledger, packet=packet, reviewer_ids=TWO_REVIEWER_IDS
    )

    assert result["status"] == "ready-researcher-audit"
    assert result["passing_reviewer_count"] == 2
    assert result["unanimous_semantic_agreement_rate"] == 1.0
    assert result["action_krippendorff_alpha"] == 1.0


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


class _AttemptTransport:
    def __init__(self, *, identity_drift: bool = False) -> None:
        _, ledger = build_simulated_ledger(
            "pass", reviewer_ids=GEMINI_REVIEWER_IDS
        )
        self.ideal = {
            row["review_item_id"]: {
                key: value for key, value in row.items() if key != "reviewer_id"
            }
            for row in ledger["votes"]
            if row["reviewer_id"] == GEMINI_REVIEWER_IDS[1]
        }
        self.calls = 0
        self.identity_drift = identity_drift

    async def call(
        self,
        *,
        reviewer: dict[str, object],
        items: list[dict[str, object]],
        schema: dict[str, object],
    ) -> ProviderBatchResult:
        del schema
        self.calls += 1
        revision = reviewer.get("documented_revision")
        if (
            self.identity_drift
            and reviewer["reviewer_id"] == GEMINI_REVIEWER_IDS[1]
            and self.calls >= 3
        ):
            revision = "unexpected-revision"
        return ProviderBatchResult(
            content=json.dumps(
                {"votes": [self.ideal[str(row["review_item_id"])] for row in items]}
            ),
            provider_model=str(reviewer["provider_model"]),
            provider_revision=str(revision),
            provider_name=str(
                reviewer.get("endpoint_provider") or reviewer["provider"]
            ),
            input_tokens=500,
            output_tokens=250,
            cost_usd=0.001,
            latency_ms=1.0,
        )


class _Attempt004Transport:
    def __init__(
        self,
        *,
        failure_calls: dict[int, ProviderCallFailure] | None = None,
        quality_failure: bool = False,
    ) -> None:
        _, ledger = build_simulated_ledger("pass", reviewer_ids=TWO_REVIEWER_IDS)
        self.ideal = {
            row["review_item_id"]: {
                key: value for key, value in row.items() if key != "reviewer_id"
            }
            for row in ledger["votes"]
            if row["reviewer_id"] == TWO_REVIEWER_IDS[1]
        }
        self.failure_calls = failure_calls or {}
        self.quality_failure = quality_failure
        self.calls = 0

    async def call(
        self,
        *,
        reviewer: dict[str, object],
        items: list[dict[str, object]],
        schema: dict[str, object],
    ) -> ProviderBatchResult:
        del schema
        self.calls += 1
        if self.calls in self.failure_calls:
            raise self.failure_calls[self.calls]
        votes = [deepcopy(self.ideal[str(row["review_item_id"])]) for row in items]
        if self.quality_failure:
            for vote in votes:
                vote["case_semantically_valid"] = False
        return ProviderBatchResult(
            content=json.dumps({"votes": votes}),
            provider_model=str(reviewer["provider_model"]),
            provider_revision=str(reviewer.get("documented_revision")),
            provider_name=str(reviewer["endpoint_provider"]),
            input_tokens=500,
            output_tokens=250,
            cost_usd=0.001,
            latency_ms=1.0,
        )


def _transport_failure(category: str, *, status: int | None = None) -> ProviderCallFailure:
    details: dict[str, object] = {
        "cost_accounting_status": "unavailable-transport-failure"
    }
    if status is not None:
        details["http_status"] = status
    return ProviderCallFailure(category, details)


def _run_attempt_004(
    tmp_path: Path, transport: _Attempt004Transport
) -> dict[str, object]:
    assets = load_assets(ATTEMPT_004_PATH)
    codex = tmp_path / "codex-calibration.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=codex)
    return asyncio.run(
        execute_calibration(
            assets,
            codex_votes_path=codex,
            output_path=tmp_path / "ledger.json",
            transport=transport,
            simulation=True,
            resume=False,
        )
    )


def test_attempt_004_valid_quality_failure_is_refine_without_retry(
    tmp_path: Path,
) -> None:
    result = _run_attempt_004(
        tmp_path, _Attempt004Transport(quality_failure=True)
    )

    assert result["status"] == "completed-refine"
    assert result["provider_calls"] == 10
    assert result["transport_retry_count"] == 0
    assert result["calibration"][TWO_REVIEWER_IDS[1]]["passed"] is False


def test_attempt_004_recovers_two_distinct_transport_failures(
    tmp_path: Path,
) -> None:
    transport = _Attempt004Transport(
        failure_calls={
            1: _transport_failure("provider-timeout"),
            3: _transport_failure("provider-http-error", status=429),
        }
    )
    result = _run_attempt_004(tmp_path, transport)

    assert result["status"] == "completed-go-deeper"
    assert result["provider_calls"] == 12
    assert result["transport_retry_count"] == 2
    assert result["recovered_transport_failure_count"] == 2
    assert [
        row["retry_scheduled"] for row in result["provider_call_records"] if row["status"] == "failed"
    ] == [True, True]


def test_attempt_004_does_not_retry_a_second_failure_for_one_batch(
    tmp_path: Path,
) -> None:
    result = _run_attempt_004(
        tmp_path,
        _Attempt004Transport(
            failure_calls={
                1: _transport_failure("provider-timeout"),
                2: _transport_failure("provider-timeout"),
            }
        ),
    )

    assert result["status"] == "invalid-execution"
    assert result["provider_calls"] == 2
    assert result["transport_retry_count"] == 1
    assert result["provider_call_records"][1]["retry_eligible"] is True
    assert result["provider_call_records"][1]["retry_scheduled"] is False


def test_attempt_004_does_not_retry_malformed_or_identity_failures(
    tmp_path: Path,
) -> None:
    assets = load_assets(ATTEMPT_004_PATH)
    codex = tmp_path / "codex-calibration.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=codex)
    malformed = asyncio.run(
        execute_calibration(
            assets,
            codex_votes_path=codex,
            output_path=tmp_path / "malformed-ledger.json",
            transport=_MalformedTransport(),
            simulation=True,
            resume=False,
        )
    )
    identity = asyncio.run(
        execute_calibration(
            assets,
            codex_votes_path=codex,
            output_path=tmp_path / "identity-ledger.json",
            transport=_AttemptTransport(identity_drift=True),
            simulation=True,
            resume=False,
        )
    )

    assert malformed["provider_calls"] == 1
    assert malformed["transport_retry_count"] == 0
    assert identity["status"] == "invalid-execution"
    assert identity["transport_retry_count"] == 0


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


def test_attempt_003_first_canary_failure_suppresses_deepseek_and_bulk(
    tmp_path: Path,
) -> None:
    assets = load_assets(ATTEMPT_003_PATH)
    codex = tmp_path / "codex-calibration.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=codex)

    result = asyncio.run(
        execute_calibration(
            assets,
            codex_votes_path=codex,
            output_path=tmp_path / "ledger.json",
            transport=_ProviderErrorTransport(),
            simulation=True,
            resume=False,
        )
    )

    assert result["status"] == "invalid-execution"
    assert result["provider_calls"] == 1
    assert result["provider_call_records"][0]["reviewer_id"] == GEMINI_REVIEWER_IDS[1]
    assert not any(
        row["reviewer_id"] == GEMINI_REVIEWER_IDS[2]
        for row in result["provider_call_records"]
    )


def test_attempt_003_runtime_identity_drift_stops_after_two_canaries(
    tmp_path: Path,
) -> None:
    assets = load_assets(ATTEMPT_003_PATH)
    codex = tmp_path / "codex-calibration.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=codex)

    result = asyncio.run(
        execute_calibration(
            assets,
            codex_votes_path=codex,
            output_path=tmp_path / "ledger.json",
            transport=_AttemptTransport(identity_drift=True),
            simulation=True,
            resume=False,
        )
    )

    assert result["status"] == "invalid-execution"
    assert result["provider_calls"] == 3
    assert result["provider_failures"][0]["detail"] == (
        "provider runtime identity drifted"
    )


def test_attempt_003_pre_call_budget_stop_makes_zero_provider_calls(
    tmp_path: Path,
) -> None:
    assets = deepcopy(load_assets(ATTEMPT_003_PATH))
    assets["binding"]["cost_guard"]["emergency_hard_stop_usd"] = 0.01
    codex = tmp_path / "codex-calibration.json"
    _simulated_codex_artifact(assets, item_kind="calibration", path=codex)

    result = asyncio.run(
        execute_calibration(
            assets,
            codex_votes_path=codex,
            output_path=tmp_path / "ledger.json",
            transport=_AttemptTransport(),
            simulation=True,
            resume=False,
        )
    )

    assert result["status"] == "invalid-execution"
    assert result["provider_calls"] == 0
    assert result["provider_failures"] == [{"reason": "pre-call-budget-stop"}]
