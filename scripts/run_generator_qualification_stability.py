"""Run the frozen P2 development stability subset without opening held-out."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
from pathlib import Path

from scripts.run_generator_qualification import (
    GeneratorQualificationError,
    ROOT,
    build_preflight,
    execute,
    validate_assets,
)
from scripts.professor_fidelity_scoring import nearest_rank_percentile


INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/generator_qualification_v1_development_stability_001.json"
)


async def run_stability(assets):
    protocol = assets["instrument"]["stability_protocol"]
    case_ids = protocol["case_ids"]
    if len(case_ids) != 12 or len(set(case_ids)) != 12:
        raise GeneratorQualificationError(
            "stability subset must freeze 12 unique cases"
        )
    source_cases = assets["datasets"]["development"]["dataset"]["cases"]
    by_id = {case["case_id"]: case for case in source_cases}
    if set(case_ids) - set(by_id):
        raise GeneratorQualificationError("stability subset references unknown cases")
    selected = [by_id[case_id] for case_id in case_ids]
    expected_scenarios = set(assets["instrument"]["dataset"]["scenario_types"])
    if {case["scenario_type"] for case in selected} != expected_scenarios:
        raise GeneratorQualificationError("stability subset must cover every scenario")

    assets["datasets"]["development"]["dataset"] = {
        **assets["datasets"]["development"]["dataset"],
        "cases": selected,
    }
    repeats = []
    for repeat_index in range(1, protocol["repeats"] + 1):
        result = await execute(
            assets,
            split="development",
            prompt_conditions=["P2"],
        )
        for case in result["results"]:
            case["repeat_index"] = repeat_index
        repeats.append(result)

    results = [case for repeat in repeats for case in repeat["results"]]
    latencies = [case["latency_ms"] for case in results]
    total_cost = sum(repeat["cumulative_cost_usd"] for repeat in repeats)
    if total_cost >= assets["instrument"]["budget"]["development_stop_cap_usd"]:
        raise GeneratorQualificationError("stability cost stop cap reached")
    return {
        "run_type": "generator-qualification-v1-development-stability",
        "status": "stability-output-review-required",
        "instrument_id": assets["instrument"]["instrument_id"],
        "split": "development",
        "dataset_sha256": assets["datasets"]["development"]["sha256"],
        "case_ids": case_ids,
        "repeats": protocol["repeats"],
        "case_attempts": len(results),
        "completed_attempts": sum(case["completed"] for case in results),
        "deterministic_check_passes": sum(
            case["deterministic_checks_passed"] for case in results
        ),
        "cumulative_cost_usd": total_cost,
        "input_tokens": sum(case["usage"]["input_tokens"] for case in results),
        "output_tokens": sum(case["usage"]["output_tokens"] for case in results),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": nearest_rank_percentile(latencies, 0.95),
        "provider_revisions": sorted(
            {case["provider_revision"] for case in results if case["provider_revision"]}
        ),
        "private_course_external_calls": 0,
        "review_required": True,
        "results": results,
        "code_revision": repeats[0]["code_revision"],
        "working_tree_dirty": repeats[0]["working_tree_dirty"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-external-provider", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    assets = validate_assets(INSTRUMENT_PATH)
    if not arguments.execute:
        print(json.dumps(build_preflight(assets), indent=2, sort_keys=True))
        return
    if not arguments.allow_external_provider or arguments.output is None:
        parser.error("execution requires --allow-external-provider and --output")
    credential_name = assets["instrument"]["candidate_binding"][
        "credential_environment_variable"
    ]
    if not os.environ.get(credential_name, "").strip():
        raise SystemExit(f"missing environment credential: {credential_name}")
    payload = asyncio.run(run_stability(assets))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
