#!/usr/bin/env python3
"""Rescore and analyze a completed professor-fidelity C0-C3 run.

The analyzer never trusts score fields embedded by an older runner. It rebuilds
deterministic metrics from the frozen dataset, tutor outputs, and retrieved
source metadata. Semantic support and pedagogy remain unresolved unless an
eligible blinded review or calibrated judge result is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import jsonschema

from scripts.professor_fidelity_scoring import (
    nearest_rank_percentile,
    score_response,
)


ROOT = Path(__file__).resolve().parents[1]
BLINDED_REVIEW_SCHEMA = (
    ROOT
    / "research/05_evaluation/instruments/"
    "professor_fidelity_blinded_review_v1.schema.json"
)
CONDITIONS = ("C0", "C1", "C2", "C3")
CONTRASTS = (("C1", "C0"), ("C2", "C1"), ("C3", "C2"), ("C3", "C0"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--primary-judge", type=Path)
    parser.add_argument("--judge-calibration", type=Path)
    parser.add_argument("--blinded-review", type=Path)
    parser.add_argument("--record-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric(values: list[bool | None]) -> dict[str, Any]:
    applicable = [value for value in values if value is not None]
    unresolved = sum(value is None for value in values)
    passed = sum(bool(value) for value in applicable)
    return {
        "value": passed / len(applicable) if applicable and unresolved == 0 else None,
        "passed": passed,
        "total": len(values),
        "applicable": len(applicable),
        "unresolved": unresolved,
        "resolved": bool(values) and unresolved == 0,
    }


def _applicable_metric(values: list[bool | None]) -> dict[str, Any]:
    applicable = [value for value in values if value is not None]
    passed = sum(bool(value) for value in applicable)
    return {
        "value": passed / len(applicable) if applicable else None,
        "passed": passed,
        "total": len(applicable),
        "applicable": len(applicable),
        "unresolved": 0,
        "resolved": bool(applicable),
    }


def _bootstrap_difference(pairs: list[tuple[bool, bool]]) -> dict[str, float]:
    rng = random.Random(5002)
    samples = []
    for _ in range(10000):
        selected = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        samples.append(
            sum(left for left, _ in selected) / len(selected)
            - sum(right for _, right in selected) / len(selected)
        )
    observed = (
        sum(left for left, _ in pairs) / len(pairs)
        - sum(right for _, right in pairs) / len(pairs)
    )
    return {
        "difference": observed,
        "ci95_low": nearest_rank_percentile(samples, 0.025),
        "ci95_high": nearest_rank_percentile(samples, 0.975),
    }


def _mcnemar(pairs: list[tuple[bool, bool]]) -> dict[str, Any]:
    left_only = sum(left and not right for left, right in pairs)
    right_only = sum(right and not left for left, right in pairs)
    discordant = left_only + right_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, index)
            for index in range(0, min(left_only, right_only) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "left_only": left_only,
        "right_only": right_only,
        "discordant": discordant,
        "p_value": p_value,
    }


def _holm(records: dict[str, dict[str, Any]]) -> None:
    ordered = sorted(records.items(), key=lambda item: item[1]["mcnemar"]["p_value"])
    running = 0.0
    count = len(ordered)
    for rank, (name, record) in enumerate(ordered):
        adjusted = min(1.0, record["mcnemar"]["p_value"] * (count - rank))
        running = max(running, adjusted)
        records[name]["mcnemar"]["holm_p_value"] = running


def _paired_contrasts(
    rows_by_case: dict[str, dict[str, dict[str, Any]]],
    field: str,
) -> dict[str, Any] | None:
    if any(
        portfolio[condition][field] is None
        for portfolio in rows_by_case.values()
        for condition in CONDITIONS
    ):
        return None
    records = {}
    for left, right in CONTRASTS:
        pairs = [
            (bool(portfolio[left][field]), bool(portfolio[right][field]))
            for portfolio in rows_by_case.values()
        ]
        records[f"{left}_vs_{right}"] = {
            **_bootstrap_difference(pairs),
            "mcnemar": _mcnemar(pairs),
        }
    _holm(records)
    return records


def _review_labels(
    review: dict[str, Any] | None,
    run_id: str,
    dataset_sha256: str,
) -> tuple[
    dict[tuple[str, str], bool],
    dict[tuple[str, str], bool],
    dict[tuple[str, str], bool],
    dict[tuple[str, str], bool],
    dict[str, Any],
]:
    if review is None:
        return {}, {}, {}, {}, {
            "eligible": False,
            "reason": "no blinded review supplied",
        }
    jsonschema.Draft202012Validator(
        load_json(BLINDED_REVIEW_SCHEMA),
        format_checker=jsonschema.FormatChecker(),
    ).validate(review)
    reviewer = review.get("reviewer", {})
    eligible = all(
        (
            review.get("status") == "complete",
            review.get("source_run_id") == run_id,
            review.get("dataset_sha256") == dataset_sha256,
            reviewer.get("blinded_to_conditions") is True,
            reviewer.get("role") in {"researcher", "professor"},
        )
    )
    if not eligible:
        return {}, {}, {}, {}, {
            "eligible": False,
            "reason": "review is incomplete, unblinded, or bound to another run",
        }
    semantic: dict[tuple[str, str], bool] = {}
    citation_completeness: dict[tuple[str, str], bool] = {}
    presented_evidence_completeness: dict[tuple[str, str], bool] = {}
    pedagogy: dict[tuple[str, str], bool] = {}
    for item in review.get("judgments", []):
        key = (item["case_id"], item["condition"])
        if key in semantic:
            raise ValueError(f"duplicate blinded review judgment: {key}")
        semantic[key] = all(
            item[field] is True
            for field in (
                "required_claim_expression",
                "supported_claim_precision",
                "citation_semantic_alignment",
                "citation_completeness",
            )
        )
        citation_completeness[key] = item["citation_completeness"]
        presented_evidence_completeness[key] = item[
            "presented_evidence_completeness"
        ]
        dimensions = item.get("pedagogy_dimensions", [])
        pedagogy[key] = bool(dimensions) and all(
            dimension["label"] == "pass" for dimension in dimensions
        )
    return (
        semantic,
        citation_completeness,
        presented_evidence_completeness,
        pedagogy,
        {
            "eligible": True,
            "review_id": review.get("review_id"),
            "reviewer_role": reviewer["role"],
            "independent_human_review": reviewer.get(
                "independent_human_review", False
            ),
        },
    )


def _judge_labels(
    judge: dict[str, Any] | None,
    calibration: dict[str, Any] | None,
) -> tuple[dict[tuple[str, str], bool], Counter[str], dict[str, Any]]:
    if judge is None:
        return {}, Counter(), {"eligible": False, "reason": "no judge supplied"}
    if calibration is None or calibration.get("automated_pedagogy_eligible") is not True:
        return {}, Counter(), {
            "eligible": False,
            "reason": "judge calibration is absent or ineligible",
        }
    scores: dict[tuple[str, str], bool] = {}
    preferences: Counter[str] = Counter()
    for record in judge["case_judgments"]:
        if record["repeat"]:
            continue
        mapping = record["mapping"]
        for response in record["judgment"]["responses"]:
            condition = mapping[response["label"]]
            scores[(record["case_id"], condition)] = all(
                item["label"] == "pass" for item in response["dimensions"]
            )
        for pairwise in record["judgment"].get("c1_c2_pairwise", []):
            preferences[pairwise["preference"]] += 1
    return scores, preferences, {
        "eligible": True,
        "model": judge["model"],
        "digest": judge["model_digest"],
        "calibration_id": calibration.get("calibration_id"),
    }


def _rescore_rows(
    run: dict[str, Any],
    dataset: dict[str, Any],
    semantic_review: dict[tuple[str, str], bool],
    citation_completeness_review: dict[tuple[str, str], bool],
    presented_evidence_review: dict[tuple[str, str], bool],
    pedagogy_review: dict[tuple[str, str], bool],
    judge_pedagogy: dict[tuple[str, str], bool],
) -> list[dict[str, Any]]:
    cases = {case["case_id"]: case for case in dataset["cases"]}
    if len(cases) != len(dataset["cases"]) or len(cases) != run["case_count"]:
        raise ValueError("dataset case identities or run case count drifted")
    run_case_ids = {row["case_id"] for row in run["results"]}
    if run_case_ids != set(cases):
        raise ValueError("run and dataset case IDs do not match")
    rescored = []
    seen: set[tuple[str, str]] = set()
    for original in run["results"]:
        row = dict(original)
        key = (row["case_id"], row["condition"])
        if row["condition"] not in CONDITIONS or key in seen:
            raise ValueError(f"duplicate or invalid condition row: {key}")
        seen.add(key)
        output = {
            "answer": row["answer"],
            "citation_ids": row["citation_ids"],
            "action": row["score"]["actual_action"],
        }
        score = score_response(cases[row["case_id"]], output, row["retrieved"])
        requires_semantic_review = (
            score["deterministic_structural_success"]
            and score["actual_action"] == "answer"
            and score["citation_applicable_claims"] > 0
        )
        if not score["deterministic_structural_success"]:
            safe_grounded: bool | None = False
        elif requires_semantic_review:
            safe_grounded = semantic_review.get(key)
        else:
            safe_grounded = True
        score["semantic_support_resolved"] = not requires_semantic_review or key in semantic_review
        score["safe_grounded_success"] = safe_grounded
        score["citation_completeness"] = (
            citation_completeness_review.get(key)
            if score["citation_applicable_claims"] > 0
            else None
        )
        score["reviewed_presented_evidence_completeness"] = (
            presented_evidence_review.get(key)
            if score["complete_evidence_eligible"]
            else None
        )
        row["score"] = score
        row["pedagogy_success"] = pedagogy_review.get(key, judge_pedagogy.get(key))
        rescored.append(row)
    return rescored


def analyze(
    run: dict[str, Any],
    dataset: dict[str, Any],
    judge: dict[str, Any] | None = None,
    calibration: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if run["condition_attempts"] != len(run["results"]):
        raise ValueError("condition-attempt ledger does not match result rows")
    if run["condition_attempts"] != run["case_count"] * len(CONDITIONS):
        raise ValueError("condition-attempt ledger is not a complete C0-C3 portfolio")
    (
        semantic_review,
        citation_completeness_review,
        presented_evidence_review,
        pedagogy_review,
        review_status,
    ) = _review_labels(
        review, run["run_id"], run["dataset_sha256"]
    )
    judge_pedagogy, preferences, judge_status = _judge_labels(judge, calibration)
    rows = _rescore_rows(
        run,
        dataset,
        semantic_review,
        citation_completeness_review,
        presented_evidence_review,
        pedagogy_review,
        judge_pedagogy,
    )
    rows_by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows_by_case: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        rows_by_condition[row["condition"]].append(row)
        rows_by_case[row["case_id"]][row["condition"]] = row
    if set(rows_by_condition) != set(CONDITIONS):
        raise ValueError("run does not contain all four conditions")
    if any(set(portfolio) != set(CONDITIONS) for portfolio in rows_by_case.values()):
        raise ValueError("one or more cases has an incomplete condition portfolio")

    summaries: dict[str, dict[str, Any]] = {}
    for condition in CONDITIONS:
        condition_rows = rows_by_condition[condition]
        citation_required_rows = [
            row
            for row in condition_rows
            if row["score"]["citation_applicable_claims"] > 0
        ]
        latencies = [row["latency_ms"] for row in condition_rows]
        summaries[condition] = {
            "n": len(condition_rows),
            "safe_grounded_success": _metric(
                [row["score"]["safe_grounded_success"] for row in condition_rows]
            ),
            "deterministic_structural_success": _applicable_metric(
                [row["score"]["deterministic_structural_success"] for row in condition_rows]
            ),
            "action_accuracy": _applicable_metric(
                [row["score"]["action_passed"] for row in condition_rows]
            ),
            "citation_identity_validity": _applicable_metric(
                [row["score"]["citation_identity_validity"] for row in condition_rows]
            ),
            "citation_source_correctness": _applicable_metric(
                [row["score"]["citation_source_correctness"] for row in citation_required_rows]
            ),
            "citation_claim_source_coverage": _applicable_metric(
                [
                    row["score"]["citation_claim_source_coverage"]
                    for row in citation_required_rows
                ]
            ),
            "citation_completeness": _metric(
                [row["score"]["citation_completeness"] for row in citation_required_rows]
            ),
            "complete_evidence_at_3": _applicable_metric(
                [row["score"]["complete_evidence_at_3"] for row in condition_rows]
            ),
            "source_locator_evidence_at_3": _applicable_metric(
                [
                    row["score"]["source_locator_evidence_at_3"]
                    for row in condition_rows
                ]
            ),
            "reviewed_presented_evidence_completeness": _metric(
                [
                    row["score"]["reviewed_presented_evidence_completeness"]
                    for row in condition_rows
                    if row["score"]["complete_evidence_eligible"]
                ]
            ),
            "no_evidence_accuracy": _applicable_metric(
                [
                    row["score"]["action_passed"]
                    for row in condition_rows
                    if row["scenario_type"] == "no_evidence"
                ]
            ),
            "pedagogical_success": _metric(
                [row["pedagogy_success"] for row in condition_rows]
            ),
            "latency_p50_ms": statistics.median(latencies),
            "latency_p95_ms": nearest_rank_percentile(latencies, 0.95),
        }

    structural_contrasts = _paired_contrasts(
        {
            case_id: {
                condition: {
                    "deterministic_structural_success": row["score"][
                        "deterministic_structural_success"
                    ]
                }
                for condition, row in portfolio.items()
            }
            for case_id, portfolio in rows_by_case.items()
        },
        "deterministic_structural_success",
    )
    safe_contrasts = _paired_contrasts(
        {
            case_id: {
                condition: {
                    "safe_grounded_success": row["score"]["safe_grounded_success"]
                }
                for condition, row in portfolio.items()
            }
            for case_id, portfolio in rows_by_case.items()
        },
        "safe_grounded_success",
    )

    c3 = summaries["C3"]
    requested = run.get("requested_attempts", run["case_count"] * len(CONDITIONS))
    completed = run.get(
        "completed_attempts",
        sum(row.get("status", "completed") == "completed" for row in run["results"]),
    )
    completion_rate = completed / requested if requested else 0.0
    safe_resolved = c3["safe_grounded_success"]["resolved"]
    pedagogy_resolved = c3["pedagogical_success"]["resolved"]
    c3_c0 = None if safe_contrasts is None else safe_contrasts["C3_vs_C0"]["difference"]
    c3_c2 = None if safe_contrasts is None else safe_contrasts["C3_vs_C2"]["difference"]
    c3_hard_failures = sum(
        not row["score"]["deterministic_hard_gates_passed"]
        for row in rows_by_condition["C3"]
    )
    dataset_human_reviewed = all(
        case.get("annotation", {}).get("status")
        in {"single_review", "professor_approved"}
        and bool(case.get("annotation", {}).get("reviewer_ids"))
        for case in dataset["cases"]
    )
    expected_retrieval_binding = {
        "implementation_id": "qwen3-hybrid-v1",
        "implementation_version": "cross-course-retrieval-v1",
        "chunker_implementation_id": "page-bounded-heading-paragraph-chunker",
        "chunker_version": "v1",
        "corpus_id": "it5002-lectures-v1",
    }
    retrieval_binding = run.get("retrieval_binding", {})
    candidate_binding_resolved = all(
        retrieval_binding.get(key) == value
        for key, value in expected_retrieval_binding.items()
    )
    condition_binding_resolved = bool(run.get("conditions_sha256"))
    policy_prompt_binding_resolved = all(
        (
            run.get("policy_binding_sha256"),
            run.get("prompt_binding")
            == "professor-fidelity-integration-prompt-v2",
        )
    )
    gates = {
        "dataset_human_authoring_review": dataset_human_reviewed,
        "selected_retrieval_and_chunker_identity": candidate_binding_resolved,
        "condition_set_hash_bound": condition_binding_resolved,
        "policy_and_prompt_hash_bound": policy_prompt_binding_resolved,
        "zero_c3_deterministic_hard_gate_failures": c3_hard_failures == 0,
        "semantic_support_resolved": safe_resolved,
        "c3_safe_grounded_success_at_least_0_80": (
            safe_resolved and c3["safe_grounded_success"]["value"] >= 0.80
        ),
        "c3_complete_evidence_at_3_at_least_0_80": (
            c3["complete_evidence_at_3"]["value"] is not None
            and c3["complete_evidence_at_3"]["value"] >= 0.80
        ),
        "c3_citation_source_correctness_at_least_0_95": (
            c3["citation_source_correctness"]["value"] is not None
            and c3["citation_source_correctness"]["value"] >= 0.95
        ),
        "c3_citation_completeness_at_least_0_95": (
            c3["citation_completeness"]["value"] is not None
            and c3["citation_completeness"]["value"] >= 0.95
        ),
        "pedagogy_resolved": pedagogy_resolved,
        "c3_pedagogy_at_least_0_80": (
            pedagogy_resolved and c3["pedagogical_success"]["value"] >= 0.80
        ),
        "c3_over_c0_gain_at_least_0_10": c3_c0 is not None and c3_c0 >= 0.10,
        "c3_below_c2_loss_at_most_0_10": c3_c2 is not None and c3_c2 >= -0.10,
        "reliable_completion_at_least_0_95": completion_rate >= 0.95,
        "p95_latency_at_most_10_seconds": c3["latency_p95_ms"] <= 10000,
    }
    decision = "keep" if all(gates.values()) else "refine"
    failures = []
    for row in rows_by_condition["C3"]:
        failed = [
            key
            for key, passed in row["score"].items()
            if isinstance(passed, bool) and not passed
        ]
        if row["score"]["safe_grounded_success"] is not True:
            failures.append(
                {
                    "case_id": row["case_id"],
                    "scenario_type": row["scenario_type"],
                    "failed_checks": sorted(failed),
                    "semantic_review_pending": row["score"]["safe_grounded_success"] is None,
                }
            )

    return {
        "result_id": f"{run['run_id']}-analysis-correction-001",
        "source_run_id": run["run_id"],
        "status": "analysis-corrected-development-refine",
        "decision": decision,
        "sample_size": run["case_count"],
        "condition_attempts": run["condition_attempts"],
        "completed_attempts": completed,
        "requested_attempts": requested,
        "reliable_completion": completion_rate,
        "condition_summaries": summaries,
        "primary_safe_grounded_contrasts": safe_contrasts,
        "diagnostic_structural_contrasts": structural_contrasts,
        "c1_c2_pairwise_preferences": dict(preferences),
        "decision_gates": gates,
        "review": review_status,
        "judge": judge_status,
        "binding_audit": {
            "dataset_human_reviewed": dataset_human_reviewed,
            "expected_retrieval_binding": expected_retrieval_binding,
            "observed_retrieval_binding": retrieval_binding or None,
            "condition_set_hash_bound": condition_binding_resolved,
            "policy_prompt_binding_resolved": policy_prompt_binding_resolved,
        },
        "operational": {
            key: run[key]
            for key in (
                "cost_usd",
                "input_tokens",
                "output_tokens",
                "latency_p50_ms",
                "latency_p95_ms",
                "provider_model",
                "provider_revision",
                "retrieval",
            )
        },
        "source_code_revision": run["code_revision"],
        "analysis_code_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "representative_failures": failures[:12],
        "limitations": [
            "Safe-grounded success and its paired effects are unresolved until blinded semantic review covers every structurally passing answer.",
            "The source run did not bind the selected page-bounded chunker, exact retrieved passage IDs, the condition-set hash, or a hash-frozen shared policy; its C3 outputs are not evidence for the selected M2 product condition.",
            "The v1.1 course-tutor cases were not independently human reviewed and leaked case-specific expected actions into the historical C2/C3 prompt, so condition effects are diagnostic only.",
            "Pedagogy is unresolved because the earlier local-judge implementation drifted from the frozen per-dimension pairwise contract and no eligible blinded reference exists.",
            "Citation source correctness and claim-source coverage verify source/page alignment only; they do not establish semantic entailment or true citation completeness.",
            "The course-tutor cases are synthetic transformations and do not establish learning, usability, satisfaction, adoption, or professor equivalence.",
            "Eligible private course text was processed by the authorized DeepSeek API; provider disk caching and the absence of a project-specific no-training guarantee remain data-boundary limitations.",
            "The one-time held-out split remains unopened because development gates failed.",
        ],
    }


def _display(metric: dict[str, Any]) -> str:
    if metric["value"] is None:
        return f"Unresolved ({metric['unresolved']} pending)"
    return f"{metric['passed']}/{metric['applicable']} ({metric['value']:.1%})"


def render_report(result: dict[str, Any]) -> str:
    summaries = result["condition_summaries"]
    lines = [
        "# Professor-fidelity C0-C3 corrected analysis",
        "",
        f"Decision: **{result['decision'].title()}**. This correction rescored {result['condition_attempts']}/{result['requested_attempts']} preserved tutor outputs without new provider calls.",
        "",
        "## Corrected measurements",
        "",
        "| Condition | Safe grounded | Structural success | Action | Citation source correctness | Claim-source coverage | Semantic citation completeness | Exact evidence@3 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        row = summaries[condition]
        lines.append(
            f"| {condition} | {_display(row['safe_grounded_success'])} | "
            f"{_display(row['deterministic_structural_success'])} | "
            f"{_display(row['action_accuracy'])} | "
            f"{_display(row['citation_source_correctness'])} | "
            f"{_display(row['citation_claim_source_coverage'])} | "
            f"{_display(row['citation_completeness'])} | "
            f"{_display(row['complete_evidence_at_3'])} |"
        )
    lines += [
        "",
        "Safe-grounded and pedagogical success remain unresolved. Structural success is a diagnostic, not a substitute for semantic review.",
        "",
        "## Decision gates",
        "",
    ]
    for name, passed in result["decision_gates"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — {name.replace('_', ' ')}")
    lines += ["", "## Limitations", ""]
    lines.extend(f"- {item}" for item in result["limitations"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    arguments = parse_args()
    run = load_json(arguments.run)
    dataset = load_json(arguments.dataset)
    if sha256(arguments.dataset) != run["dataset_sha256"]:
        raise ValueError("dataset hash does not match the source run")
    result = analyze(
        run,
        dataset,
        load_json(arguments.primary_judge) if arguments.primary_judge else None,
        load_json(arguments.judge_calibration) if arguments.judge_calibration else None,
        load_json(arguments.blinded_review) if arguments.blinded_review else None,
    )
    write_json(arguments.record_output, result)
    arguments.report_output.parent.mkdir(parents=True, exist_ok=True)
    arguments.report_output.write_text(render_report(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "result_id": result["result_id"],
                "decision": result["decision"],
                "sample_size": result["sample_size"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
