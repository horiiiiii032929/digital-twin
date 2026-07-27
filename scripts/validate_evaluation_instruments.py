#!/usr/bin/env python3
"""Validate frozen judge, simulator, run-record, and analysis instruments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS = ROOT / "research/05_evaluation/instruments"


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as error:
        raise ValueError(f"missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_schema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"schema validation failed at {location}: {error.message}")


def unique_by(
    records: list[dict[str, Any]], key: str, label: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        identifier = record[key]
        require(identifier not in result, f"duplicate {label}: {identifier}")
        result[identifier] = record
    return result


def validate_judge_pair(
    input_record: dict[str, Any], output_record: dict[str, Any]
) -> None:
    require(
        input_record["task_id"] == output_record["task_id"],
        "judge input/output task_id mismatch",
    )
    require(
        input_record["mode"] == output_record["mode"],
        "judge input/output mode mismatch",
    )
    input_dimensions = [item["dimension"] for item in input_record["dimensions"]]
    require(
        len(input_dimensions) == len(set(input_dimensions)),
        f"judge task {input_record['task_id']} repeats a dimension",
    )

    if input_record["mode"] == "single":
        judgments = output_record["single_judgments"]
        output_dimensions = [item["dimension"] for item in judgments]
        require(
            set(output_dimensions) == set(input_dimensions),
            "single judge output dimensions do not match the input",
        )
        require(
            len(output_dimensions) == len(set(output_dimensions)),
            "single judge output repeats a dimension",
        )
        for judgment in judgments:
            require(
                judgment["evidence_quote"] in input_record["response_a"],
                f"single judge quote is absent for {judgment['dimension']}",
            )
        return

    judgments = output_record["pairwise_judgments"]
    output_dimensions = [item["dimension"] for item in judgments]
    require(
        set(output_dimensions) == set(input_dimensions),
        "pairwise judge output dimensions do not match the input",
    )
    require(
        len(output_dimensions) == len(set(output_dimensions)),
        "pairwise judge output repeats a dimension",
    )
    for judgment in judgments:
        require(
            judgment["evidence_quote_a"] in input_record["response_a"],
            f"pairwise A quote is absent for {judgment['dimension']}",
        )
        require(
            judgment["evidence_quote_b"] in input_record["response_b"],
            f"pairwise B quote is absent for {judgment['dimension']}",
        )


def validate_state_card(state_card: dict[str, Any]) -> None:
    states = unique_by(state_card["states"], "state_id", "state ID")
    transitions = unique_by(
        state_card["transitions"], "transition_id", "transition ID"
    )
    require(
        state_card["initial_state_id"] in states,
        "simulator initial_state_id is unknown",
    )

    transition_keys: set[tuple[str, str]] = set()
    for transition in transitions.values():
        from_state = transition["from_state_id"]
        to_state = transition["to_state_id"]
        event = transition["observed_event"]
        require(from_state in states, f"transition has unknown source: {from_state}")
        require(to_state in states, f"transition has unknown destination: {to_state}")
        key = (from_state, event)
        require(
            key not in transition_keys,
            f"non-unique simulator transition for {from_state} + {event}",
        )
        transition_keys.add(key)
        require(
            transition["stop"] == states[to_state]["terminal"],
            f"transition {transition['transition_id']} stop flag does not match "
            "destination terminal state",
        )

    checkpoints = unique_by(
        state_card["checkpoints"], "after_tutor_turn", "checkpoint turn"
    )
    for turn, checkpoint in checkpoints.items():
        require(
            int(turn) <= state_card["max_tutor_turns"],
            f"checkpoint {turn} exceeds max_tutor_turns",
        )
        require(
            checkpoint["state_id"] in states,
            f"checkpoint {turn} has unknown state",
        )

    required_rules = {
        "unknown_knowledge_revealed",
        "prohibited_content_revealed",
        "undeclared_state_change",
        "unmapped_transition",
        "non_unique_transition",
        "word_limit_exceeded",
        "wrong_state_or_transition_id",
        "invalid_stop_behavior",
        "malformed_output",
    }
    require(
        set(state_card["invalidity_rules"]) == required_rules,
        "simulator invalidity_rules do not match the frozen v1 set",
    )


def validate_simulator_example(
    state_card_path: Path,
    state_card: dict[str, Any],
    input_record: dict[str, Any],
    output_record: dict[str, Any],
) -> None:
    states = {item["state_id"]: item for item in state_card["states"]}
    transitions = {
        item["transition_id"]: item for item in state_card["transitions"]
    }
    require(
        input_record["state_card_id"] == state_card["state_card_id"],
        "simulator input state_card_id mismatch",
    )
    require(
        input_record["state_card_sha256"] == sha256_file(state_card_path),
        "simulator input state-card hash mismatch",
    )
    current_state_id = input_record["current_state"]["state_id"]
    transition_id = input_record["selected_transition"]["transition_id"]
    destination_state_id = input_record["destination_state"]["state_id"]
    require(
        input_record["current_state"] == states[current_state_id],
        "simulator input current_state differs from the state card",
    )
    require(
        input_record["selected_transition"] == transitions[transition_id],
        "simulator selected_transition differs from the state card",
    )
    require(
        input_record["destination_state"] == states[destination_state_id],
        "simulator destination_state differs from the state card",
    )
    transition = transitions[transition_id]
    require(
        transition["from_state_id"] == current_state_id,
        "simulator transition source mismatch",
    )
    require(
        transition["to_state_id"] == destination_state_id,
        "simulator transition destination mismatch",
    )
    require(
        transition["observed_event"] == input_record["observed_event"],
        "simulator transition observed_event mismatch",
    )

    require(not output_record["invalid"], "valid synthetic simulator output expected")
    require(
        output_record["state_card_id"] == state_card["state_card_id"],
        "simulator output state_card_id mismatch",
    )
    require(
        output_record["turn_index"] == input_record["turn_index"],
        "simulator output turn_index mismatch",
    )
    require(
        output_record["from_state_id"] == current_state_id,
        "simulator output source state mismatch",
    )
    require(
        output_record["observed_event"] == input_record["observed_event"],
        "simulator output observed_event mismatch",
    )
    require(
        output_record["transition_id"] == transition_id,
        "simulator output transition mismatch",
    )
    require(
        output_record["next_state_id"] == destination_state_id,
        "simulator output next state mismatch",
    )
    require(
        output_record["stop"] == transition["stop"],
        "simulator output stop flag mismatch",
    )
    word_count = len(output_record["student_message"].split())
    require(
        word_count <= transition["response_constraints"]["max_words"],
        "simulator output exceeds max_words",
    )


def validate_analysis(analysis: dict[str, Any]) -> None:
    require(analysis["analysis_id"] == "analysis-v1", "unexpected analysis_id")
    require(analysis["status"] == "frozen", "analysis must be frozen")
    require(analysis["random_seed"] == 5002, "analysis seed must be 5002")
    metric_ids = {
        item["metric_id"] for item in analysis["primary_metrics"]
    }
    require(
        metric_ids
        == {
            "safe_grounded_task_success",
            "complete_evidence_success_at_3",
            "complete_evidence_success_at_5",
            "pedagogical_success",
            "safe_trajectory_completion",
            "reliable_turn_completion",
        },
        "analysis primary metric set differs from v1",
    )
    hypotheses = {
        item["hypothesis_id"] for item in analysis["confirmatory_contrasts"]
    }
    require(hypotheses == {"H1", "H2", "H3", "H4"}, "hypothesis set differs")
    stop_ids = [item["rule_id"] for item in analysis["stop_rules"]]
    require(len(stop_ids) == len(set(stop_ids)), "duplicate analysis stop rule")


def validate_run(run: dict[str, Any]) -> None:
    result_ids = [item["result_id"] for item in run["case_results"]]
    require(len(result_ids) == len(set(result_ids)), "duplicate case result ID")
    trajectory_ids = [
        item["trajectory_id"] for item in run["trajectory_results"]
    ]
    require(
        len(trajectory_ids) == len(set(trajectory_ids)),
        "duplicate trajectory result ID",
    )
    for result in run["case_results"]:
        applicable_gates = [
            gate for gate in result["hard_gates"] if gate["applicable"]
        ]
        if result["safe_grounded_task_success"]:
            require(
                result["attempt_status"] == "completed",
                "successful case must be completed",
            )
            require(
                all(gate["passed"] for gate in applicable_gates),
                "successful case has a failed hard gate",
            )
            require(
                result["expected_action_correct"] is True,
                "successful case has wrong expected action",
            )
        if result["attempt_status"] in {"missing", "malformed"}:
            require(
                result["analysis_eligibility"] == "included",
                "missing or malformed tutor output must remain included",
            )
            require(
                result["safe_grounded_task_success"] is False,
                "missing or malformed tutor output must fail safe success",
            )


def validate_freeze_manifest(manifest: dict[str, Any]) -> None:
    require(
        manifest["manifest_id"] == "instrument-freeze-v1",
        "unexpected freeze manifest ID",
    )
    require(manifest["status"] == "frozen", "freeze manifest must be frozen")
    paths = [item["path"] for item in manifest["files"]]
    require(len(paths) == len(set(paths)), "duplicate file in freeze manifest")
    for item in manifest["files"]:
        path = ROOT / item["path"]
        require(path.is_file(), f"freeze manifest file is missing: {path}")
        require(
            sha256_file(path) == item["sha256"],
            f"freeze manifest hash mismatch: {item['path']}",
        )


def validate_instruments() -> dict[str, int | str]:
    judge_input_schema = load_json(
        INSTRUMENTS / "llm_judge_input_v1.schema.json"
    )
    judge_output_schema = load_json(
        INSTRUMENTS / "llm_judge_output_v1.schema.json"
    )
    course_schema = load_json(
        INSTRUMENTS.parent / "course_tutor_v1.schema.json"
    )
    course_dimensions = set(
        course_schema["$defs"]["rubric"]["properties"][
            "required_pedagogy_dimensions"
        ]["items"]["enum"]
    )
    require(
        set(judge_input_schema["$defs"]["dimension"]["enum"])
        == course_dimensions,
        "judge input dimensions differ from course-tutor-v1",
    )
    require(
        set(judge_output_schema["$defs"]["dimension"]["enum"])
        == course_dimensions,
        "judge output dimensions differ from course-tutor-v1",
    )
    judge_pairs = [
        (
            load_json(
                INSTRUMENTS / "llm_judge_input_v1_synthetic_single.json"
            ),
            load_json(
                INSTRUMENTS / "llm_judge_output_v1_synthetic_single.json"
            ),
        ),
        (
            load_json(
                INSTRUMENTS / "llm_judge_input_v1_synthetic_pairwise.json"
            ),
            load_json(
                INSTRUMENTS / "llm_judge_output_v1_synthetic_pairwise.json"
            ),
        ),
    ]
    for input_record, output_record in judge_pairs:
        validate_schema(input_record, judge_input_schema)
        validate_schema(output_record, judge_output_schema)
        validate_judge_pair(input_record, output_record)

    state_schema = load_json(
        INSTRUMENTS / "simulated_student_state_v1.schema.json"
    )
    state_dimensions = set(
        state_schema["$defs"]["checkpoint"]["properties"][
            "required_pedagogy_dimensions"
        ]["items"]["enum"]
    )
    require(
        state_dimensions == course_dimensions,
        "simulator checkpoint dimensions differ from course-tutor-v1",
    )
    simulator_input_schema = load_json(
        INSTRUMENTS / "simulated_student_input_v1.schema.json"
    )
    simulator_output_schema = load_json(
        INSTRUMENTS / "simulated_student_turn_v1.schema.json"
    )
    state_card_path = (
        INSTRUMENTS / "simulated_student_state_v1_synthetic_example.json"
    )
    state_card = load_json(state_card_path)
    simulator_input = load_json(
        INSTRUMENTS / "simulated_student_input_v1_synthetic_example.json"
    )
    simulator_output = load_json(
        INSTRUMENTS / "simulated_student_turn_v1_synthetic_example.json"
    )
    validate_schema(state_card, state_schema)
    validate_schema(simulator_input, simulator_input_schema)
    validate_schema(simulator_output, simulator_output_schema)
    validate_state_card(state_card)
    validate_simulator_example(
        state_card_path, state_card, simulator_input, simulator_output
    )

    run_schema = load_json(INSTRUMENTS / "evaluation_run_v1.schema.json")
    run_example = load_json(
        INSTRUMENTS / "evaluation_run_v1_synthetic_example.json"
    )
    validate_schema(run_example, run_schema)
    validate_run(run_example)

    analysis_path = INSTRUMENTS / "analysis_v1.json"
    analysis = load_json(analysis_path)
    validate_analysis(analysis)
    require(
        run_example["evaluator_config"]["analysis_sha256"]
        == sha256_file(analysis_path),
        "evaluation run analysis hash mismatch",
    )

    manifest = load_json(INSTRUMENTS / "instrument_freeze_v1.json")
    validate_freeze_manifest(manifest)

    return {
        "status": "passed",
        "judge_examples": len(judge_pairs),
        "simulator_states": len(state_card["states"]),
        "simulator_transitions": len(state_card["transitions"]),
        "run_case_examples": len(run_example["case_results"]),
        "primary_metrics": len(analysis["primary_metrics"]),
        "frozen_files": len(manifest["files"]),
    }


def main() -> None:
    print(json.dumps(validate_instruments(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
