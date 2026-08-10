#!/usr/bin/env python3
"""Run frozen-schema, blinded local pedagogy judging."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANCHOR_ROOT = ROOT / "data/processed/course_tutor_v1/sealed_v1"
PRIVATE_ROOT = ROOT / "data/processed/course_tutor_v1/sealed_v2"
DEFAULT_RUN = ROOT / "experiments/runs/professor_fidelity_v1/development/result.json"
DEFAULT_OUTPUT = ROOT / "experiments/runs/professor_fidelity_v1/development/judgments-gemma3.json"
PROMPT_PATH = ROOT / "research/05_evaluation/instruments/llm_judge_v1.prompt.md"
LABELS = ("A", "B", "C", "D")
VALID = {"pass", "partial", "fail"}
CONDITIONS = ("C0", "C1", "C2", "C3")


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
    if rate == 0:
        return False
    if not 0 < rate <= 1:
        raise JudgeError("selection rate must be in [0, 1]")
    bucket = int(
        hashlib.sha256(f"{salt}:{case_id}".encode()).hexdigest()[:8], 16
    ) / 0xFFFFFFFF
    return bucket < rate


def _dataset_path(run: dict[str, Any], supplied: Path | None) -> Path:
    if supplied:
        return supplied
    if run["split"] == "anchor":
        return ANCHOR_ROOT / "anchor.json"
    return PRIVATE_ROOT / f"{run['split']}.json"


def _ollama(
    prompt: str,
    model: str,
    schema: dict[str, Any],
    *,
    seed: int,
) -> dict[str, Any]:
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "format": schema,
                "options": {
                    "temperature": 0,
                    "seed": seed,
                    "num_predict": 1200,
                },
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        envelope = json.load(response)
    try:
        return json.loads(envelope["response"])
    except (KeyError, json.JSONDecodeError) as error:
        raise JudgeError("local judge returned malformed JSON") from error


def _judgment_schema(
    *,
    task_id: str,
    mode: str,
    dimensions: list[str],
) -> dict[str, Any]:
    single_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "dimension": {"type": "string", "enum": dimensions},
            "label": {"type": "string", "enum": sorted(VALID)},
            "evidence_quote": {"type": "string", "minLength": 1},
            "reason": {"type": "string", "minLength": 1},
        },
        "required": ["dimension", "label", "evidence_quote", "reason"],
    }
    pair_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "dimension": {"type": "string", "enum": dimensions},
            "preference": {"type": "string", "enum": ["A", "B", "tie"]},
            "evidence_quote_a": {"type": "string", "minLength": 1},
            "evidence_quote_b": {"type": "string", "minLength": 1},
            "reason": {"type": "string", "minLength": 1},
        },
        "required": [
            "dimension",
            "preference",
            "evidence_quote_a",
            "evidence_quote_b",
            "reason",
        ],
    }
    single_schema: dict[str, Any]
    pair_schema: dict[str, Any]
    if mode == "single":
        single_schema = {
            "type": "array",
            "minItems": len(dimensions),
            "maxItems": len(dimensions),
            "items": single_item,
        }
        pair_schema = {"type": "null"}
    else:
        single_schema = {"type": "null"}
        pair_schema = {
            "type": "array",
            "minItems": len(dimensions),
            "maxItems": len(dimensions),
            "items": pair_item,
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0.0"]},
            "instrument_id": {"type": "string", "enum": ["llm-judge-v1"]},
            "task_id": {"type": "string", "enum": [task_id]},
            "mode": {"type": "string", "enum": [mode]},
            "single_judgments": single_schema,
            "pairwise_judgments": pair_schema,
        },
        "required": [
            "schema_version",
            "instrument_id",
            "task_id",
            "mode",
            "single_judgments",
            "pairwise_judgments",
        ],
    }


def _mapping(case_id: str, swap: bool) -> dict[str, str]:
    conditions = list(("C0", "C1", "C2", "C3"))
    shift = int(hashlib.sha256(case_id.encode()).hexdigest()[:2], 16) % 4
    conditions = conditions[shift:] + conditions[:shift]
    if swap:
        conditions.reverse()
    return dict(zip(LABELS, conditions, strict=True))


def _pair_mapping(swap: bool) -> dict[str, str]:
    return {"A": "C2", "B": "C1"} if swap else {"A": "C1", "B": "C2"}


def _assessment_context(case: dict[str, Any]) -> str:
    value = case["student_input"]["student_state"]["assessment_context"]
    return {
        "summative": "assessed_current",
        "unassessed": "unassessed",
        "practice": "practice",
    }.get(value, "unknown")


def _dimension_specs(case: dict[str, Any]) -> list[dict[str, Any]]:
    expected = case["ground_truth"]["expected_behavior"]
    required_moves = ", ".join(expected["required_tutoring_moves"]) or "none"
    forbidden = expected["forbidden_actions"] or ["miss the case-specific expectation"]
    return [
        {
            "dimension": dimension,
            "case_specific_expectation": (
                f"Expected action {expected['primary_action']}; required tutoring moves: "
                f"{required_moves}; support level: {expected['allowed_support_level']}."
            ),
            "material_failure_conditions": forbidden,
        }
        for dimension in case["rubric"]["required_pedagogy_dimensions"]
    ]


def _judge_input(
    case: dict[str, Any],
    *,
    task_id: str,
    mode: str,
    response_a: str,
    response_b: str | None,
    presentation_order: str | None,
) -> dict[str, Any]:
    state = case["student_input"]["student_state"]
    return {
        "schema_version": "1.0.0",
        "instrument_id": "llm-judge-v1",
        "task_id": task_id,
        "mode": mode,
        "case_ref": case["case_id"],
        "student_context": {
            "question": case["student_input"]["question"],
            "dialogue_history": case["student_input"]["dialogue_history"],
            "state_summary": json.dumps(state, ensure_ascii=False, sort_keys=True),
            "assessment_context": _assessment_context(case),
        },
        "policy_excerpt": (
            "Judge only the supplied pedagogical expectations. Do not evaluate "
            "factual correctness, citations, permissions, or hard gates."
        ),
        "dimensions": _dimension_specs(case),
        "response_a": response_a,
        "response_b": response_b,
        "blinding": {
            "model_names_removed": True,
            "provider_names_removed": True,
            "condition_ids_removed": True,
            "irrelevant_style_metadata_removed": True,
        },
        "hard_gate_results_visible": False,
        "gold_claims_visible": False,
        "randomization": (
            None
            if mode == "single"
            else {
                "assignment_id": f"{task_id}-assignment",
                "seed": 5002,
                "presentation_order": presentation_order,
            }
        ),
    }


def _prompt(payload: dict[str, Any]) -> str:
    return (
        PROMPT_PATH.read_text(encoding="utf-8")
        + "\nINPUT JSON:\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def _validate_judgment(
    value: dict[str, Any],
    *,
    task_id: str,
    mode: str,
    dimensions: list[str],
) -> None:
    if set(value) != {
        "schema_version",
        "instrument_id",
        "task_id",
        "mode",
        "single_judgments",
        "pairwise_judgments",
    }:
        raise JudgeError("judge output contract drifted")
    if value["schema_version"] != "1.0.0" or value["instrument_id"] != "llm-judge-v1":
        raise JudgeError("judge instrument identity drifted")
    if value["task_id"] != task_id or value["mode"] != mode:
        raise JudgeError("judge task identity drifted")
    records = (
        value["single_judgments"]
        if mode == "single"
        else value["pairwise_judgments"]
    )
    if not isinstance(records, list) or {
        item.get("dimension") for item in records
    } != set(dimensions):
        raise JudgeError("judge dimensions drifted")
    if mode == "single":
        if value["pairwise_judgments"] is not None or any(
            item.get("label") not in VALID
            or not item.get("evidence_quote")
            or not item.get("reason")
            for item in records
        ):
            raise JudgeError("single-response judgment is invalid")
    elif value["single_judgments"] is not None or any(
        item.get("preference") not in {"A", "B", "tie"}
        or not item.get("evidence_quote_a")
        or not item.get("evidence_quote_b")
        or not item.get("reason")
        for item in records
    ):
        raise JudgeError("pairwise judgment is invalid")


def _judge_case(
    case: dict[str, Any],
    rows: dict[str, dict[str, Any]],
    mapping: dict[str, str],
    model: str,
    *,
    swap: bool,
) -> dict[str, Any]:
    dimensions = case["rubric"]["required_pedagogy_dimensions"]
    responses = []
    for label, condition in mapping.items():
        task_id = f"judge-{case['case_id']}-{label.lower()}"
        payload = _judge_input(
            case,
            task_id=task_id,
            mode="single",
            response_a=rows[condition]["answer"],
            response_b=None,
            presentation_order=None,
        )
        value = _ollama(
            _prompt(payload),
            model,
            _judgment_schema(
                task_id=task_id,
                mode="single",
                dimensions=dimensions,
            ),
            seed=5002,
        )
        _validate_judgment(
            value,
            task_id=task_id,
            mode="single",
            dimensions=dimensions,
        )
        responses.append({"label": label, "dimensions": value["single_judgments"]})

    pair_mapping = _pair_mapping(swap)
    pair_task_id = f"judge-{case['case_id']}-c1-c2-{'ba' if swap else 'ab'}"
    pair_payload = _judge_input(
        case,
        task_id=pair_task_id,
        mode="pairwise",
        response_a=rows[pair_mapping["A"]]["answer"],
        response_b=rows[pair_mapping["B"]]["answer"],
        presentation_order="BA" if swap else "AB",
    )
    pair = _ollama(
        _prompt(pair_payload),
        model,
        _judgment_schema(
            task_id=pair_task_id,
            mode="pairwise",
            dimensions=dimensions,
        ),
        seed=5002,
    )
    _validate_judgment(
        pair,
        task_id=pair_task_id,
        mode="pairwise",
        dimensions=dimensions,
    )
    normalized = []
    for item in pair["pairwise_judgments"]:
        preference = item["preference"]
        normalized.append(
            {
                **item,
                "preference": (
                    pair_mapping[preference] if preference in {"A", "B"} else "tie"
                ),
            }
        )
    return {
        "responses": responses,
        "c1_c2_pairwise": normalized,
        "pair_mapping": pair_mapping,
    }


def _validate_case_result(
    value: dict[str, Any],
    case: dict[str, Any],
    mapping: dict[str, str],
) -> None:
    expected_dimensions = set(case["rubric"]["required_pedagogy_dimensions"])
    records = value.get("responses", [])
    if {record.get("label") for record in records} != set(LABELS):
        raise JudgeError("judge response labels are incomplete")
    for record in records:
        dimensions = record.get("dimensions", [])
        if {item.get("dimension") for item in dimensions} != expected_dimensions:
            raise JudgeError("judge dimensions drifted")
        if record["label"] not in mapping:
            raise JudgeError("judge response label is invalid")
    pairwise = value.get("c1_c2_pairwise", [])
    if {item.get("dimension") for item in pairwise} != expected_dimensions:
        raise JudgeError("pairwise dimensions drifted")
    if any(item.get("preference") not in {"C1", "C2", "tie"} for item in pairwise):
        raise JudgeError("pairwise preference is invalid")


def run_judging(arguments: argparse.Namespace) -> dict[str, Any]:
    run = load_json(arguments.run)
    dataset = load_json(_dataset_path(run, arguments.dataset))
    case_by_id = {case["case_id"]: case for case in dataset["cases"]}
    rows_by_case: dict[str, dict[str, dict[str, Any]]] = {}
    for row in run["results"]:
        rows_by_case.setdefault(row["case_id"], {})[row["condition"]] = row
    results = []
    selected_case_ids = [
        case_id
        for case_id in sorted(rows_by_case)
        if _selected(case_id, arguments.sample_rate, f"sample-{arguments.model}")
    ]
    for index, case_id in enumerate(selected_case_ids, start=1):
        rows = rows_by_case[case_id]
        if set(rows) != set(CONDITIONS):
            raise JudgeError(f"incomplete condition portfolio: {case_id}")
        mapping = _mapping(case_id, arguments.swap_order)
        value = _judge_case(
            case_by_id[case_id],
            rows,
            mapping,
            arguments.model,
            swap=arguments.swap_order,
        )
        _validate_case_result(value, case_by_id[case_id], mapping)
        results.append(
            {
                "case_id": case_id,
                "mapping": mapping,
                "judgment": value,
                "repeat": False,
            }
        )
        if _selected(case_id, arguments.repeat_rate, f"repeat-{arguments.model}"):
            repeated = _judge_case(
                case_by_id[case_id],
                rows,
                mapping,
                arguments.model,
                swap=arguments.swap_order,
            )
            _validate_case_result(repeated, case_by_id[case_id], mapping)
            results.append(
                {
                    "case_id": case_id,
                    "mapping": mapping,
                    "judgment": repeated,
                    "repeat": True,
                }
            )
        write_json(
            arguments.output.with_name(f"{arguments.output.stem}-checkpoint.json"),
            {
                "status": "running",
                "source_run_id": run["run_id"],
                "model": arguments.model,
                "completed_cases": index,
                "expected_cases": len(selected_case_ids),
                "case_judgments": results,
            },
        )
        print(
            f"judge={arguments.model} case={index}/{len(selected_case_ids)}",
            flush=True,
        )
    return {
        "judge_run_id": (
            f"{run['run_id']}-{arguments.model.replace(':', '-')}"
            f"{'-swapped' if arguments.swap_order else ''}-contract-v2"
        ),
        "status": "complete",
        "source_run_id": run["run_id"],
        "instrument_id": "llm-judge-v1",
        "contract_revision": "per-dimension-pairwise-v2",
        "model": arguments.model,
        "model_digest": _model_digest(arguments.model),
        "temperature": 0,
        "seed": 5002,
        "thinking": False,
        "max_output_tokens_per_call": 1200,
        "calls_per_nonrepeat_case": 5,
        "sample_rate": arguments.sample_rate,
        "repeat_rate": arguments.repeat_rate,
        "swapped_order": arguments.swap_order,
        "case_judgments": results,
    }


def _model_digest(model: str) -> str:
    completed = subprocess_run(["ollama", "list"])
    for line in completed.splitlines()[1:]:
        columns = line.split()
        if len(columns) >= 2 and columns[0] == model:
            return columns[1]
    raise JudgeError(f"Ollama model digest is unavailable: {model}")


def subprocess_run(command: list[str]) -> str:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def main() -> None:
    arguments = parse_args()
    result = run_judging(arguments)
    write_json(arguments.output, result)
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "case_judgments"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
