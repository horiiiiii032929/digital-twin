#!/usr/bin/env python3
"""Run the OpenAI-only wording stage of development checkpoint 003."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv

from scripts import run_academic_factual_qa_open_wording as legacy
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-checkpoint-003"
CONFIGURATION: dict[str, Any] = {
    "INSTRUMENT_ID": INSTRUMENT_ID,
    "BINDING_ID": "academic-factual-qa-open-10000-openai-binding-003",
    "INSTRUMENT_PATH": ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_development_checkpoint_003.json",
    "BINDING_PATH": ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_openai_binding_003.json",
    "LEDGER_PATH": ROOT
    / "reports/generated/academic-factual-qa-open-10000-wording-development-003.sqlite3",
    "RESULT_PATH": ROOT
    / "reports/generated/academic-factual-qa-open-10000-wording-development-003-result.json",
}


@contextmanager
def configured_runner() -> Iterator[None]:
    previous = {name: getattr(legacy, name) for name in CONFIGURATION}
    try:
        for name, value in CONFIGURATION.items():
            setattr(legacy, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(legacy, name, value)


def validate(*, require_unauthorized: bool = True) -> dict[str, Any]:
    with configured_runner():
        return legacy.validate(require_unauthorized=require_unauthorized)


def simulate() -> dict[str, Any]:
    with configured_runner():
        return legacy.simulate()


def preflight(*, resume: bool = False) -> dict[str, Any]:
    with configured_runner():
        return legacy.preflight(resume=resume)


async def execute(*, resume: bool) -> dict[str, Any]:
    with configured_runner():
        return await legacy.execute(resume=resume)


def score() -> dict[str, Any]:
    with configured_runner():
        return legacy.score()


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--validate-live", action="store_true")
    mode.add_argument("--simulate", action="store_true")
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
        result = simulate()
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
