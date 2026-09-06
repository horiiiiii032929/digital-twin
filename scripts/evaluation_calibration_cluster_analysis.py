"""No-network diagnostic; see prospective 2026-09-06 evaluator calibration plan."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import statistics
import subprocess
from pathlib import Path

from scripts.cross_course_quality_development import (
    PACKET,
    ROOT,
    score_case,
    wilson_interval,
)

RUN_ID = "evaluation-calibration-cluster-development-20260906-001"


def cluster_interval(
    values: dict[str, list[float]], *, repeats: int = 10000, seed: int = 620906
) -> dict:
    """Equal-cluster mean percentile bootstrap; never treat nested rows as independent."""
    if not values or repeats < 100:
        raise ValueError("nonempty clusters and at least100 replicates required")
    if any(
        not rows or any(not math.isfinite(v) for v in rows) for rows in values.values()
    ):
        raise ValueError("empty or nonfinite cluster")
    means = [statistics.mean(values[k]) for k in sorted(values)]
    rng = random.Random(seed)
    draws = sorted(
        statistics.mean(rng.choices(means, k=len(means))) for _ in range(repeats)
    )
    return {
        "clusters": len(means),
        "equal_cluster_mean": statistics.mean(means),
        "percentile_95_interval": [
            draws[int(0.025 * (repeats - 1))],
            draws[int(0.975 * (repeats - 1))],
        ],
        "seed": seed,
        "replicates": repeats,
        "interpretation": "Exploratory conditional cluster resampling; few authored clusters do not qualify population inference",
    }


def paired_quality(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("empty paired sample")
    pairs: dict[str, dict] = {}
    for row in rows:
        arm = row["arm"]
        if arm not in ("incumbent", "question-specific-profile-candidate"):
            raise ValueError("unknown arm")
        pair = pairs.setdefault(row["case_id"], {})
        if arm in pair:
            raise ValueError("duplicate case arm")
        pair[arm] = row
    clusters: dict[str, list[float]] = {}
    discordance = {
        "both_pass": 0,
        "candidate_only": 0,
        "incumbent_only": 0,
        "both_fail": 0,
    }
    counts = [0, 0]
    for pair in pairs.values():
        if len(pair) != 2:
            raise ValueError("unmatched case")
        a, b = pair["incumbent"], pair["question-specific-profile-candidate"]
        if a["public_input"]["course_id"] != b["public_input"]["course_id"]:
            raise ValueError("mismatched course")
        raw = [r["score"]["mechanical_source_containment_pass"] for r in (a, b)]
        if any(type(v) is not bool for v in raw):
            raise ValueError("nonboolean mechanical score")
        x, y = raw
        counts[0] += x
        counts[1] += y
        discordance[
            "both_pass"
            if x and y
            else "candidate_only"
            if y
            else "incumbent_only"
            if x
            else "both_fail"
        ] += 1
        clusters.setdefault(a["public_input"]["course_id"], []).append(int(y) - int(x))
    n = len(pairs)
    means = {k: statistics.mean(v) for k, v in clusters.items()}
    return {
        "paired_cases": n,
        "original_pass_counts": counts,
        "discordance": discordance,
        "binomial_independence_approximation_only": [
            wilson_interval(k, n) for k in counts
        ],
        "course_differences": means,
        "course_cluster_bootstrap": cluster_interval(clusters),
        "leave_one_course_out_difference": {
            k: statistics.mean([v for c, v in means.items() if c != k]) for k in means
        }
        if len(means) > 1
        else {},
    }


def residual_advisory(response: dict) -> dict:
    """Uncovered text is review-needed, not automatically false. No semantic judge."""
    residue = response.get("text", "")
    if not isinstance(residue, str):
        return {"needs_review": True, "reason": "nontext"}
    for citation in response.get("citations", []):
        if (
            isinstance(citation, dict)
            and isinstance(citation.get("quote"), str)
            and citation["quote"]
        ):
            residue = residue.replace(citation["quote"], "")
    return {
        "needs_review": bool(residue.strip()),
        "residue": residue.strip(),
        "limitation": "Can neither validate citation truth nor distinguish good prose from unsupported prose; questions remain unscored",
    }


def calibration(packet: dict) -> list[dict]:
    case = next(
        c for c in packet["cases"] if c["public"]["case_id"] == "scheduler-explanatory"
    )
    req = case["gold"]["requirements"][0]
    clean = {
        "action": "answer",
        "text": req["quote"],
        "citations": [{**req, "version": 1}],
    }
    variants = []
    for name in [
        "clean",
        "unsupported-addition",
        "contradiction-addition",
        "missing-requirement",
        "wrong-version",
        "malformed-citation",
        "empty-text",
        "duplicate-text",
    ]:
        r = copy.deepcopy(clean)
        if name == "unsupported-addition":
            r["text"] += " Aster also sells student records to advertisers."
        if name == "contradiction-addition":
            r["text"] += " In fact, deadlines never affect scheduling."
        if name == "missing-requirement":
            r["text"] = "Aster is a scheduler."
        if name == "wrong-version":
            r["citations"][0]["version"] = 999
        if name == "malformed-citation":
            r["citations"] = [None]
        if name == "empty-text":
            r["text"] = ""
        if name == "duplicate-text":
            r["text"] += "\n" + req["quote"]
        variants.append((name, "scheduler-explanatory", r))
    for name, text in [
        ("generic-question", "What have you tried?"),
        ("irrelevant-question", "What is your favourite ice cream?"),
        (
            "paraphrased-solution",
            "The runnable job whose due time arrives first gets priority. What have you tried?",
        ),
    ]:
        variants.append(
            (
                name,
                "scheduler-socratic",
                {"action": "diagnostic-question", "text": text, "citations": []},
            )
        )
    return [
        {
            "mutation": name,
            "case_id": cid,
            "response": r,
            "baseline": score_case(packet, cid, r),
            "advisory": residual_advisory(r),
        }
        for name, cid, r in variants
    ]


def history_analysis(root: Path) -> dict:
    pairs = {}
    rows = []
    for path in sorted(root.glob("*/turns.jsonl")):
        name = path.parent.name
        arm = "autonomous" if "-autonomous-" in name else "reactive"
        key = name.replace(f"-{arm}-", "-PAIRED-")
        turns = [json.loads(line) for line in path.open()]
        if not turns:
            raise ValueError("empty history")
        failures = sum(
            t["turn"]["tutor_message"]["action"] == "safe-graph-failure" for t in turns
        )
        item = {
            "history": name,
            "arm": arm,
            "turns": len(turns),
            "failures": failures,
            "fraction": failures / len(turns),
        }
        if arm in pairs.setdefault(key, {}):
            raise ValueError("duplicate history")
        pairs[key][arm] = item
        rows.append(item)
    if any(set(pair) != {"autonomous", "reactive"} for pair in pairs.values()):
        raise ValueError("unmatched history")
    diffs = {
        k: [v["autonomous"]["fraction"] - v["reactive"]["fraction"]]
        for k, v in pairs.items()
    }
    return {
        "histories": rows,
        "matched_pairs": len(pairs),
        "autonomous_minus_reactive_guarded_failure": cluster_interval(diffs),
        "scope": "Within selected synthetic persona/profile contexts, operational failure fraction only; dependent turns, adaptive paths and one seed prevent learning/causal effect inference",
    }


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    qa = (
        ROOT
        / "reports/generated/cross-course-quality-development-001-live-005/cases.jsonl"
    )
    full = (
        ROOT
        / "reports/generated/final-profile-operational-dialogue-development-001-full-live-001"
    )
    packet = json.loads(PACKET.read_text())
    inputs = [PACKET, qa, *sorted(full.glob("*/turns.jsonl")), Path(__file__).resolve()]
    result = {
        "run_id": RUN_ID,
        "code_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            )
        ),
        "status": "completed-development-diagnostic",
        "decision": "Keep explicit review-needed advisory; Refine semantic scoring; no tutor quality promotion",
        "external_calls": 0,
        "cost_usd": 0,
        "input_hashes": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in inputs
        },
        "calibration": calibration(packet),
        "paired_quality": paired_quality([json.loads(line) for line in qa.open()]),
        "history_analysis": history_analysis(full),
        "human_review": False,
        "held_out_confirmation": False,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    r = run(args.output_dir)
    print(
        json.dumps(
            {
                "run_id": r["run_id"],
                "paired_quality": r["paired_quality"],
                "histories": r["history_analysis"]["matched_pairs"],
            }
        )
    )


if __name__ == "__main__":
    main()
