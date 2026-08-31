#!/usr/bin/env python3
"""Validate the finite successor that closes issue 153 once."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scripts.academic_factual_qa_atomic_m2_t0_adapter import (
    ACTION_ROUTER_ADAPTER_VERSION,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-grounding-selection-002"
PROGRAM_ID = INSTRUMENT_ID
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
INSTRUMENT_ROOT = ROOT / "research/05_evaluation/instruments"
CASES = (
    DATASET_ROOT
    / "academic-factual-qa-action-router-product-development-001-cases.json"
)
GOLD = (
    DATASET_ROOT / "academic-factual-qa-action-router-product-development-001-gold.json"
)
CONTROL_CASES = (
    DATASET_ROOT
    / "academic-factual-qa-action-router-product-development-001-control-cases.json"
)
CONTROL_GOLD = (
    DATASET_ROOT
    / "academic-factual-qa-action-router-product-development-001-control-gold.json"
)
INSTRUMENT = INSTRUMENT_ROOT / "academic_factual_qa_grounding_selection_002.json"
BINDING = (
    INSTRUMENT_ROOT / "academic_factual_qa_grounding_selection_openai_binding_002.json"
)
CANDIDATE_MANIFEST = (
    INSTRUMENT_ROOT
    / "academic_factual_qa_grounding_selection_candidate_manifest_002.json"
)
CONTROL_MANIFEST = (
    INSTRUMENT_ROOT
    / "academic_factual_qa_grounding_selection_control_manifest_002.json"
)
RETRIEVAL_RUNTIME = (
    ROOT
    / "reports/generated/academic-factual-qa-action-router-product-checkpoint-001/retrieval-runtime.json"
)
PROFILE = (
    ROOT / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)


class GroundingSelectionBuildError(RuntimeError):
    pass


class _AuthorizationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_execution_authorized: bool = False
    paid_execution_authorized: bool = False
    final_execution_authorized: bool = False


class _OpenAiGeneratorBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: str = Field(min_length=1)
    provider: Literal["openai"]
    first_party_endpoint: Literal[True]
    api_url: Literal["https://api.openai.com/v1/responses"]
    credential_environment_variable: Literal["OPENAI_API_KEY"]
    provider_model: Literal["gpt-5.4-mini-2026-03-17"]
    documented_revision: Literal["gpt-5.4-mini-2026-03-17"]
    reasoning_effort: Literal["low"]
    max_output_tokens: Literal[600]
    timeout_seconds: int = Field(ge=1, le=120)
    maximum_transport_retries: Literal[0]
    pricing_usd_per_million_input_tokens: float = Field(ge=0)
    pricing_usd_per_million_output_tokens: float = Field(ge=0)
    request_store: Literal[False]


class _ProviderSetV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    high_volume_generator: _OpenAiGeneratorBindingV1 = Field(
        alias="high-volume-generator"
    )


class GroundingSelectionBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    binding_id: str = Field(min_length=1)
    instrument_id: Literal[INSTRUMENT_ID]
    metadata_status: Literal["refresh-required", "fresh"]
    verified_at: str | None
    freshness_hours: Literal[24]
    official_sources: list[str] = Field(min_length=2)
    providers: _ProviderSetV1
    authorization: _AuthorizationV1
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def freshness_fields_must_match(self) -> "GroundingSelectionBindingV1":
        if (self.metadata_status == "fresh") != (self.verified_at is not None):
            raise ValueError("provider freshness status and timestamp disagree")
        return self


class GroundingSelectionInstrumentV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: Literal[1]
    instrument_id: Literal[INSTRUMENT_ID]
    status: Literal["reviewed-build-only", "frozen-pending-execution"]
    binding_id: str = Field(min_length=1)
    owner_issue: Literal[153]
    execution: dict[str, object]
    hard_gates: dict[str, object]
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _load_hashed(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise GroundingSelectionBuildError(f"content hash drifted: {path.name}")
    return payload


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict[str, object]:
    instrument_payload = _load_hashed(INSTRUMENT)
    binding_payload = _load_hashed(BINDING)
    instrument = GroundingSelectionInstrumentV1.model_validate(instrument_payload)
    binding = GroundingSelectionBindingV1.model_validate(binding_payload)
    candidate = SystemUnderTestManifestV1.model_validate_json(
        CANDIDATE_MANIFEST.read_text(encoding="utf-8")
    )
    control = SystemUnderTestManifestV1.model_validate_json(
        CONTROL_MANIFEST.read_text(encoding="utf-8")
    )
    if instrument.binding_id != binding.binding_id:
        raise GroundingSelectionBuildError(
            "instrument/provider binding identity drifted"
        )
    authorization_values = (
        binding.authorization.provider_execution_authorized,
        binding.authorization.paid_execution_authorized,
        binding.authorization.final_execution_authorized,
    )
    if instrument.status == "reviewed-build-only" and any(authorization_values):
        raise GroundingSelectionBuildError(
            "build-only checkpoint gained execution authority"
        )
    if instrument.status == "frozen-pending-execution" and authorization_values != (
        True,
        True,
        False,
    ):
        raise GroundingSelectionBuildError(
            "frozen checkpoint requires exact bounded development authority"
        )
    execution = instrument.execution
    if (
        execution.get("maximum_product_calls") != 600
        or execution.get("maximum_canary_calls") != 2
        or execution.get("maximum_total_calls") != 602
        or execution.get("maximum_transport_retries") != 0
        or execution.get("absolute_emergency_cost_usd") != 50.0
        or execution.get("hidden_gold_after_both_response_ledgers") is not True
        or execution.get("maximum_harness_corrections") != 1
    ):
        raise GroundingSelectionBuildError("finite execution boundary drifted")
    if (
        candidate.retriever != control.retriever
        or candidate.model_bindings.get("generator")
        != control.model_bindings.get("generator")
        or candidate.evidence_gate != "question-targeted-atomic-evidence-gate-v1"
        or candidate.model_bindings.get("action-router")
        != "deterministic-tutor-action-router-v1"
        or control.evidence_gate != "atomic-structured-coverage-control-v1"
        or control.model_bindings.get("action-router") != "none-historical-control"
    ):
        raise GroundingSelectionBuildError("candidate/control comparison drifted")
    if (
        candidate.adapter_version != ACTION_ROUTER_ADAPTER_VERSION
        or control.adapter_version != ACTION_ROUTER_ADAPTER_VERSION
    ):
        raise GroundingSelectionBuildError(
            "system manifest does not match the action-router adapter contract"
        )
    public = _load_hashed(CASES)
    hidden = _load_hashed(GOLD)
    control_public = _load_hashed(CONTROL_CASES)
    control_hidden = _load_hashed(CONTROL_GOLD)
    cases = [EvaluationCaseV1.model_validate(row) for row in public["cases"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in hidden["gold"]]
    controls = [EvaluationCaseV1.model_validate(row) for row in control_public["cases"]]
    control_gold = [
        EvaluationGoldV1.model_validate(row) for row in control_hidden["gold"]
    ]
    if (
        len(cases) != 500
        or len(gold) != 500
        or len(controls) != 100
        or len(control_gold) != 100
        or {row.case_id for row in cases} != {row.case_id for row in gold}
        or {row.case_id for row in controls} != {row.case_id for row in control_gold}
    ):
        raise GroundingSelectionBuildError("500+100 package drifted")
    if any(
        {"expected_action", "canonical_answer", "claims", "boundary_reason"} & set(row)
        for row in public["cases"]
    ):
        raise GroundingSelectionBuildError("public questions expose hidden gold")
    runtime_binding = instrument_payload.get("retrieval_runtime", {})
    if RETRIEVAL_RUNTIME.is_file() and _file_sha256(RETRIEVAL_RUNTIME) != (
        runtime_binding.get("file_sha256")
    ):
        raise GroundingSelectionBuildError("historical retrieval runtime drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "passed-frozen-pending-execution"
            if instrument.status == "frozen-pending-execution"
            else "passed-build-only"
        ),
        "candidate_case_count": 500,
        "control_case_count": 100,
        "binding_id": binding.binding_id,
        "adapter_version": ACTION_ROUTER_ADAPTER_VERSION,
        "metadata_status": binding.metadata_status,
        "provider_execution_authorized": (
            binding.authorization.provider_execution_authorized
        ),
        "paid_execution_authorized": binding.authorization.paid_execution_authorized,
        "historical_retrieval_runtime_available": RETRIEVAL_RUNTIME.is_file(),
        "historical_retrieval_runtime_sha256": (
            _file_sha256(RETRIEVAL_RUNTIME) if RETRIEVAL_RUNTIME.is_file() else None
        ),
        "final_10000_opened": False,
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(validate(), indent=2, sort_keys=True))


# Keep the entrypoint naming consistent with the older product-checkpoint
# builders without mutating any historical builder.
check = validate


if __name__ == "__main__":
    main()
