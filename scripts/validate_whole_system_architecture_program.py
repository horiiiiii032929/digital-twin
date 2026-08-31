#!/usr/bin/env python3
"""Validate the finite whole-system architecture-evolution program."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from src.digital_twin.evaluation.architecture_evolution import (
    ArchitectureEvolutionProgramV1,
    TrancheStatus,
    load_architecture_evolution_program,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_whole_system_architecture_evolution_001.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repository_file(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("program paths must remain repository relative")
    resolved = ROOT / path
    if not resolved.is_file():
        raise ValueError(f"program artifact does not exist: {relative_path}")
    return resolved


def validate_program(
    instrument_path: Path = DEFAULT_INSTRUMENT,
) -> tuple[ArchitectureEvolutionProgramV1, dict[str, object]]:
    program = load_architecture_evolution_program(instrument_path)
    registry_path = _repository_file(program.recording_policy.registry_path)
    records_directory = ROOT / program.recording_policy.records_directory
    if not records_directory.is_dir():
        raise ValueError("evaluation records directory does not exist")

    registry = registry_path.read_text(encoding="utf-8")
    registered_ids = set(
        re.findall(r"^\| `([^`]+)` \|", registry, flags=re.MULTILINE)
    )
    missing_baselines = set(program.historical_baseline_run_ids) - registered_ids
    if missing_baselines:
        raise ValueError(
            "program baseline run IDs are absent from the registry: "
            + ", ".join(sorted(missing_baselines))
        )

    for artifact in program.baseline_artifacts:
        path = _repository_file(artifact.path)
        if _sha256(path) != artifact.sha256:
            raise ValueError(f"baseline artifact hash drift: {artifact.path}")

    frozen_count = 0
    for tranche in program.tranches:
        if tranche.status == TrancheStatus.PLANNED:
            continue
        frozen_count += 1
        if tranche.public_path is None or tranche.public_sha256 is None:
            raise ValueError("validated frozen tranche lacks public binding")
        public_path = _repository_file(tranche.public_path)
        if _sha256(public_path) != tranche.public_sha256:
            raise ValueError(f"public tranche hash drift: {tranche.tranche_id}")
        if tranche.gold_path is not None and tranche.gold_sha256 is not None:
            gold_path = _repository_file(tranche.gold_path)
            if _sha256(gold_path) != tranche.gold_sha256:
                raise ValueError(f"gold tranche hash drift: {tranche.tranche_id}")

    summary: dict[str, object] = {
        "program_id": program.program_id,
        "status": "passed",
        "architecture_planes": len(program.architecture_planes),
        "architecture_rounds": len(program.rounds),
        "dataset_tranches": len(program.tranches),
        "frozen_or_historical_tranches": frozen_count,
        "final_stages": len(program.final_stages),
        "historical_baseline_runs": len(program.historical_baseline_run_ids),
        "human_participants_required": program.human_participants_required,
        "provider_execution_authorized": program.provider_execution_authorized,
        "paid_execution_authorized": program.paid_execution_authorized,
        "instrument_sha256": _sha256(instrument_path),
    }
    return program, summary


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    _, summary = validate_program(arguments.instrument)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
