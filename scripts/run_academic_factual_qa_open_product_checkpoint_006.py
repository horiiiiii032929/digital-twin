#!/usr/bin/env python3
"""Run the immutable-index 500+100 T0 development checkpoint."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv

from scripts import run_academic_factual_qa_open_product_checkpoint_005 as base
from src.digital_twin.grounding import RetrievalIndexStoreV1
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-product-checkpoint-006"
BINDING_ID = "academic-factual-qa-open-10000-openai-binding-007"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_product_checkpoint_006.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_007.json"
)
CANDIDATE_MANIFEST = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_candidate_manifest_006.json"
)
CONTROL_MANIFEST = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_t0_openai_control_manifest_006.json"
)
INDEX_QUALIFICATION_RECORD = ROOT / (
    "research/05_evaluation/records/retrieval-index-lifecycle-development-001.json"
)
INDEX_ROOT = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-v1-retrieval-indexes-001"
)
GENERATED = ROOT / "reports/generated"
CANDIDATE_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-candidate-responses.sqlite3"
)
CANDIDATE_PROVIDER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-candidate-provider.sqlite3"
)
CANDIDATE_STATE = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-candidate-state.sqlite3"
)
CONTROL_RESPONSES = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-control-responses.sqlite3"
)
CONTROL_PROVIDER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-control-provider.sqlite3"
)
CONTROL_STATE = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-control-state.sqlite3"
)
CANDIDATE_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-candidate-result.json"
)
PAIRED_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-paired-result.json"
)
ADVISORY_LEDGER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-advisory-audit.sqlite3"
)
ADVISORY_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-advisory-audit-result.json"
)
CRITICAL_REVIEW_LEDGER = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-critical-review.sqlite3"
)
CRITICAL_REVIEW_RESULT = GENERATED / (
    "academic-factual-qa-open-10000-v1-development-006-critical-review-result.json"
)
CHECKPOINT_STATE = GENERATED / (
    "academic-factual-qa-open-10000-development-product-checkpoint-006-state.json"
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

ProductCheckpointError = base.ProductCheckpointError
_BASE_REPO_DIRTY = base._repo_dirty  # noqa: SLF001
_BASE_REPO_REVISION = base._repo_revision  # noqa: SLF001


def _repo_dirty() -> bool:
    return _BASE_REPO_DIRTY()


def _repo_revision() -> str:
    return _BASE_REPO_REVISION()


@contextmanager
def configured_checkpoint() -> Iterator[None]:
    """Apply successor identities without mutating checkpoint 005 on disk."""

    configuration = {
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "BINDING_ID": BINDING_ID,
        "INSTRUMENT_PATH": INSTRUMENT_PATH,
        "BINDING_PATH": BINDING_PATH,
        "CANDIDATE_MANIFEST": CANDIDATE_MANIFEST,
        "CONTROL_MANIFEST": CONTROL_MANIFEST,
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
        "_repo_dirty": _repo_dirty,
        "_repo_revision": _repo_revision,
    }
    previous = {name: getattr(base, name) for name in configuration}
    adapter_root = base.adapter.RETRIEVAL_INDEX_ROOT
    try:
        for name, value in configuration.items():
            setattr(base, name, value)
        base.adapter.RETRIEVAL_INDEX_ROOT = INDEX_ROOT
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)
        base.adapter.RETRIEVAL_INDEX_ROOT = adapter_root


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProductCheckpointError(f"JSON root is not an object: {path.name}")
    return value


def _verify_qualification_record(instrument: dict[str, Any]) -> None:
    record = _load(INDEX_QUALIFICATION_RECORD)
    lifecycle = instrument["retrieval_index_lifecycle"]
    candidate = next(
        row
        for row in record["candidates"]
        if row["role"] == "candidate"
    )
    configuration = candidate["implementation"]["configuration"]
    if (
        record["run_id"] != lifecycle["qualification_result_id"]
        or record["decision"]["outcome"] != "keep"
        or record["decision"]["selected_implementation_id"]
        != "immutable-release-bound-hybrid-index"
        or record["decision"]["generated_evidence"]["build_result_sha256"]
        != lifecycle["build_result_sha256"]
        or record["decision"]["generated_evidence"]["runtime_result_sha256"]
        != lifecycle["runtime_result_sha256"]
        or configuration["qualification_runtime_document_embedding_requests"] != 0
        or configuration["embedding_revision"] != lifecycle["embedding_revision"]
    ):
        raise ProductCheckpointError("retrieval-index qualification binding drifted")


def _verify_local_indexes(instrument: dict[str, Any]) -> dict[str, str]:
    expected = instrument["retrieval_index_lifecycle"]["artifact_ids"]
    store = RetrievalIndexStoreV1(INDEX_ROOT)
    observed: dict[str, str] = {}
    for course_id, artifact_id in sorted(expected.items()):
        manifest = store.verify(artifact_id)
        if manifest.binding.course_id != course_id:
            raise ProductCheckpointError("retrieval-index course binding drifted")
        observed[course_id] = manifest.artifact_id
    if observed != expected:
        raise ProductCheckpointError("retrieval-index artifact identities drifted")
    return observed


def validate(*, require_unauthorized: bool = True) -> dict[str, Any]:
    instrument = base._load_hashed(  # noqa: SLF001
        INSTRUMENT_PATH,
        key="instrument_id",
        identity=INSTRUMENT_ID,
    )
    _verify_qualification_record(instrument)
    with configured_checkpoint():
        result = base.validate(require_unauthorized=require_unauthorized)
    result.update(
        {
            "retrieval_index_qualification": "completed-keep",
            "runtime_document_embedding_requests": 0,
            "retrieval_index_artifact_count": 4,
        }
    )
    return result


def simulate(*, scenario: str) -> dict[str, Any]:
    with configured_checkpoint():
        result = base.simulate(scenario=scenario)
    result["retrieval_index_mode"] = "immutable-load-only"
    result["runtime_document_embedding_requests"] = 0
    return result


def preflight(*, resume: bool = False) -> dict[str, Any]:
    with configured_checkpoint():
        result = base.preflight(resume=resume)
    blockers = list(result["blockers"])
    try:
        _verify_local_indexes(_load(INSTRUMENT_PATH))
    except Exception as error:  # noqa: BLE001 - emit all no-call blockers
        blockers.append(f"retrieval-index-verification-failed:{type(error).__name__}")
    result["blockers"] = sorted(set(blockers))
    result["status"] = "ready" if not blockers else "blocked-not-authorized"
    result["retrieval_index_mode"] = "immutable-load-only"
    result["runtime_document_embedding_requests"] = 0
    return result


def _initial_state(instrument: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    with configured_checkpoint():
        state = base._initial_state(instrument, binding)  # noqa: SLF001
    state["retrieval_index_artifact_ids"] = instrument["retrieval_index_lifecycle"][
        "artifact_ids"
    ]
    return state


def _write_state(state: dict[str, Any], *, exclusive: bool = False) -> None:
    with configured_checkpoint():
        base._write_state(state, exclusive=exclusive)  # noqa: SLF001


def _resume_state(instrument: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    with configured_checkpoint():
        state = base._resume_state(instrument, binding)  # noqa: SLF001
    expected = instrument["retrieval_index_lifecycle"]["artifact_ids"]
    if state.get("retrieval_index_artifact_ids") != expected:
        raise ProductCheckpointError("checkpoint retrieval-index binding drifted")
    return state


async def execute(*, resume: bool = False) -> dict[str, Any]:
    _verify_local_indexes(_load(INSTRUMENT_PATH))
    with configured_checkpoint():
        return await base.execute(resume=resume)


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
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate()
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
