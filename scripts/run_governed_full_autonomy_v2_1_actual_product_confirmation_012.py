#!/usr/bin/env python3
"""Run the fresh release-bound hybrid autonomy confirmation 012."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_012 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_002 as shared,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

GROUNDING_RESULT = ROOT / (
    "research/05_evaluation/records/"
    "governed-full-autonomy-v2-1-grounding-successor-011.json"
)
CONTEXT = shared.ActualProductEvaluationContext(
    builder=builder,
    instrument_id=builder.INSTRUMENT_ID,
    grounding_result_path=GROUNDING_RESULT,
    grounding_result_id="governed-full-autonomy-v2-1-grounding-successor-011",
    selected_grounding_architecture_id=(
        "ambiguity-safe-source-semantic-evidence-atoms-v2"
    ),
    runtime_grounding_architecture_id=(
        "ambiguity-safe-source-semantic-evidence-atoms-v2"
    ),
    grounding_missing_blocker="grounding-successor-011-keep-missing",
    canary_case_ids=(
        "release-fresh-trajectory-001-t0-grounded-control-seed-1",
        "release-fresh-trajectory-006-t1-v2-reactive-seed-1",
    ),
    source_resolver=builder.source_fixture_for_case,
    hybrid_safe_generation=True,
    generator_model_override="deterministic/evidence-set-v2",
    expected_canary_models={
        "t0-grounded-control": set(),
        "t1-v2-reactive": {"gpt-5.6-terra"},
    },
)


def validate():
    return shared.validate(CONTEXT)


def simulate():
    return shared.simulate(CONTEXT)


def preflight(*, resume: bool = False):
    return shared.preflight(resume=resume, context=CONTEXT)


async def execute(*, resume: bool = False):
    return await shared.execute(resume=resume, context=CONTEXT)


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            builder.INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            builder.INSTRUMENT_ID, "method_evaluation_execution"
        )
        result = asyncio.run(execute(resume=arguments.resume))
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.simulate:
        result = simulate()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
