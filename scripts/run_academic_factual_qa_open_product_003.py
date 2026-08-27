#!/usr/bin/env python3
"""Execute candidate or control T0 responses for development checkpoint 003.

This response-execution module deliberately imports no hidden-gold or scoring
module. It receives only the public runtime package and a system manifest.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv

from scripts import academic_factual_qa_open_10000_t0_adapter as adapter
from scripts import run_academic_factual_qa_open_10000 as runner
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-open-10000-development-checkpoint-003"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_development_checkpoint_003.json"
)
BINDING_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_openai_binding_003.json"
)
GENERATED = ROOT / "reports/generated"
CONFIGURATIONS: dict[str, dict[str, Path]] = {
    "candidate": {
        "cases": GENERATED / "academic-factual-qa-open-10000-v1-development-003-cases.json",
        "manifest": ROOT
        / "research/05_evaluation/instruments/academic_factual_qa_open_10000_v1_t0_openai_candidate_manifest_003.json",
        "responses": GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-candidate-responses.sqlite3",
        "provider": GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-candidate-provider.sqlite3",
        "state": GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-candidate-state.sqlite3",
    },
    "control": {
        "cases": GENERATED
        / "academic-factual-qa-open-10000-v1-development-control-003-cases.json",
        "manifest": ROOT
        / "research/05_evaluation/instruments/academic_factual_qa_open_10000_v1_t0_openai_control_manifest_003.json",
        "responses": GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-control-responses.sqlite3",
        "provider": GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-control-provider.sqlite3",
        "state": GENERATED
        / "academic-factual-qa-open-10000-v1-development-003-control-state.sqlite3",
    },
}


@contextmanager
def configured_runner() -> Iterator[None]:
    runner_previous = {
        "INSTRUMENT_ID": runner.INSTRUMENT_ID,
        "INSTRUMENT_PATH": runner.INSTRUMENT_PATH,
        "PROVIDER_BINDING_PATH": runner.PROVIDER_BINDING_PATH,
    }
    adapter_previous = adapter.OPENAI_BINDING_PATH
    try:
        runner.INSTRUMENT_ID = INSTRUMENT_ID
        runner.INSTRUMENT_PATH = INSTRUMENT_PATH
        runner.PROVIDER_BINDING_PATH = BINDING_PATH
        adapter.OPENAI_BINDING_PATH = BINDING_PATH
        yield
    finally:
        for name, value in runner_previous.items():
            setattr(runner, name, value)
        adapter.OPENAI_BINDING_PATH = adapter_previous


def validate() -> dict[str, Any]:
    with configured_runner():
        result = runner.validate_contract()
    manifests = {
        name: runner._load_manifest(paths["manifest"])  # noqa: SLF001
        for name, paths in CONFIGURATIONS.items()
    }
    if "candidate" not in manifests["candidate"].flow_id:
        raise ValueError("candidate manifest identity drifted")
    if "control" not in manifests["control"].flow_id:
        raise ValueError("control manifest identity drifted")
    return {
        **result,
        "status": "passed-build-only",
        "conditions": sorted(CONFIGURATIONS),
        "hidden_gold_module_imported": False,
    }


def preflight(*, condition: str, resume: bool = False) -> dict[str, Any]:
    paths = CONFIGURATIONS[condition]
    with configured_runner():
        return runner.preflight(
            stage="development",
            cases_path=paths["cases"],
            manifest_path=paths["manifest"],
            output=paths["responses"],
            provider_ledger=paths["provider"],
            state_path=paths["state"],
            resume=resume,
        )


async def execute(*, condition: str, resume: bool) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    readiness = preflight(condition=condition, resume=resume)
    if readiness["status"] != "ready":
        raise RuntimeError(f"{condition} product preflight blocked: {readiness['blockers']}")
    paths = CONFIGURATIONS[condition]
    with configured_runner():
        return await runner.execute(
            cases_path=paths["cases"],
            manifest_path=paths["manifest"],
            output=paths["responses"],
            adapter_factory=(
                "scripts.academic_factual_qa_open_10000_t0_adapter:build_live_t0_adapter"
            ),
            provider_ledger=paths["provider"],
            state_path=paths["state"],
            resume=resume,
        )


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--condition", choices=tuple(CONFIGURATIONS), default="candidate")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        result = asyncio.run(
            execute(condition=arguments.condition, resume=arguments.resume)
        )
    elif arguments.preflight:
        result = preflight(condition=arguments.condition, resume=arguments.resume)
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
