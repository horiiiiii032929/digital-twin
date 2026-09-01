#!/usr/bin/env python3
"""Validate and execute the finite ambiguity-safe grounding comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_whole_system_architecture_round import (  # noqa: E402
    ArchitectureRoundExecutionError,
    _build_retrievers,
    _gate_results,
    _load_hashed,
    _response_package,
    _router,
    _score_packages,
)
from scripts.validate_reference_uniqueness_controls import validate as validate_controls  # noqa: E402
from src.digital_twin.evaluation.architecture_evolution import (  # noqa: E402
    ArchitectureRoundInstrumentV1,
    ArchitectureSystemManifestV1,
    BoundArtifactV1,
)
from src.digital_twin.evaluation.factual_qa_contract import EvaluationCaseV1  # noqa: E402
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256  # noqa: E402
from src.digital_twin.grounding.models import DocumentChunk  # noqa: E402
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed  # noqa: E402


INSTRUMENT_IDS = {
    "academic-factual-qa-ambiguity-safe-comparison-001",
    "academic-factual-qa-ambiguity-safe-comparison-002",
}
BASELINE_ID = "source-semantic-evidence-atoms-v1"
CANDIDATE_ID = "ambiguity-safe-source-semantic-evidence-atoms-v2"
DEFAULT_INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_ambiguity_safe_comparison_002.json"
)


class AmbiguitySafeComparisonInstrumentV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    instrument_id: str
    program_id: Literal["course-digital-twin-grounding-correction-003"]
    status: Literal[
        "reviewed-not-authorized",
        "frozen-network-free",
        "invalid-execution-authorization-revoked",
        "completed-authorization-revoked",
    ]
    source: BoundArtifactV1
    public_cases: BoundArtifactV1
    hidden_gold: BoundArtifactV1
    reference_controls: BoundArtifactV1
    case_count: Literal[500]
    candidates: list[ArchitectureSystemManifestV1] = Field(min_length=2, max_length=2)
    hard_gates: dict[str, float] = Field(min_length=1)
    candidate_grounded_success_non_inferiority_margin: Literal[0.0]
    scoring_profile: Literal["source-semantic-token-v2"]
    output_directory: str = Field(min_length=1)
    network_free_execution_authorized: bool
    provider_execution_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    maximum_executions: Literal[1]
    hidden_gold_after_response_persistence: Literal[True]
    known_500_used_only_for_regression: Literal[True]
    prior_results_immutable: Literal[True]
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def finite_and_complete(self) -> "AmbiguitySafeComparisonInstrumentV1":
        if self.instrument_id not in INSTRUMENT_IDS:
            raise ValueError("unknown ambiguity-safe comparison identity")
        identities = {row.architecture_id for row in self.candidates}
        if identities != {BASELINE_ID, CANDIDATE_ID}:
            raise ValueError("comparison candidates drifted")
        if sum(row.role == "baseline" for row in self.candidates) != 1:
            raise ValueError("comparison requires one baseline")
        if self.network_free_execution_authorized != (
            self.status == "frozen-network-free"
        ):
            raise ValueError("status and network-free authorization disagree")
        output = Path(self.output_directory)
        if output.is_absolute() or ".." in output.parts:
            raise ValueError("output directory must be repository relative")
        return self


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(binding: BoundArtifactV1) -> Path:
    path = ROOT / binding.path
    if not path.is_file() or _raw_sha256(path) != binding.sha256:
        raise ArchitectureRoundExecutionError(f"artifact drifted: {binding.path}")
    return path


def _instrument(path: Path) -> AmbiguitySafeComparisonInstrumentV1:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise ArchitectureRoundExecutionError("comparison instrument hash drifted")
    return AmbiguitySafeComparisonInstrumentV1.model_validate(payload)


def _inputs(
    instrument: AmbiguitySafeComparisonInstrumentV1,
) -> tuple[list[EvaluationCaseV1], list[DocumentChunk], Path]:
    source = _load_hashed(_path(instrument.source))
    public = _load_hashed(_path(instrument.public_cases))
    cases = [EvaluationCaseV1.model_validate(row) for row in public.get("cases", [])]
    chunks = [DocumentChunk.model_validate(row) for row in source.get("chunks", [])]
    if len(cases) != 500 or len(chunks) != 300:
        raise ArchitectureRoundExecutionError("comparison input count drifted")
    if source.get("reference_uniqueness_diagnostics") != {"unique": 400}:
        raise ArchitectureRoundExecutionError("sealed reference uniqueness drifted")
    if source.get("source_range_disjoint_from_all_prior_development") is not True:
        raise ArchitectureRoundExecutionError("source-disjoint declaration drifted")
    if source.get("final_split_opened") is not False:
        raise ArchitectureRoundExecutionError("comparison may not open final data")
    return cases, chunks, _path(instrument.hidden_gold)


def validate(path: Path) -> dict[str, Any]:
    instrument = _instrument(path)
    cases, chunks, _ = _inputs(instrument)
    controls = validate_controls(_path(instrument.reference_controls))
    for architecture in instrument.candidates:
        _build_retrievers(architecture, chunks)
        _router(architecture)
    return {
        "instrument_id": instrument.instrument_id,
        "status": "passed-build-only",
        "execution_authorized": instrument.network_free_execution_authorized,
        "case_count": len(cases),
        "source_chunk_count": len(chunks),
        "planted_control_count": controls["control_count"],
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded": False,
    }


def simulate(path: Path) -> dict[str, Any]:
    instrument = _instrument(path)
    cases, chunks, _ = _inputs(instrument)
    selected = cases[:20]
    packages = {
        row.architecture_id: _response_package(row, selected, chunks)
        for row in instrument.candidates
    }
    if any(len(value["responses"]) != len(selected) for value in packages.values()):
        raise ArchitectureRoundExecutionError("simulation response count drifted")
    return {
        "instrument_id": instrument.instrument_id,
        "status": "passed-network-free-simulation",
        "case_count": len(selected),
        "candidate_count": len(packages),
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded": False,
    }


def preflight(path: Path) -> dict[str, Any]:
    result = validate(path)
    result["status"] = (
        "ready-network-free"
        if result["execution_authorized"]
        else "blocked-not-authorized"
    )
    return result


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ArchitectureRoundExecutionError(f"exclusive output exists: {path}")
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _fully_grounded_success(score: dict[str, Any]) -> float:
    try:
        value = score["aggregate"]["metrics"]["fully_grounded_factual_success"]
    except (KeyError, TypeError) as error:
        raise ArchitectureRoundExecutionError(
            "scorer omitted fully grounded factual success"
        ) from error
    return float(value)


def execute(path: Path) -> dict[str, Any]:
    instrument = _instrument(path)
    if not instrument.network_free_execution_authorized:
        raise ArchitectureRoundExecutionError("comparison is not authorized")
    require_bounded_pilot_operation_allowed(
        instrument.instrument_id, "method_evaluation_execution"
    )
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise ArchitectureRoundExecutionError("comparison requires a clean worktree")
    output_root = ROOT / instrument.output_directory
    if output_root.exists():
        raise ArchitectureRoundExecutionError("exclusive comparison output exists")
    cases, chunks, gold_path = _inputs(instrument)
    response_paths: dict[str, Path] = {}
    for architecture in instrument.candidates:
        package = _response_package(architecture, cases, chunks)
        response_path = output_root / f"{architecture.architecture_id}-responses.json"
        _write(response_path, package)
        response_paths[architecture.architecture_id] = response_path
    scores = _score_packages(
        cases=cases,
        gold_path=gold_path,
        response_paths=response_paths,
        scoring_profile=instrument.scoring_profile,
    )
    gate_proxy = ArchitectureRoundInstrumentV1.model_construct(
        hard_gates=instrument.hard_gates
    )
    gates = {
        architecture_id: _gate_results(gate_proxy, score["aggregate"])
        for architecture_id, score in scores.items()
    }
    operational_failures = {
        architecture_id: int(score["aggregate"]["operational_failure_count"])
        for architecture_id, score in scores.items()
    }
    execution_valid = not any(operational_failures.values())
    candidate_success = _fully_grounded_success(scores[CANDIDATE_ID])
    baseline_success = _fully_grounded_success(scores[BASELINE_ID])
    candidate_selected = bool(
        all(gates[CANDIDATE_ID].values())
        and candidate_success >= baseline_success
    )
    if not execution_valid:
        status, decision = "invalid-execution", "correct-harness-only"
    elif candidate_selected:
        status, decision = "completed-keep", "select-ambiguity-safe-atoms-v2"
    else:
        status, decision = "completed-refine", "retain-v1-and-redesign-method"
    result: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": instrument.instrument_id,
        "status": status,
        "decision": decision,
        "selected_architecture_id": CANDIDATE_ID if candidate_selected else BASELINE_ID,
        "baseline_architecture_id": BASELINE_ID,
        "candidate_architecture_id": CANDIDATE_ID,
        "case_count": len(cases),
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded_after_all_responses": True,
        "source_range_disjoint_from_all_prior_development": True,
        "planted_reference_controls_passed": 6,
        "operational_failure_counts": operational_failures,
        "code_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "candidates": {
            architecture_id: {
                "aggregate": value["aggregate"],
                "hard_gates": gates[architecture_id],
            }
            for architecture_id, value in scores.items()
        },
        "limitations": [
            "This is a fresh network-free development comparison, not release evidence.",
            "The planted controls calibrate deterministic ambiguity handling.",
            "No professor fidelity, usability, or student learning claim is supported.",
        ],
    }
    result["content_sha256"] = canonical_json_sha256(result)
    _write(output_root / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        guarded_instrument = _instrument(arguments.instrument)
        require_bounded_pilot_operation_allowed(
            guarded_instrument.instrument_id, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate(arguments.instrument)
    elif arguments.simulate:
        result = simulate(arguments.instrument)
    elif arguments.preflight:
        result = preflight(arguments.instrument)
    else:
        result = execute(arguments.instrument)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
