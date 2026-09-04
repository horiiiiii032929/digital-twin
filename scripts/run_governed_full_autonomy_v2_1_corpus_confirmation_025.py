#!/usr/bin/env python3
"""Run the multi-source-corpus successor to persona confirmation 024.

Everything the persona confirmations already exercise -- personas, turn kinds,
events, the virtual clock, consent, quiet hours, frequency, restart, goal
termination, proactive lineage -- is reused unchanged. Two things differ:

* every release publishes a whole approved corpus rather than one paragraph;
* grounding uses the dominance-scoped v4 successor rather than v3.

The sealed 10,000-case regression is the recorded before-measurement. It is
never rerun and never rescored.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from scripts import build_governed_full_autonomy_v2_1_corpus_confirmation_025 as package
from scripts import run_governed_full_autonomy_v2_1_actual_product_evaluation_002 as shared
from scripts.governed_full_autonomy_v2_1_actual_product_runtime import (
    selected_h_e1_engine_binding,
)
from src.digital_twin.action_router import DeterministicActionRouterV3
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student import GuardedPolicyValuePlanner


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = package.INSTRUMENT_ID
INSTRUMENT = package.INSTRUMENT
GROUNDING_RESULT = ROOT / (
    "research/05_evaluation/records/"
    "governed-full-autonomy-v2-1-grounding-successor-011.json"
)
SUCCESSOR_ARCHITECTURE = "dominance-scoped-source-semantic-evidence-atoms-v4"

CONTEXT = shared.ActualProductEvaluationContext(
    builder=package,
    instrument_id=INSTRUMENT_ID,
    grounding_result_path=GROUNDING_RESULT,
    grounding_result_id="governed-full-autonomy-v2-1-grounding-successor-011",
    selected_grounding_architecture_id=SUCCESSOR_ARCHITECTURE,
    grounding_result_expected_architecture_id=(
        "ambiguity-safe-source-semantic-evidence-atoms-v2"
    ),
    runtime_grounding_architecture_id=SUCCESSOR_ARCHITECTURE,
    grounding_missing_blocker="grounding-successor-011-keep-missing",
    canary_case_ids=(
        "release-corpus-confirm-h-e1-trajectory-001-t1-v2-autonomous-seed-1",
        "release-corpus-confirm-h-e1-long-horizon-001",
    ),
    source_resolver=package.source_fixture_for_case,
    distractor_resolver=package.distractor_fixtures_for_case,
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
    set_valued_action_gold=True,
)


def validate_attempt() -> dict[str, object]:
    result = shared.validate(CONTEXT)
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    if instrument["method"]["request_intent_contract"] != (
        DeterministicActionRouterV3.implementation_id
    ):
        raise ValueError("confirmation 025 request-intent contract drifted")
    if instrument["execution"]["selected_evidence_gate"] != (
        "source-semantic-evidence-atom-gate-v4"
    ):
        raise ValueError("confirmation 025 must bind the v4 successor gate")
    published = instrument["dataset"]["published_sources_per_release"]
    if published < 2:
        raise ValueError(
            "confirmation 025 exists to publish a corpus; a single-source "
            "release would repeat the gap it was built to close"
        )
    return {
        **result,
        "selected_release_candidate": "t1-v2-autonomous",
        "grounding_architecture": SUCCESSOR_ARCHITECTURE,
        "published_sources_per_release": published,
        "action_gold_contract": "set-valued-valid-actions-v2",
        "request_intent_contract": DeterministicActionRouterV3.implementation_id,
        "harness_only_changes": ["multi-source-release-corpus"],
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
