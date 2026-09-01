#!/usr/bin/env python3
"""Run one fresh, finite, network-free semantic-target architecture comparison."""

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
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationCaseV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.grounding.models import DocumentChunk  # noqa: E402
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


DEFAULT_INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_semantic_target_comparison_001.json"
)
CANDIDATE_ID = "semantic-target-resolution-v3"


class SemanticTargetComparisonInstrumentV1(BaseModel):
    """Frozen public/gold bindings for one successor comparison."""

    schema_version: Literal[1]
    instrument_id: str = Field(min_length=1)
    program_id: str = Field(min_length=1)
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
    def finite_and_complete(self) -> "SemanticTargetComparisonInstrumentV1":
        if len({row.architecture_id for row in self.candidates}) != 2:
            raise ValueError("comparison requires two distinct architectures")
        if sum(row.role == "baseline" for row in self.candidates) != 1:
            raise ValueError("comparison requires exactly one baseline")
        if CANDIDATE_ID not in {row.architecture_id for row in self.candidates}:
            raise ValueError("semantic-target candidate is missing")
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


def _instrument(path: Path) -> SemanticTargetComparisonInstrumentV1:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise ArchitectureRoundExecutionError("comparison instrument hash drifted")
    return SemanticTargetComparisonInstrumentV1.model_validate(payload)


def _inputs(
    instrument: SemanticTargetComparisonInstrumentV1,
) -> tuple[list[EvaluationCaseV1], list[DocumentChunk], Path]:
    source = _load_hashed(_path(instrument.source))
    public = _load_hashed(_path(instrument.public_cases))
    cases = [EvaluationCaseV1.model_validate(row) for row in public.get("cases", [])]
    chunks = [DocumentChunk.model_validate(row) for row in source.get("chunks", [])]
    gold_path = _path(instrument.hidden_gold)
    if len(cases) != instrument.case_count or not chunks:
        raise ArchitectureRoundExecutionError("comparison input count drifted")
    if len({row.case_id for row in cases}) != len(cases):
        raise ArchitectureRoundExecutionError("comparison case IDs are not unique")
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
    selected_id = max(scores, key=lambda row: _selection_key(scores[row]))
    candidate_passed = all(gates[CANDIDATE_ID].values())
    candidate_selected = selected_id == CANDIDATE_ID
    baseline_id = next(
        row.architecture_id for row in instrument.candidates if row.role == "baseline"
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": instrument.instrument_id,
        "status": (
            "completed-keep"
            if candidate_passed and candidate_selected
            else "completed-refine"
        ),
        "decision": (
            "select-semantic-target-resolution-v3"
            if candidate_passed and candidate_selected
            else "retain-typed-target-evidence-v1"
        ),
        "selected_architecture_id": selected_id,
        "baseline_architecture_id": baseline_id,
        "candidate_architecture_id": CANDIDATE_ID,
        "case_count": len(cases),
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded_after_all_responses": True,
        "source_range_disjoint_from_prior_development": True,
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
            "Extractive generation isolates retrieval, routing, and source-range selection.",
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
        instrument = _instrument(arguments.instrument)
        require_bounded_pilot_operation_allowed(
            instrument.instrument_id,
            "method_evaluation_execution",
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
