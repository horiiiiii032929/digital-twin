"""Compare frozen paired revision controls using externally reviewed final text."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random


def reviewed_cases(packet: dict, review: dict) -> dict:
    """Reject incomplete, duplicated, or internally contradictory judgments."""
    rows = review["cases"]
    expected = {row["id"] for row in packet["contexts"]}
    actual = {row["id"] for row in rows}
    if len(rows) != len(actual) or actual != expected:
        raise ValueError("Review must cover every control exactly once")
    for row in rows:
        if any(type(row.get(key)) is not bool for key in ("useful", "critical", "uncertain")):
            raise ValueError("Explicit boolean judgments required")
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            raise ValueError("Per-case judgment rationale required")
        if row["useful"] and (row["critical"] or row["uncertain"]):
            raise ValueError("Critical or uncertain content cannot qualify as useful")
    return {row["id"]: row for row in rows}


def paired_statistics(packet: dict, baseline: dict, candidate: dict,
                      *, repeats: int = 10000, seed: int = 8801) -> dict:
    """Resample scenario pairs within families, retaining both draft conditions."""
    if repeats < 1:
        raise ValueError("Positive bootstrap repeat count required")
    pairs = defaultdict(list)
    for row in packet["contexts"]:
        pairs[row["pair_id"]].append(row)
    strata = defaultdict(list)
    for pair_id, rows in sorted(pairs.items()):
        if len(rows) != 2 or {row["gold"]["draft_adequate"] for row in rows} != {True, False}:
            raise ValueError("Every scenario must retain adequate and flawed controls")
        if len({row["family"] for row in rows}) != 1:
            raise ValueError("A scenario pair cannot cross families")
        difference = sum(int(candidate[r["id"]]["useful"]) - int(baseline[r["id"]]["useful"])
                         for r in rows)
        strata[rows[0]["family"]].append(difference)
    count = len(packet["contexts"])
    if not count:
        raise ValueError("Nonempty paired packet required")
    generator = random.Random(seed)
    samples = sorted(100 * sum(sum(generator.choice(values) for _ in values)
                              for _, values in sorted(strata.items())) / count
                     for _ in range(repeats))

    def quantile(probability):
        position = (len(samples) - 1) * probability
        lower = int(position)
        upper = min(lower + 1, len(samples) - 1)
        return samples[lower] + (position - lower) * (samples[upper] - samples[lower])

    improvements = [key for key in baseline if candidate[key]["useful"] and not baseline[key]["useful"]]
    regressions = [key for key in baseline if baseline[key]["useful"] and not candidate[key]["useful"]]
    return {"scenario_pairs": len(pairs), "family_pair_counts": {k: len(v) for k, v in strata.items()},
            "useful_difference_percentage_points": 100 * (len(improvements) - len(regressions)) / count,
            "exploratory_95_percentile_interval": [quantile(.025), quantile(.975)],
            "improved_ids": sorted(improvements), "regressed_ids": sorted(regressions),
            "bootstrap_repeats": repeats, "bootstrap_seed": seed,
            "limitation": "Conditional on authored scenario pairs and one provider draw per arm; not a population accuracy guarantee or independent human validation."}


def summarize_arm(packet: dict, rows: dict) -> dict:
    slices = defaultdict(list)
    for context in packet["contexts"]:
        judgment = rows[context["id"]]
        action = context["public"]["draft"]["action"]
        for key in ("all", "family:" + context["family"],
                    "adequate" if context["gold"]["draft_adequate"] else "flawed",
                    "global_branch" if action in {"instruction", "partial"} else "base_branch",
                    "action:" + action):
            slices[key].append(judgment)
    return {key: {"total": len(values), **{field: sum(row[field] for row in values)
                                        for field in ("useful", "critical", "uncertain")}}
            for key, values in sorted(slices.items())}


def analyze(packet_path: Path, baseline_dir: Path, candidate_dir: Path,
            baseline_review_path: Path, candidate_review_path: Path) -> dict:
    packet_bytes = packet_path.read_bytes()
    digest = hashlib.sha256(packet_bytes).hexdigest()
    packet = json.loads(packet_bytes)
    if len(packet["contexts"]) != 112:
        raise ValueError("Preregistered study requires exactly112 controls")
    arms, indexed, provenance = {}, {}, {}
    for name, directory, review_path in (("v14-medium", baseline_dir, baseline_review_path),
                                        ("v16", candidate_dir, candidate_review_path)):
        manifest = json.loads((directory / "manifest.json").read_text())
        summary = json.loads((directory / "summary.json").read_text())
        review = json.loads(review_path.read_text())
        review_digest = review.get("packet_sha256", review.get("manifest", {}).get("packet_sha256"))
        if manifest["packet_sha256"] != digest or review_digest != digest:
            raise ValueError("Review, live manifest and current packet must agree")
        if (directory / "packet.json").read_bytes() != packet_bytes or manifest["candidate"] != name:
            raise ValueError("Wrong candidate or archived packet")
        indexed[name] = reviewed_cases(packet, review)
        raw_rows = [json.loads(line) for line in (directory / "cases.jsonl").read_text().splitlines()]
        if len(raw_rows) != 112 or {r["id"] for r in raw_rows} != set(indexed[name]):
            raise ValueError("Complete raw evidence required")
        raw_by_id = {r["id"]: r for r in raw_rows}
        for context in packet["contexts"]:
            if raw_by_id[context["id"]]["public_input"] != context["public"]:
                raise ValueError("Raw public input differs from frozen packet")
        operational = {key: summary[key] for key in ("completed", "provider_attempts", "provider_failures",
                        "unknown_cost_calls", "known_reported_cost_usd", "source_files_unchanged", "wall_seconds")}
        arms[name] = {"slices": summarize_arm(packet, indexed[name]), "operational": operational}
        provenance[name] = {"manifest": manifest, "review_path": str(review_path),
                            "review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
                            "cases_sha256": hashlib.sha256((directory / "cases.jsonl").read_bytes()).hexdigest()}
    candidate = arms["v16"]["slices"]
    operational_pass = all(arm["operational"]["completed"] == 112
                           and arm["operational"]["provider_attempts"] == 112
                           and arm["operational"]["provider_failures"] == 0
                           and arm["operational"]["unknown_cost_calls"] == 0
                           and arm["operational"]["source_files_unchanged"] for arm in arms.values())
    gates = {"adequate_at_least54": candidate["adequate"]["useful"] >= 54,
             "flawed_at_least54": candidate["flawed"]["useful"] >= 54,
             "each_family_at_least26": all(v["useful"] >= 26 for k, v in candidate.items() if k.startswith("family:")),
             "zero_critical": candidate["all"]["critical"] == 0,
             "complete_known_unchanged": operational_pass,
             "no_lower_paired_useful_total": candidate["all"]["useful"] >= arms["v14-medium"]["slices"]["all"]["useful"]}
    return {"packet_sha256": digest, "arms": arms, "paired": paired_statistics(packet, indexed["v14-medium"], indexed["v16"]),
            "prospective_gates": gates, "all_gates_pass": all(gates.values()), "provenance": provenance,
            "decision": "Go Deeper for separately gated integration" if all(gates.values()) else "Refine; no V16 integration or later-stage dispatch",
            "previous_gate": "Original reused-data Dahlia failure remains failed regardless of this prospective amendment."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("packet", "baseline-dir", "candidate-dir", "baseline-review", "candidate-review", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.packet, args.baseline_dir, args.candidate_dir, args.baseline_review, args.candidate_review)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"decision": result["decision"], "gates": result["prospective_gates"]}))


if __name__ == "__main__":
    main()
