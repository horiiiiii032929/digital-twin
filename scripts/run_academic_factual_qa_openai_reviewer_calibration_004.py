#!/usr/bin/env python3
"""Run the non-redundant GPT-5.4 reviewer calibration successor."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

from scripts import run_academic_factual_qa_openai_reviewer_calibration as runner
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-reviewer-calibration-004"
BINDING_ID = "academic-factual-qa-open-10000-openai-binding-004"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_reviewer_calibration_004.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_004.json"
)
LEDGER_PATH = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-openai-"
    "reviewer-calibration-004.sqlite3"
)
RESULT_PATH = ROOT / (
    "reports/generated/academic-factual-qa-open-10000-openai-"
    "reviewer-calibration-004-result.json"
)


@contextmanager
def _configuration() -> Iterator[None]:
    replacements = {
        "INSTRUMENT_ID": INSTRUMENT_ID,
        "BINDING_ID": BINDING_ID,
        "INSTRUMENT_PATH": INSTRUMENT_PATH,
        "BINDING_PATH": BINDING_PATH,
        "LEDGER_PATH": LEDGER_PATH,
        "RESULT_PATH": RESULT_PATH,
    }
    previous = {name: getattr(runner, name) for name in replacements}
    for name, value in replacements.items():
        setattr(runner, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(runner, name, value)


def validate(*, require_unauthorized: bool = True) -> dict[str, object]:
    with _configuration():
        return runner.validate(require_unauthorized=require_unauthorized)


def preflight(*, resume: bool = False) -> dict[str, object]:
    with _configuration():
        return runner.preflight(resume=resume)


def simulate(*, scenario: str = "pass") -> dict[str, object]:
    with _configuration():
        return runner.simulate(scenario=scenario)


async def execute(*, resume: bool = False) -> dict[str, object]:
    with _configuration():
        return await runner.execute(resume=resume)


def score() -> dict[str, object]:
    with _configuration():
        return runner.score()


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--validate-live", action="store_true")
    mode.add_argument("--simulate", choices=("pass", "quality-failure", "malformed"))
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--score", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
    if arguments.score:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    if arguments.validate or arguments.validate_live:
        result = validate(require_unauthorized=not arguments.validate_live)
    elif arguments.simulate:
        result = simulate(scenario=arguments.simulate)
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.execute:
        result = asyncio.run(execute(resume=arguments.resume))
    else:
        result = score()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
