"""Independently recompute and sanitize the IT5002 rapid retrieval result."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.it5002_rapid_common import (
    HELDOUT_PATH,
    LOCAL_RUN_ROOT,
    RapidRetrievalCase,
    load_dataset,
    sha256_file,
)


DEVELOPMENT_RESULT_PATH = LOCAL_RUN_ROOT / "development_result.json"
HELDOUT_RESULT_PATH = LOCAL_RUN_ROOT / "heldout_result.json"
DEFAULT_OUTPUT = Path("reports/generated/it5002-retrieval-rapid-v1-analysis.json")
CONDITIONS = ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "O1")
FORBIDDEN_RESULT_KEYS = {"query", "text", "claims", "required_evidence"}
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 5002


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--heldout-result", type=Path, default=HELDOUT_RESULT_PATH)
    parser.add_argument(
        "--development-result",
        type=Path,
        default=DEVELOPMENT_RESULT_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--latency-contaminated", action="store_true")
    args = parser.parse_args()

    analysis = analyze(
        development_result_path=args.development_result,
        heldout_result_path=args.heldout_result,
        latency_contaminated=args.latency_contaminated,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(analysis, indent=2, sort_keys=True))


def analyze(
    *,
    development_result_path: Path,
    heldout_result_path: Path,
    latency_contaminated: bool,
) -> dict[str, Any]:
    development = _load_json(development_result_path)
    heldout = _load_json(heldout_result_path)
    dataset = load_dataset(HELDOUT_PATH)
    thresholds = {
        condition: float(values["threshold"])
        for condition, values in development["aggregate"].items()
        if condition in CONDITIONS
    }
    thresholds["R6"] = thresholds["R5"]
    thresholds["O1"] = 0.0

    forbidden_paths = _find_forbidden_keys(heldout)
    if forbidden_paths:
        raise ValueError(
            "private content fields found in held-out result: "
            + ", ".join(forbidden_paths)
        )
    scored = _score_all(dataset.cases, heldout["cases"], thresholds)
    recomputed = _aggregate(scored, heldout)
    _assert_aggregate_matches(recomputed, heldout["aggregate"])

    primary = _primary_contrast(scored)
    failures = _failure_summary(scored)
    integrity = _integrity_review(heldout, dataset.cases)
    decision = _screening_decision(
        recomputed=recomputed,
        development=development,
        heldout=heldout,
        integrity=integrity,
        latency_contaminated=latency_contaminated,
    )
    return {
        "analysis_id": "it5002-retrieval-rapid-v1-analysis",
        "run_id": heldout["run_id"],
        "dataset_id": dataset.dataset_id,
        "dataset_sha256": sha256_file(HELDOUT_PATH),
        "heldout_result_sha256": sha256_file(heldout_result_path),
        "development_result_sha256": sha256_file(development_result_path),
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "interval": "paired percentile 95%",
        },
        "integrity": integrity,
        "aggregate": recomputed,
        "slices": _slice_summary(scored),
        "primary_contrast_r5_minus_r1": primary,
        "failures": failures,
        "operational": {
            "development_clean_latency_ms": {
                condition: {
                    "p50": values["latency_p50_ms"],
                    "p95": values["latency_p95_ms"],
                }
                for condition, values in development["aggregate"].items()
            },
            "heldout_observed_latency_ms": {
                condition: {
                    "p50": values["latency_p50_ms"],
                    "p95": values["latency_p95_ms"],
                }
                for condition, values in heldout["aggregate"].items()
            },
            "heldout_latency_contaminated": latency_contaminated,
            "peak_rss_bytes": heldout["operational"]["peak_rss_bytes"],
            "model_cache_bytes": heldout["operational"]["model_cache_bytes"],
            "approximate_cost_usd": heldout["operational"]["approximate_cost_usd"],
        },
        "decision": decision,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_RESULT_KEYS:
                found.append(child_path)
            found.extend(_find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, f"{path}[{index}]"))
    return found


def _score_all(
    cases: list[RapidRetrievalCase],
    results: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    case_lookup = {case.case_id: case for case in cases}
    scored: list[dict[str, Any]] = []
    for result in results:
        case = case_lookup[result["case_id"]]
        threshold = thresholds[result["condition"]]
        predicted_answer = float(result["decision_score"]) >= threshold
        selected_hits = result["hits"][:3] if predicted_answer else []
        evidence_covered = [
            any(
                hit["document_id"] == evidence.document_id
                and hit["page_start"] is not None
                and hit["page_end"] is not None
                and hit["page_start"] <= evidence.page <= hit["page_end"]
                for hit in selected_hits
            )
            for evidence in case.required_evidence
        ]
        covered_claims = (
            sum(
                evidence_covered[min(index, len(evidence_covered) - 1)]
                for index, _claim in enumerate(case.claims)
            )
            if evidence_covered
            else 0
        )
        scored.append(
            {
                "case_id": case.case_id,
                "condition": result["condition"],
                "scenario": case.scenario,
                "expected_action": case.expected_action,
                "predicted_action": "answer" if predicted_answer else "abstain",
                "complete_evidence": bool(evidence_covered)
                and all(evidence_covered),
                "covered_claims": covered_claims,
                "total_claims": len(case.claims),
                "correct_abstention": case.expected_action == "abstain"
                and not predicted_answer,
            }
        )
    return scored


def _aggregate(
    scored: list[dict[str, Any]],
    result: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for condition in CONDITIONS:
        members = [item for item in scored if item["condition"] == condition]
        if not members:
            continue
        answerable = [
            item for item in members if item["expected_action"] == "answer"
        ]
        no_evidence = [
            item for item in members if item["expected_action"] == "abstain"
        ]
        complete = sum(item["complete_evidence"] for item in answerable)
        covered = sum(item["covered_claims"] for item in answerable)
        claims = sum(item["total_claims"] for item in answerable)
        abstained = sum(item["correct_abstention"] for item in no_evidence)
        observed = result["aggregate"][condition]
        output[condition] = {
            "eligible_cases": len(members),
            "complete_evidence": {
                "numerator": complete,
                "denominator": len(answerable),
                "value": complete / len(answerable) if answerable else None,
                "wilson_95": _wilson(complete, len(answerable)),
            },
            "claim_coverage": {
                "numerator": covered,
                "denominator": claims,
                "value": covered / claims if claims else None,
                "wilson_95": _wilson(covered, claims),
            },
            "no_evidence_accuracy": {
                "numerator": abstained,
                "denominator": len(no_evidence),
                "value": abstained / len(no_evidence) if no_evidence else None,
                "wilson_95": _wilson(abstained, len(no_evidence)),
            },
            "threshold": observed["threshold"],
            "latency_p50_ms": observed["latency_p50_ms"],
            "latency_p95_ms": observed["latency_p95_ms"],
        }
    return output


def _assert_aggregate_matches(
    recomputed: dict[str, dict[str, Any]],
    recorded: dict[str, dict[str, Any]],
) -> None:
    mappings = {
        "complete_evidence": (
            "complete_evidence_numerator",
            "answerable_denominator",
        ),
        "claim_coverage": (
            "claim_coverage_numerator",
            "claim_coverage_denominator",
        ),
        "no_evidence_accuracy": (
            "no_evidence_numerator",
            "no_evidence_denominator",
        ),
    }
    for condition, values in recomputed.items():
        for metric, (numerator, denominator) in mappings.items():
            if values[metric]["numerator"] != recorded[condition][numerator]:
                raise ValueError(f"{condition} {metric} numerator mismatch")
            if values[metric]["denominator"] != recorded[condition][denominator]:
                raise ValueError(f"{condition} {metric} denominator mismatch")


def _primary_contrast(scored: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {
        (item["condition"], item["case_id"]): item
        for item in scored
        if item["condition"] in {"R1", "R5"}
    }
    answerable_ids = sorted(
        case_id
        for condition, case_id in by_key
        if condition == "R1"
        and by_key[(condition, case_id)]["expected_action"] == "answer"
    )
    no_evidence_ids = sorted(
        case_id
        for condition, case_id in by_key
        if condition == "R1"
        and by_key[(condition, case_id)]["expected_action"] == "abstain"
    )

    complete_pairs = [
        (
            int(by_key[("R1", case_id)]["complete_evidence"]),
            int(by_key[("R5", case_id)]["complete_evidence"]),
        )
        for case_id in answerable_ids
    ]
    claim_pairs = [
        (
            by_key[("R1", case_id)]["covered_claims"],
            by_key[("R5", case_id)]["covered_claims"],
            by_key[("R1", case_id)]["total_claims"],
        )
        for case_id in answerable_ids
    ]
    abstention_pairs = [
        (
            int(by_key[("R1", case_id)]["correct_abstention"]),
            int(by_key[("R5", case_id)]["correct_abstention"]),
        )
        for case_id in no_evidence_ids
    ]
    wins = sum(control == 0 and candidate == 1 for control, candidate in complete_pairs)
    losses = sum(
        control == 1 and candidate == 0 for control, candidate in complete_pairs
    )
    return {
        "complete_evidence": {
            "difference": _binary_difference(complete_pairs),
            "net_additional_successes": wins - losses,
            "candidate_wins": wins,
            "control_wins": losses,
            "paired_bootstrap_95": _bootstrap_binary(complete_pairs),
            "mcnemar_exact_two_sided_p": _mcnemar_exact(wins, losses),
        },
        "claim_coverage": {
            "difference": _claim_difference(claim_pairs),
            "paired_bootstrap_95": _bootstrap_claims(claim_pairs),
        },
        "no_evidence_accuracy": {
            "difference": _binary_difference(abstention_pairs),
            "paired_bootstrap_95": _bootstrap_binary(abstention_pairs),
        },
    }


def _binary_difference(pairs: list[tuple[int, int]]) -> float:
    return sum(candidate - control for control, candidate in pairs) / len(pairs)


def _claim_difference(pairs: list[tuple[int, int, int]]) -> float:
    denominator = sum(total for _control, _candidate, total in pairs)
    return sum(candidate - control for control, candidate, _total in pairs) / denominator


def _bootstrap_binary(pairs: list[tuple[int, int]]) -> list[float]:
    randomizer = random.Random(BOOTSTRAP_SEED)
    values = []
    for _ in range(BOOTSTRAP_REPLICATES):
        sample = [pairs[randomizer.randrange(len(pairs))] for _ in pairs]
        values.append(_binary_difference(sample))
    return _percentile_interval(values)


def _bootstrap_claims(pairs: list[tuple[int, int, int]]) -> list[float]:
    randomizer = random.Random(BOOTSTRAP_SEED)
    values = []
    for _ in range(BOOTSTRAP_REPLICATES):
        sample = [pairs[randomizer.randrange(len(pairs))] for _ in pairs]
        values.append(_claim_difference(sample))
    return _percentile_interval(values)


def _percentile_interval(values: list[float]) -> list[float]:
    ordered = sorted(values)
    return [
        ordered[math.floor(0.025 * (len(ordered) - 1))],
        ordered[math.ceil(0.975 * (len(ordered) - 1))],
    ]


def _mcnemar_exact(wins: int, losses: int) -> float:
    discordant = wins + losses
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(wins, losses) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def _wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    estimate = successes / total
    denominator = 1 + z * z / total
    centre = (estimate + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(estimate * (1 - estimate) / total + z * z / (4 * total**2))
        / denominator
    )
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def _slice_summary(scored: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    scenarios = sorted(
        {
            item["scenario"]
            for item in scored
            if item["expected_action"] == "answer"
        }
    )
    for condition in CONDITIONS:
        condition_values: dict[str, Any] = {}
        for scenario in scenarios:
            members = [
                item
                for item in scored
                if item["condition"] == condition and item["scenario"] == scenario
            ]
            if not members:
                continue
            successes = sum(item["complete_evidence"] for item in members)
            condition_values[scenario] = {
                "numerator": successes,
                "denominator": len(members),
                "value": successes / len(members),
            }
        if condition_values:
            output[condition] = condition_values
    return output


def _failure_summary(scored: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, Counter[str]] = {}
    case_ids: dict[str, dict[str, list[str]]] = {}
    for condition in CONDITIONS:
        counts: Counter[str] = Counter()
        ids: dict[str, list[str]] = {}
        for item in scored:
            if item["condition"] != condition:
                continue
            category: str | None = None
            if (
                item["expected_action"] == "answer"
                and item["predicted_action"] == "abstain"
            ):
                category = "threshold"
            elif (
                item["expected_action"] == "answer"
                and not item["complete_evidence"]
            ):
                category = "ranking"
            elif (
                item["expected_action"] == "abstain"
                and not item["correct_abstention"]
            ):
                category = "open-set-threshold"
            if category is not None:
                counts[category] += 1
                ids.setdefault(category, []).append(item["case_id"])
        categories[condition] = counts
        case_ids[condition] = ids
    return {
        "counts_by_condition": {
            condition: dict(counts) for condition, counts in categories.items()
        },
        "case_ids_by_condition": case_ids,
        "taxonomy_note": (
            "Threshold and ranking labels are deterministic screening diagnoses; "
            "manual page-level review is still required before causal claims."
        ),
    }


def _integrity_review(
    result: dict[str, Any],
    cases: list[RapidRetrievalCase],
) -> dict[str, Any]:
    expected_counts = {
        "R0": len(cases),
        "R1": len(cases),
        "R2": len(cases),
        "R3": len(cases),
        "R4": len(cases),
        "R5": len(cases),
        "R6": sum(case.scenario == "multi_evidence" for case in cases),
        "O1": sum(case.expected_action == "answer" for case in cases),
    }
    actual_counts = Counter(item["condition"] for item in result["cases"])
    provenance_complete = all(
        all(
            hit.get("document_id")
            and hit.get("content_hash")
            and hit.get("page_start") is not None
            and hit.get("page_end") is not None
            for hit in item["hits"]
        )
        for item in result["cases"]
    )
    counts_match = all(
        actual_counts[condition] == count
        for condition, count in expected_counts.items()
    )
    return {
        "condition_counts_expected": expected_counts,
        "condition_counts_actual": dict(actual_counts),
        "condition_counts_match": counts_match,
        "provenance_complete": provenance_complete,
        "private_content_fields_absent": True,
        "aggregate_independently_recomputed": True,
        "passed": counts_match and provenance_complete,
    }


def _screening_decision(
    *,
    recomputed: dict[str, dict[str, Any]],
    development: dict[str, Any],
    heldout: dict[str, Any],
    integrity: dict[str, Any],
    latency_contaminated: bool,
) -> dict[str, Any]:
    r1 = recomputed["R1"]
    r5 = recomputed["R5"]
    clean_p95 = float(development["aggregate"]["R5"]["latency_p95_ms"])
    cache_bytes = int(heldout["operational"]["model_cache_bytes"])
    peak_rss_bytes = int(heldout["operational"]["peak_rss_bytes"])
    gates = {
        "integrity_and_provenance": integrity["passed"],
        "no_evidence_at_least_19_of_20": (
            r5["no_evidence_accuracy"]["numerator"] >= 19
        ),
        "answerable_not_more_than_two_below_r1": (
            r5["complete_evidence"]["numerator"]
            >= r1["complete_evidence"]["numerator"] - 2
        ),
        "clean_development_p95_at_most_5000_ms": clean_p95 <= 5000,
        "peak_rss_at_most_8_gib": peak_rss_bytes <= 8 * 1024**3,
        "cache_at_most_5_gib": cache_bytes <= 5 * 1024**3,
    }
    resource_or_safety_failure = not all(
        gates[name]
        for name in (
            "integrity_and_provenance",
            "no_evidence_at_least_19_of_20",
            "clean_development_p95_at_most_5000_ms",
            "peak_rss_at_most_8_gib",
            "cache_at_most_5_gib",
        )
    )
    net = (
        r5["complete_evidence"]["numerator"]
        - r1["complete_evidence"]["numerator"]
    )
    claim_regressed = (
        r5["claim_coverage"]["value"] < r1["claim_coverage"]["value"]
    )
    if resource_or_safety_failure:
        outcome = "Drop"
    elif net < 4 or claim_regressed:
        outcome = "Refine"
    else:
        outcome = "Go Deeper"
    return {
        "outcome": outcome,
        "hard_gates": gates,
        "latency_evidence": (
            "Use the clean development p95 for the frozen deployability gate. "
            "Held-out latency is retained but excluded from that claim because "
            "of documented unified-memory/MPS contamination."
            if latency_contaminated
            else "Held-out and development latency were not marked contaminated."
        ),
        "retained_fallback": "R1 heading-aware BM25",
        "keep_unavailable": True,
    }


if __name__ == "__main__":
    main()
