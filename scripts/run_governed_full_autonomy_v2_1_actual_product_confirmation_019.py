#!/usr/bin/env python3
"""Run the sole canary-role correction for actual-product confirmation 019."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_019 as package,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_002 as shared,
)
from scripts.governed_full_autonomy_v2_1_actual_product_runtime import (
    selected_h_e1_engine_binding,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student import GuardedPolicyValuePlanner


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-confirmation-019"
INSTRUMENT = package.INSTRUMENT
GROUNDING_RESULT = ROOT / (
    "research/05_evaluation/records/"
    "governed-full-autonomy-v2-1-grounding-successor-011.json"
)


CONTEXT = shared.ActualProductEvaluationContext(
    builder=package,
    instrument_id=INSTRUMENT_ID,
    grounding_result_path=GROUNDING_RESULT,
    grounding_result_id="governed-full-autonomy-v2-1-grounding-successor-011",
    selected_grounding_architecture_id=(
        "pedagogy-aware-source-semantic-evidence-atoms-v3"
    ),
    grounding_result_expected_architecture_id=(
        "ambiguity-safe-source-semantic-evidence-atoms-v2"
    ),
    runtime_grounding_architecture_id=(
        "pedagogy-aware-source-semantic-evidence-atoms-v3"
    ),
    grounding_missing_blocker="grounding-successor-011-keep-missing",
    canary_case_ids=(
        "release-fresh-h-e1-trajectory-001-t1-v2-reactive-seed-1",
        "release-fresh-h-e1-long-horizon-001",
    ),
    source_resolver=package.source_fixture_for_case,
    engine_binding=selected_h_e1_engine_binding(),
    independent_scoring=True,
    hybrid_safe_generation=True,
    generator_model_override="deterministic/evidence-set-v2",
    expected_canary_models={
        "t1-v2-reactive": {"gpt-5.6-luna"},
        "t1-v2-autonomous": {"gpt-5.6-luna"},
    },
    dependency_aware_provider_failure=True,
    autonomy_architecture_id=GuardedPolicyValuePlanner.implementation_id,
    bounded_strategy_generation=True,
    require_separate_transport_canary=True,
    product_route_canary_accepts_safe_fallback=True,
)


def validate_attempt() -> dict[str, object]:
    result = shared.validate(CONTEXT)
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    execution = instrument["execution"]
    if execution.get("product_route_canary_contract") != (
        "observed-exact-identity-provider-attempt-plus-safe-product-completion-v1"
    ):
        raise ValueError("confirmation 019 canary-role contract drifted")
    if execution.get("product_route_canary_case_ids") != list(CONTEXT.canary_case_ids):
        raise ValueError("confirmation 019 product-route canary drifted")
    return {
        **result,
        "direct_transport_identity_canary_required": True,
        "product_route_canary_accepts_safe_fallback": True,
        "product_route_canary_case_ids": list(CONTEXT.canary_case_ids),
    }


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
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
        result = asyncio.run(shared.execute(resume=arguments.resume, context=CONTEXT))
    elif arguments.preflight:
        result = shared.preflight(resume=arguments.resume, context=CONTEXT)
    elif arguments.simulate:
        result = shared.simulate(CONTEXT)
    else:
        result = validate_attempt()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
