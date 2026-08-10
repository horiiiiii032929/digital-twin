#!/usr/bin/env python3
"""Run blinded local pedagogical judging for professor-fidelity outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT / "data/processed/course_tutor_v1/sealed_v1"
DEFAULT_RUN = ROOT / "experiments/runs/professor_fidelity_v1/development/result.json"
DEFAULT_OUTPUT = ROOT / "experiments/runs/professor_fidelity_v1/development/judgments-gemma3.json"
PROMPT_PATH = ROOT / "research/05_evaluation/instruments/llm_judge_v1.prompt.md"
LABELS = ("A", "B", "C", "D")
VALID = {"pass", "partial", "fail"}


class JudgeError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--model", choices=("gemma3:4b", "qwen3:4b"), default="gemma3:4b")
    parser.add_argument("--sample-rate", type=float, default=1.0)
    parser.add_argument("--swap-order", action="store_true")
    parser.add_argument("--repeat-rate", type=float, default=0.2)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")


def _selected(case_id: str, rate: float, salt: str) -> bool:
    if not 0 < rate <= 1:
        raise JudgeError("sample rate must be in (0, 1]")
    bucket = int(hashlib.sha256(f"{salt}:{case_id}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return bucket < rate


def _dataset_path(run: dict[str, Any], supplied: Path | None) -> Path:
    if supplied:
        return supplied
    split = run["split"]
    if split == "anchor":
        return ROOT / "data/processed/course_tutor_v1/anchor/course_tutor_v1_anchor_draft.json"
    return PRIVATE_ROOT / f"{split}.json"


def _ollama(prompt: str, model: str, *, seed: int) -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "responses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "enum": list(LABELS)},
                        "dimensions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "dimension": {"type": "string"},
                                    "label": {"type": "string", "enum": sorted(VALID)},
                                    "quote": {"type": "string"},
                                    "reason": {"type": "string"},
                                },
                                "required": ["dimension", "label", "quote", "reason"],
                            },
                        },
                    },
                    "required": ["label", "dimensions"],
                },
            },
            "c1_c2_preference": {"type": "string", "enum": ["C1", "C2", "tie"]},
        },
        "required": ["responses", "c1_c2_preference"],
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps({"model": model, "prompt": prompt, "stream": False, "format": schema, "options": {"temperature": 0, "seed": seed, "num_predict": 1600}}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        envelope = json.load(response)
    try:
        return json.loads(envelope["response"])
    except (KeyError, json.JSONDecodeError) as error:
        raise JudgeError("local judge returned malformed JSON") from error


def _mapping(case_id: str, swap: bool) -> dict[str, str]:
    conditions = list(("C0", "C1", "C2", "C3"))
    shift = int(hashlib.sha256(case_id.encode()).hexdigest()[:2], 16) % 4
    conditions = conditions[shift:] + conditions[:shift]
    if swap:
        conditions.reverse()
    return dict(zip(LABELS, conditions, strict=True))


def _prompt(case: dict[str, Any], rows: dict[str, dict[str, Any]], mapping: dict[str, str]) -> str:
    dimensions = case["rubric"]["required_pedagogy_dimensions"]
    blinded = {label: rows[condition]["answer"] for label, condition in mapping.items()}
    c1_label = next(label for label, condition in mapping.items() if condition == "C1")
    c2_label = next(label for label, condition in mapping.items() if condition == "C2")
    return (
        PROMPT_PATH.read_text(encoding="utf-8")
        + "\nEvaluate all four blinded responses independently. Judge only these dimensions: "
        + json.dumps(dimensions)
        + ". For c1_c2_preference, compare " + c1_label + " (C1) with " + c2_label
        + " (C2), but return only C1, C2, or tie.\nINPUT JSON:\n"
        + json.dumps({"question": case["student_input"]["question"], "student_state": case["student_input"]["student_state"], "dimension_expectations": case["ground_truth"]["expected_behavior"], "responses": blinded}, ensure_ascii=False, sort_keys=True)
    )


def _validate(value: dict[str, Any], case: dict[str, Any], mapping: dict[str, str]) -> None:
    expected_dimensions = set(case["rubric"]["required_pedagogy_dimensions"])
    records = value.get("responses", [])
    if {record.get("label") for record in records} != set(LABELS):
        raise JudgeError("judge response labels are incomplete")
    for record in records:
        dimensions = record.get("dimensions", [])
        if {item.get("dimension") for item in dimensions} != expected_dimensions:
            raise JudgeError("judge dimensions drifted")
        response_text = mapping[record["label"]]
        if any(item.get("label") not in VALID or not item.get("reason") for item in dimensions):
            raise JudgeError(f"invalid judgment for {response_text}")
    if value.get("c1_c2_preference") not in {"C1", "C2", "tie"}:
        raise JudgeError("pairwise preference is invalid")


def run_judging(arguments: argparse.Namespace) -> dict[str, Any]:
    run = load_json(arguments.run)
    dataset = load_json(_dataset_path(run, arguments.dataset))
    case_by_id = {case["case_id"]: case for case in dataset["cases"]}
    rows_by_case: dict[str, dict[str, dict[str, Any]]] = {}
    for row in run["results"]:
        rows_by_case.setdefault(row["case_id"], {})[row["condition"]] = row
    results = []
    for index, case_id in enumerate(sorted(rows_by_case), start=1):
        if not _selected(case_id, arguments.sample_rate, f"sample-{arguments.model}"):
            continue
        rows = rows_by_case[case_id]
        if set(rows) != {"C0", "C1", "C2", "C3"}:
            raise JudgeError(f"incomplete condition portfolio: {case_id}")
        mapping = _mapping(case_id, arguments.swap_order)
        value = _ollama(_prompt(case_by_id[case_id], rows, mapping), arguments.model, seed=5002)
        _validate(value, case_by_id[case_id], mapping)
        results.append({"case_id": case_id, "mapping": mapping, "judgment": value, "repeat": False})
        if _selected(case_id, arguments.repeat_rate, f"repeat-{arguments.model}"):
            repeated = _ollama(_prompt(case_by_id[case_id], rows, mapping), arguments.model, seed=5002)
            _validate(repeated, case_by_id[case_id], mapping)
            results.append({"case_id": case_id, "mapping": mapping, "judgment": repeated, "repeat": True})
        print(f"judge={arguments.model} case={index}/{len(rows_by_case)}", flush=True)
    return {
        "judge_run_id": f"{run['run_id']}-{arguments.model.replace(':', '-')}{'-swapped' if arguments.swap_order else ''}",
        "status": "complete", "source_run_id": run["run_id"], "model": arguments.model,
        "model_digest": _model_digest(arguments.model), "temperature": 0, "seed": 5002,
        "sample_rate": arguments.sample_rate, "repeat_rate": arguments.repeat_rate,
        "swapped_order": arguments.swap_order, "case_judgments": results,
    }


def _model_digest(model: str) -> str:
    completed = subprocess_run(["ollama", "list"])
    for line in completed.splitlines()[1:]:
        columns = line.split()
        if len(columns) >= 2 and columns[0] == model:
            return columns[1]
    raise JudgeError(f"Ollama model digest is unavailable: {model}")


def subprocess_run(command: list[str]) -> str:
    import subprocess
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def main() -> None:
    arguments = parse_args()
    result = run_judging(arguments)
    write_json(arguments.output, result)
    print(json.dumps({key: value for key, value in result.items() if key != "case_judgments"}, indent=2))


if __name__ == "__main__":
    main()
