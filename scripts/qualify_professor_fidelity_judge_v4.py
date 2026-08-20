#!/usr/bin/env python3
"""Run the public empty-response probe for professor-fidelity judge v4."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.judge_professor_fidelity import (
    DEEPSEEK_EXPECTED_FINGERPRINT,
    DEEPSEEK_MODEL,
    EMPTY_RESPONSE_DISPLAY,
    JUDGE_CONTRACT_REVISION,
    JudgeError,
    JudgeTransport,
    _judge_input,
    _judge_input_sha256,
    _judgment_schema,
    _prompt,
    _validate_judgment,
    write_json_exclusive,
)
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/professor-fidelity-judge-v4-empty-response-probe-001.json"
)
PROBE_ID = "professor-fidelity-judge-v4-empty-response-probe-001"
TASK_ID = "judge-public-empty-response-single"
DIMENSION = "actionability"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-external-provider", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    if not arguments.allow_external_provider:
        parser.error("qualification requires --allow-external-provider")
    return arguments


def _public_case() -> dict[str, Any]:
    return {
        "case_id": "public-empty-response-probe",
        "student_input": {
            "question": "What should I do next?",
            "dialogue_history": [],
            "student_state": {"assessment_context": "unassessed"},
        },
        "ground_truth": {
            "expected_behavior": {
                "primary_action": "abstain",
                "required_tutoring_moves": [],
                "forbidden_actions": ["return an empty response"],
                "allowed_support_level": "bounded refusal",
            }
        },
        "rubric": {"required_pedagogy_dimensions": [DIMENSION]},
    }


def run_probe(output: Path) -> dict[str, Any]:
    case = _public_case()
    payload = _judge_input(
        case,
        task_id=TASK_ID,
        mode="single",
        response_a="",
        response_b=None,
        presentation_order=None,
    )
    if payload["response_a"] != EMPTY_RESPONSE_DISPLAY:
        raise JudgeError("empty-response display binding drifted")
    transport = JudgeTransport(
        DEEPSEEK_MODEL,
        split="anchor",
        call_limit=1,
        cost_stop_usd=0.25,
    )
    value = transport.call(
        prompt=_prompt(payload),
        schema=_judgment_schema(
            task_id=TASK_ID,
            mode="single",
            dimensions=[DIMENSION],
        ),
        seed=5002,
        task_id=TASK_ID,
        input_sha256=_judge_input_sha256(payload),
    )
    status = "passed"
    failure = None
    try:
        _validate_judgment(
            value,
            task_id=TASK_ID,
            mode="single",
            dimensions=[DIMENSION],
            response_a=payload["response_a"],
            response_b=None,
        )
        judgment = value["single_judgments"][0]
        if judgment["label"] != "fail":
            raise JudgeError("empty response was not labeled fail")
        if judgment["evidence_quote"] != EMPTY_RESPONSE_DISPLAY:
            raise JudgeError("empty-response placeholder was not quoted exactly")
    except JudgeError as error:
        status = "invalid"
        failure = str(error)

    result = {
        "probe_id": PROBE_ID,
        "status": status,
        "failure": failure,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "data_boundary": "public-synthetic-only",
        "private_text_used": False,
        "heldout_used": False,
        "contract_revision": JUDGE_CONTRACT_REVISION,
        "empty_response_display": EMPTY_RESPONSE_DISPLAY,
        "provider_model": DEEPSEEK_MODEL,
        "expected_provider_revision": DEEPSEEK_EXPECTED_FINGERPRINT,
        "transport": transport.summary(),
        "call_records": transport.call_records,
        "payload": payload,
        "judgment": value,
        "code_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        ),
    }
    write_json_exclusive(output, result)
    if status != "passed":
        raise JudgeError(f"public empty-response probe failed: {failure}")
    return result


def main() -> None:
    arguments = parse_args()
    require_pre_evaluation_operation_allowed("external_model_evaluation")
    result = run_probe(arguments.output)
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"payload", "judgment"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
