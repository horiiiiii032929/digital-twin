#!/usr/bin/env python3
"""Analyze and sanitize a completed professor-fidelity C0-C3 run."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("C0", "C1", "C2", "C3")
CONTRASTS = (("C1", "C0"), ("C2", "C1"), ("C3", "C2"), ("C3", "C0"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--primary-judge", type=Path)
    parser.add_argument("--sensitivity-judge", type=Path)
    parser.add_argument("--record-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")


def _primary_pedagogy(judge: dict[str, Any] | None) -> tuple[dict[tuple[str, str], bool], Counter[str]]:
    scores: dict[tuple[str, str], bool] = {}
    preferences: Counter[str] = Counter()
    if judge is None:
        return scores, preferences
    for record in judge["case_judgments"]:
        if record["repeat"]:
            continue
        mapping = record["mapping"]
        for response in record["judgment"]["responses"]:
            condition = mapping[response["label"]]
            scores[(record["case_id"], condition)] = all(
                item["label"] == "pass" for item in response["dimensions"]
            )
        preferences[record["judgment"]["c1_c2_preference"]] += 1
    return scores, preferences


def _rate(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round((len(ordered) - 1) * probability)))]


def _bootstrap_difference(pairs: list[tuple[bool, bool]]) -> dict[str, float]:
    rng = random.Random(5002)
    samples = []
    for _ in range(10000):
        selected = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        samples.append(_rate([left for left, _ in selected]) - _rate([right for _, right in selected]))
    observed = _rate([left for left, _ in pairs]) - _rate([right for _, right in pairs])
    return {"difference": observed, "ci95_low": _percentile(samples, 0.025), "ci95_high": _percentile(samples, 0.975)}


def _mcnemar(pairs: list[tuple[bool, bool]]) -> dict[str, Any]:
    left_only = sum(left and not right for left, right in pairs)
    right_only = sum(right and not left for left, right in pairs)
    discordant = left_only + right_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, index) for index in range(0, min(left_only, right_only) + 1)) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {"left_only": left_only, "right_only": right_only, "discordant": discordant, "p_value": p_value}


def _holm(records: dict[str, dict[str, Any]]) -> None:
    ordered = sorted(records.items(), key=lambda item: item[1]["mcnemar"]["p_value"])
    running = 0.0
    count = len(ordered)
    for rank, (name, record) in enumerate(ordered):
        adjusted = min(1.0, record["mcnemar"]["p_value"] * (count - rank))
        running = max(running, adjusted)
        records[name]["mcnemar"]["holm_p_value"] = running


def analyze(run: dict[str, Any], judge: dict[str, Any] | None, sensitivity: dict[str, Any] | None) -> dict[str, Any]:
    pedagogy, preferences = _primary_pedagogy(judge)
    rows_by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows_by_case: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in run["results"]:
        row = dict(row)
        row["pedagogy_success"] = pedagogy.get((row["case_id"], row["condition"]), False)
        rows_by_condition[row["condition"]].append(row)
        rows_by_case[row["case_id"]][row["condition"]] = row
    if set(rows_by_condition) != set(CONDITIONS):
        raise ValueError("run does not contain all four conditions")
    summaries = {}
    for condition in CONDITIONS:
        rows = rows_by_condition[condition]
        summaries[condition] = {
            "n": len(rows),
            "safe_grounded_success": _rate([row["score"]["safe_grounded_success"] for row in rows]),
            "hard_gate_pass_rate": _rate([row["score"]["hard_gate_passed"] for row in rows]),
            "citation_validity": _rate([row["score"]["citation_validity"] for row in rows]),
            "citation_completeness": _rate([row["score"]["citation_completeness"] for row in rows]),
            "complete_evidence_at_3": _rate([row["score"]["complete_evidence_at_3"] for row in rows]),
            "no_evidence_accuracy": _rate([row["score"]["action_passed"] for row in rows if row["scenario_type"] == "no_evidence"]),
            "professor_policy_pedagogy_proxy": None if judge is None else _rate([row["pedagogy_success"] for row in rows]),
            "latency_p50_ms": statistics.median(row["latency_ms"] for row in rows),
            "latency_p95_ms": _percentile([row["latency_ms"] for row in rows], 0.95),
            "failures": sum(not row["score"]["safe_grounded_success"] for row in rows),
        }
    contrasts = {}
    for left, right in CONTRASTS:
        pairs = [
            (portfolio[left]["score"]["safe_grounded_success"], portfolio[right]["score"]["safe_grounded_success"])
            for portfolio in rows_by_case.values()
        ]
        name = f"{left}_vs_{right}"
        contrasts[name] = {**_bootstrap_difference(pairs), "mcnemar": _mcnemar(pairs)}
    _holm(contrasts)
    hard_failures = sum(not row["score"]["hard_gate_passed"] for row in rows_by_condition["C3"])
    c3 = summaries["C3"]
    c3_c0 = contrasts["C3_vs_C0"]["difference"]
    c3_c2 = contrasts["C3_vs_C2"]["difference"]
    gates = {
        "zero_c3_hard_gate_failures": hard_failures == 0,
        "c3_safe_grounded_success_at_least_0_80": c3["safe_grounded_success"] >= 0.80,
        "pedagogy_resolved": judge is not None,
        "c3_pedagogy_proxy_at_least_0_80": judge is not None and c3["professor_policy_pedagogy_proxy"] >= 0.80,
        "c3_over_c0_gain_at_least_0_10": c3_c0 >= 0.10,
        "c3_below_c2_loss_at_most_0_10": c3_c2 >= -0.10,
        "reliable_completion_at_least_0_95": run["condition_attempts"] == run["case_count"] * 4,
        "p95_latency_at_most_10_seconds": c3["latency_p95_ms"] <= 10000,
    }
    decision = "keep" if all(gates.values()) else "refine"
    failures = [
        {"case_id": row["case_id"], "scenario_type": row["scenario_type"], "failed_checks": sorted(key for key, passed in row["score"].items() if isinstance(passed, bool) and not passed)}
        for row in rows_by_condition["C3"] if not row["score"]["safe_grounded_success"]
    ][:8]
    return {
        "result_id": run["run_id"], "status": "development-refine" if run.get("split") == "development" else "valid-complete", "decision": decision,
        "sample_size": run["case_count"], "condition_attempts": run["condition_attempts"],
        "condition_summaries": summaries, "contrasts": contrasts,
        "c1_c2_pairwise_preference": dict(preferences), "decision_gates": gates,
        "operational": {key: run[key] for key in ("cost_usd", "input_tokens", "output_tokens", "latency_p50_ms", "latency_p95_ms", "provider_model", "provider_revision", "retrieval")},
        "judge": {"primary": None if judge is None else {"model": judge["model"], "digest": judge["model_digest"], "calibration_claim": "researcher-anchor-calibrated proxy only"}, "sensitivity": None if sensitivity is None else {"model": sensitivity["model"], "digest": sensitivity["model_digest"], "sample_rate": sensitivity["sample_rate"]}},
        "representative_failures": failures,
        "limitations": [
            "Pedagogy is an automated researcher-anchor-calibrated proxy, not independent professor or human outcome evidence.",
            "Eligible private course text was processed by the authorized DeepSeek API; provider disk caching and the absence of a project-specific no-training guarantee remain data-boundary limitations.",
            "The course-tutor cases are synthetic transformations and do not establish student learning, usability, satisfaction, or adoption.",
            "Automated pedagogy is unresolved because the local judge failed the frozen calibration boundary and no genuinely blinded researcher reference exists.",
            "Required-claim recall uses exact phrase matching; the anchor exposed paraphrase false negatives, so safe-grounded success is conservative and not a final semantic-quality estimate.",
            "The one-time held-out split remains unopened because development C3 failed prospective floors.",
        ],
    }


def render_report(result: dict[str, Any]) -> str:
    summaries = result["condition_summaries"]
    lines = [
        "# Professor-fidelity C0-C3 result", "",
        f"Decision: **{result['decision'].title()}**. The one-time {result['sample_size']}-case comparison completed across {result['condition_attempts']} condition attempts.", "",
        "## Main result", "",
        "| Condition | Safe grounded success | Pedagogy proxy | Citation validity | Complete evidence@3 | p95 latency |", "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        row = summaries[condition]
        pedagogy = "Unresolved" if row["professor_policy_pedagogy_proxy"] is None else f"{row['professor_policy_pedagogy_proxy']:.1%}"
        lines.append(f"| {condition} | {row['safe_grounded_success']:.1%} | {pedagogy} | {row['citation_validity']:.1%} | {row['complete_evidence_at_3']:.1%} | {row['latency_p95_ms'] / 1000:.2f}s |")
    lines += ["", "## Controlled effects", ""]
    for name, contrast in result["contrasts"].items():
        lines.append(f"- {name.replace('_', ' ')}: {contrast['difference']:+.1%} (95% bootstrap CI {contrast['ci95_low']:+.1%} to {contrast['ci95_high']:+.1%}; Holm-adjusted p={contrast['mcnemar']['holm_p_value']:.3f}).")
    lines += ["", "## Gates and limitations", ""]
    for name, passed in result["decision_gates"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — {name.replace('_', ' ')}")
    lines += ["", *[f"- {item}" for item in result["limitations"]], ""]
    return "\n".join(lines)


def main() -> None:
    arguments = parse_args()
    run = load_json(arguments.run)
    primary = load_json(arguments.primary_judge) if arguments.primary_judge else None
    sensitivity = load_json(arguments.sensitivity_judge) if arguments.sensitivity_judge else None
    result = analyze(run, primary, sensitivity)
    write_json(arguments.record_output, result)
    arguments.report_output.parent.mkdir(parents=True, exist_ok=True)
    arguments.report_output.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"result_id": result["result_id"], "decision": result["decision"], "sample_size": result["sample_size"]}, indent=2))


if __name__ == "__main__":
    main()
