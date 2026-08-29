#!/usr/bin/env python3
"""Run the single finite extractive-boundary 500+100 successor."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv

from scripts import run_academic_factual_qa_open_product_checkpoint_005 as base
from scripts import run_academic_factual_qa_open_product_checkpoint_006 as previous
from scripts import score_academic_factual_qa_open_10000 as scorer
from src.digital_twin.evaluation.factual_qa_contract import SystemUnderTestManifestV1
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-product-checkpoint-007"
BINDING_ID = "academic-factual-qa-open-10000-openai-binding-008"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_product_checkpoint_007.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_008.json"
)
CANDIDATE_MANIFEST = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_candidate_manifest_007.json"
)
CONTROL_MANIFEST = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_control_manifest_007.json"
)
CANDIDATE_PAIRING = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_candidate_pairing_007.json"
)
CONTROL_PAIRING = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_control_pairing_007.json"
)
GENERATED = ROOT / "reports/generated"
CANDIDATE_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-candidate-responses.sqlite3"
)
CANDIDATE_PROVIDER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-candidate-provider.sqlite3"
)
CANDIDATE_STATE = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-candidate-state.sqlite3"
)
CONTROL_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-control-responses.sqlite3"
)
CONTROL_PROVIDER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-control-provider.sqlite3"
)
CONTROL_STATE = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-control-state.sqlite3"
)
CANDIDATE_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-candidate-result.json"
)
PAIRED_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-paired-result.json"
)
ADVISORY_LEDGER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-advisory-audit.sqlite3"
)
ADVISORY_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-advisory-audit-result.json"
)
CRITICAL_REVIEW_LEDGER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-critical-review.sqlite3"
)
CRITICAL_REVIEW_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-007-critical-review-result.json"
)
CHECKPOINT_STATE = GENERATED / (
    "academic-factual-qa-open-10000-development-product-checkpoint-007-state.json"
)
PRODUCT_CONFIG = {
    "candidate": (
        base.CANDIDATE_CASES,
        CANDIDATE_MANIFEST,
        CANDIDATE_RESPONSES,
        CANDIDATE_PROVIDER,
        CANDIDATE_STATE,
        500,
    ),
    "control": (
        base.CONTROL_CASES,
        CONTROL_MANIFEST,
        CONTROL_RESPONSES,
        CONTROL_PROVIDER,
        CONTROL_STATE,
        100,
    ),
}
PROVIDER_LEDGERS = (
    CANDIDATE_PROVIDER,
    CONTROL_PROVIDER,
    ADVISORY_LEDGER,
    CRITICAL_REVIEW_LEDGER,
)
ALL_OUTPUTS = (
    CHECKPOINT_STATE,
    CANDIDATE_RESPONSES,
    CANDIDATE_PROVIDER,
    CANDIDATE_STATE,
    CONTROL_RESPONSES,
    CONTROL_PROVIDER,
    CONTROL_STATE,
    CANDIDATE_RESULT,
    PAIRED_RESULT,
    ADVISORY_LEDGER,
    ADVISORY_RESULT,
    CRITICAL_REVIEW_LEDGER,
    CRITICAL_REVIEW_RESULT,
)
EXPECTED_PRODUCT_GENERATOR = "openai-gpt-5.4-mini-live-extractive-boundary"
EXPECTED_CANDIDATE_EVIDENCE_GATE = "structured-lexical-coverage-evidence-gate-v1"
EXPECTED_CONTROL_EVIDENCE_GATE = "any-hit-evidence-gate-v1"

ProductCheckpointError = previous.ProductCheckpointError


@contextmanager
def configured_successor() -> Iterator[None]:
    configuration = {
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "BINDING_ID": BINDING_ID,
        "INSTRUMENT_PATH": INSTRUMENT_PATH,
        "BINDING_PATH": BINDING_PATH,
        "CANDIDATE_MANIFEST": CANDIDATE_MANIFEST,
        "CONTROL_MANIFEST": CONTROL_MANIFEST,
        "CANDIDATE_PAIRING": CANDIDATE_PAIRING,
        "CONTROL_PAIRING": CONTROL_PAIRING,
        "CANDIDATE_RESPONSES": CANDIDATE_RESPONSES,
        "CANDIDATE_PROVIDER": CANDIDATE_PROVIDER,
        "CANDIDATE_STATE": CANDIDATE_STATE,
        "CONTROL_RESPONSES": CONTROL_RESPONSES,
        "CONTROL_PROVIDER": CONTROL_PROVIDER,
        "CONTROL_STATE": CONTROL_STATE,
        "CANDIDATE_RESULT": CANDIDATE_RESULT,
        "PAIRED_RESULT": PAIRED_RESULT,
        "ADVISORY_LEDGER": ADVISORY_LEDGER,
        "ADVISORY_RESULT": ADVISORY_RESULT,
        "CRITICAL_REVIEW_LEDGER": CRITICAL_REVIEW_LEDGER,
        "CRITICAL_REVIEW_RESULT": CRITICAL_REVIEW_RESULT,
        "CHECKPOINT_STATE": CHECKPOINT_STATE,
        "PRODUCT_CONFIG": PRODUCT_CONFIG,
        "PROVIDER_LEDGERS": PROVIDER_LEDGERS,
        "ALL_OUTPUTS": ALL_OUTPUTS,
        "EXPECTED_PRODUCT_GENERATOR": EXPECTED_PRODUCT_GENERATOR,
        "EXPECTED_CANDIDATE_EVIDENCE_GATE": EXPECTED_CANDIDATE_EVIDENCE_GATE,
        "EXPECTED_CONTROL_EVIDENCE_GATE": EXPECTED_CONTROL_EVIDENCE_GATE,
    }
    original = {name: getattr(previous, name) for name in configuration}
    original_active_generator = base.product.ACTIVE_GENERATOR
    try:
        for name, value in configuration.items():
            setattr(previous, name, value)
        base.product.ACTIVE_GENERATOR = EXPECTED_PRODUCT_GENERATOR
        yield
    finally:
        for name, value in original.items():
            setattr(previous, name, value)
        base.product.ACTIVE_GENERATOR = original_active_generator


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProductCheckpointError(f"JSON root is not an object: {path.name}")
    return payload


def _validate_pairings() -> None:
    candidate = scorer._validated_package(base.CANDIDATE_CASES, rows_key="cases")  # noqa: SLF001
    candidate_gold = scorer._validated_package(base.CANDIDATE_GOLD, rows_key="gold")  # noqa: SLF001
    control = scorer._validated_package(base.CONTROL_CASES, rows_key="cases")  # noqa: SLF001
    control_gold = scorer._validated_package(base.CONTROL_GOLD, rows_key="gold")  # noqa: SLF001
    scorer._validate_pairing_manifest(  # noqa: SLF001
        CANDIDATE_PAIRING,
        cases_package=candidate,
        gold_package=candidate_gold,
    )
    scorer._validate_pairing_manifest(  # noqa: SLF001
        CONTROL_PAIRING,
        cases_package=control,
        gold_package=control_gold,
    )


def validate(*, require_unauthorized: bool = True) -> dict[str, Any]:
    _validate_pairings()
    candidate = SystemUnderTestManifestV1.model_validate(_load(CANDIDATE_MANIFEST))
    control = SystemUnderTestManifestV1.model_validate(_load(CONTROL_MANIFEST))
    if candidate.generator != EXPECTED_PRODUCT_GENERATOR:
        raise ProductCheckpointError("candidate extractive generator drifted")
    if candidate.model_bindings.get("claim-validator") != (
        "contiguous-quote-atomic-claim-verifier-v1@1.0.0"
    ):
        raise ProductCheckpointError("candidate exact-quote validator drifted")
    if candidate.model_bindings != control.model_bindings:
        raise ProductCheckpointError("candidate/control product bindings drifted")
    with configured_successor():
        result = previous.validate(require_unauthorized=require_unauthorized)
    instrument = _load(INSTRUMENT_PATH)
    if instrument["finite_refinement"]["maximum_method_successors"] != 1:
        raise ProductCheckpointError("finite refinement boundary drifted")
    result.update(
        {
            "response_contract": "extractive-boundary-output-v1",
            "claim_validator": "contiguous-quote-atomic-claim-verifier-v1@1.0.0",
            "explicit_pairing_manifest_count": 2,
            "maximum_method_successors": 1,
        }
    )
    return result


def simulate(*, scenario: str) -> dict[str, Any]:
    with configured_successor():
        result = previous.simulate(scenario=scenario)
    result["response_contract"] = "extractive-boundary-output-v1"
    result["pairing_contract"] = "explicit-package-pairing-v1"
    return result


def preflight(*, resume: bool = False) -> dict[str, Any]:
    with configured_successor():
        result = previous.preflight(resume=resume)
    result["maximum_method_successors"] = 1
    return result


async def execute(*, resume: bool = False) -> dict[str, Any]:
    with configured_successor():
        return await previous.execute(resume=resume)


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument(
        "--simulate",
        choices=(
            "pass",
            "product-failure",
            "provider-failure",
            "advisory-malformed",
            "truth-defect",
        ),
    )
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID,
            "external_model_evaluation",
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID,
            "method_evaluation_execution",
        )
    if arguments.validate:
        result = validate(require_unauthorized=False)
    elif arguments.simulate:
        result = simulate(scenario=arguments.simulate)
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    else:
        result = asyncio.run(execute(resume=arguments.resume))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
