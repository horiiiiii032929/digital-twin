#!/usr/bin/env python3
"""Run the fresh source-semantic-atom grounding comparison once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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
    _selection_key,
)
from src.digital_twin.evaluation.architecture_evolution import (  # noqa: E402
    ArchitectureRoundInstrumentV1,
    ArchitectureSystemManifestV1,
    BoundArtifactV1,
)
from src.digital_twin.evaluation.factual_qa_contract import EvaluationCaseV1  # noqa: E402
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.grounding.models import DocumentChunk  # noqa: E402
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-source-semantic-atom-comparison-001"
CANDIDATE_ID = "source-semantic-evidence-atoms-v1"
BASELINE_ID = "typed-target-evidence-v1"
DEFAULT_INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_source_semantic_atom_comparison_001.json"
)


class SourceSemanticAtomComparisonInstrumentV1(BaseModel):
    schema_version: Literal[1]
    instrument_id: Literal[INSTRUMENT_ID]
    program_id: Literal["course-digital-twin-grounding-correction-002"]
    status: Literal["frozen-network-free"]
    source: BoundArtifactV1
    public_cases: BoundArtifactV1
    hidden_gold: BoundArtifactV1
    case_count: Literal[500]
    candidates: list[ArchitectureSystemManifestV1] = Field(min_length=2, max_length=2)
    hard_gates: dict[str, float] = Field(min_length=1)
    scoring_profile: Literal["source-semantic-token-v2"]
    output_directory: str = Field(min_length=1)
    network_free_execution_authorized: Literal[True]
    provider_execution_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    maximum_executions: Literal[1]
    hidden_gold_after_response_persistence: Literal[True]
    content_sha256: str

    @model_validator(mode="after")
    def finite_and_complete(self) -> "SourceSemanticAtomComparisonInstrumentV1":
        identities = {row.architecture_id for row in self.candidates}
        if identities != {BASELINE_ID, CANDIDATE_ID}:
            raise ValueError("comparison requires the frozen baseline and atom candidate")
        if sum(row.role == "baseline" for row in self.candidates) != 1:
            raise ValueError("comparison requires exactly one baseline")
        output = Path(self.output_directory)
        if output.is_absolute() or ".." in output.parts:
            raise ValueError("output directory must be repository relative")
        return self


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(artifact: BoundArtifactV1) -> Path:
    path = ROOT / artifact.path
    if not path.is_file() or _raw_sha256(path) != artifact.sha256:
        raise ArchitectureRoundExecutionError(f"artifact drifted: {artifact.path}")
    return path


def _instrument(path: Path) -> SourceSemanticAtomComparisonInstrumentV1:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise ArchitectureRoundExecutionError("comparison instrument hash drifted")
    return SourceSemanticAtomComparisonInstrumentV1.model_validate(payload)


def _inputs(
    instrument: SourceSemanticAtomComparisonInstrumentV1,
) -> tuple[list[EvaluationCaseV1], list[DocumentChunk], Path]:
    source = _load_hashed(_path(instrument.source))
    public = _load_hashed(_path(instrument.public_cases))
    cases = [EvaluationCaseV1.model_validate(row) for row in public.get("cases", [])]
    chunks = [DocumentChunk.model_validate(row) for row in source.get("chunks", [])]
    gold_path = _path(instrument.hidden_gold)
    if len(cases) != instrument.case_count or len(chunks) != 300:
        raise ArchitectureRoundExecutionError("comparison input count drifted")
    if len({row.case_id for row in cases}) != len(cases):
        raise ArchitectureRoundExecutionError("comparison case IDs are not unique")
    if source.get("final_split_opened") is not False:
        raise ArchitectureRoundExecutionError("comparison may not open final data")
    return cases, chunks, gold_path


def validate(path: Path) -> dict[str, Any]:
    instrument = _instrument(path)
    cases, chunks, _ = _inputs(instrument)
    for architecture in instrument.candidates:
        _build_retrievers(architecture, chunks)
        _router(architecture)
    return {
        "instrument_id": instrument.instrument_id,
        "status": "passed-build-only",
        "case_count": len(cases),
        "source_chunk_count": len(chunks),
        "candidate_count": 2,
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
        raise ArchitectureRoundExecutionError("comparison simulation response drifted")
    return {
        "instrument_id": instrument.instrument_id,
        "status": "passed-network-free-simulation",
        "case_count": len(selected),
        "candidate_count": len(packages),
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded": False,
    }


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


def _terminal_decision(
    *, execution_valid: bool, candidate_passed: bool, candidate_selected: bool
) -> tuple[str, str]:
    if not execution_valid:
        return "invalid-execution", "correct-harness-only"
    if candidate_passed and candidate_selected:
        return "completed-keep", "select-source-semantic-evidence-atoms-v1"
    return "completed-refine", "retain-typed-target-evidence-v1-as-rollback"


def execute(path: Path) -> dict[str, Any]:
    instrument = _instrument(path)
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
        architecture_id: _gate_results(gate_proxy, result["aggregate"])
        for architecture_id, result in scores.items()
    }
    operational_failures = {
        architecture_id: int(result["aggregate"]["operational_failure_count"])
        for architecture_id, result in scores.items()
    }
    execution_valid = not any(operational_failures.values())
    selected_id = max(scores, key=lambda row: _selection_key(scores[row]))
    candidate_passed = all(gates[CANDIDATE_ID].values())
    terminal_status, terminal_decision = _terminal_decision(
        execution_valid=execution_valid,
        candidate_passed=candidate_passed,
        candidate_selected=selected_id == CANDIDATE_ID,
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": instrument.instrument_id,
        "status": terminal_status,
        "decision": terminal_decision,
        "selected_architecture_id": selected_id,
        "baseline_architecture_id": BASELINE_ID,
        "candidate_architecture_id": CANDIDATE_ID,
        "case_count": len(cases),
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded_after_all_responses": True,
        "source_range_disjoint_from_all_prior_development": True,
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
            "Extractive generation isolates source registration, retrieval, routing, and lineage.",
            "No professor fidelity, real usability, or student learning claim is supported.",
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
    mode.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate(arguments.instrument)
    elif arguments.simulate:
        result = simulate(arguments.instrument)
    else:
        result = execute(arguments.instrument)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
