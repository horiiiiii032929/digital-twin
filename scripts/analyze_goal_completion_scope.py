"""Compare preserved goal-scope arms; no runtime execution or external calls."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean


def compare(baseline: Path, candidate: Path) -> dict:
    manifests = [json.loads((p / "manifest.json").read_text()) for p in (baseline, candidate)]
    if [m["arm"] for m in manifests] != ["baseline", "candidate"]:
        raise ValueError("expected the baseline and candidate arms in that order")
    if manifests[0]["dataset"] != manifests[1]["dataset"]:
        raise ValueError("paired dataset configuration differs")
    sources = [m["source_sha256"] for m in manifests]
    if sources[0].keys() != sources[1].keys():
        raise ValueError("source inventories differ")
    changed = sorted(k for k in sources[0] if sources[0][k] != sources[1][k])
    if changed != ["src/digital_twin/student/autonomy_control.py", "src/digital_twin/student/service.py"]:
        raise ValueError(f"unexpected source differences: {changed}")
    scores = []
    for path in (baseline, candidate):
        rows = [json.loads(line) for line in (path / "scores.jsonl").read_text().splitlines()]
        indexed = {(r["condition"], r["case_id"]): r for r in rows}
        if len(indexed) != len(rows):
            raise ValueError("duplicate history identifier")
        scores.append(indexed)
    if scores[0].keys() != scores[1].keys():
        raise ValueError("paired history IDs differ")
    metrics = ("messages_delivered", "final_hidden_mastery", "wasted_rate", "follow_up_fraction")
    paired = []
    for key in sorted(scores[0]):
        before, after = scores[0][key], scores[1][key]
        paired.append({"condition": key[0], "case_id": key[1], "deltas": {
            metric: after[metric] - before[metric]
            if before[metric] is not None and after[metric] is not None else None
            for metric in metrics
        }})
    aggregate = {}
    for condition in sorted({row["condition"] for row in paired}):
        aggregate[condition] = {}
        for metric in metrics:
            values = [r["deltas"][metric] for r in paired if r["condition"] == condition and r["deltas"][metric] is not None]
            aggregate[condition][metric] = {
                "n_pairs": len(values), "mean_difference": mean(values) if values else None,
                "decreased": sum(v < 0 for v in values), "unchanged": sum(v == 0 for v in values),
                "increased": sum(v > 0 for v in values),
                "minimum": min(values) if values else None, "maximum": max(values) if values else None,
            }
    return {
        "run_id": "goal-completion-scope-development-001", "changed_sources": changed,
        "input_artifacts": {str(p / name): sha256((p / name).read_bytes()).hexdigest()
                            for p in (baseline, candidate)
                            for name in ("manifest.json", "scores.jsonl", "responses.jsonl", "goal-audit.json", "decision.json", "source.zip")},
        "paired_candidate_minus_baseline": aggregate, "paired_histories": paired,
        "arms": [json.loads((p / "decision.json").read_text()) for p in (baseline, candidate)],
        "interpretation": "Descriptive matched-seed development comparison. Actions change subsequent simulated learner responses; the closed-loop transcripts are not fixed across arms. Histories share six concept cards and persona/family templates. No population confidence interval or human learning claim is made for the between-arm changes.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.baseline, args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["paired_candidate_minus_baseline"], indent=2))


if __name__ == "__main__":
    main()
