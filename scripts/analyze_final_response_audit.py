"""Offline analysis of complete final-response audit banks; never dispatches providers.

From repository cwd: .venv/bin/python -m scripts.analyze_final_response_audit
--run-dir RUN --review REVIEW --support-labels LABELS --output NEW_JSON.
Manual review binds packet_sha256/cases_sha256 and exact cases/id/C0/C1/C2 judgments.
Support annotations: per-bank {packet_sha256,cases:[{id,factual_support_defect:bool|null,reason}]}
or {banks:{fresh:...,exposed:...}}. Policy critical is not factual-support defect.
"""

from __future__ import annotations
import argparse
import collections
import hashlib
import json
import random
import statistics
import zipfile
from pathlib import Path

ARMS = ("C0", "C1", "C2")
SEED = 8801
REPEATS = 10000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def index(rows, ids, name):
    require(isinstance(rows, list), name + " requires cases list")
    require(
        len(rows) == len(ids)
        and len({r["id"] for r in rows}) == len(rows)
        and {r["id"] for r in rows} == set(ids),
        name + " exact IDs required",
    )
    return {r["id"]: r for r in rows}


def rate(a, b):
    return a / b if b else None


def quantile(xs, p):
    ys = sorted(xs)
    v = (len(ys) - 1) * p
    i = int(v)
    return ys[i] + (ys[min(i + 1, len(ys) - 1)] - ys[i]) * (v - i)


def describe(xs):
    return {
        "n": len(xs),
        "mean": statistics.mean(xs) if xs else None,
        "median": statistics.median(xs) if xs else None,
        "p95": quantile(xs, 0.95) if xs else None,
        "sum": sum(xs),
    }


def bootstrap(rows, *, arm="C2", baseline="C0", seed=SEED, repeats=REPEATS):
    """Resample complete scenario pairs within family; never sample units/arms separately."""
    families = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        families[r["family"]][r["pair_id"]].append(r)
    require(
        all(len(g) == 2 for f in families.values() for g in f.values()),
        "bootstrap requires two records per scenario pair",
    )
    clusters = {
        f: [
            [int(r[arm]["useful"]) - int(r[baseline]["useful"]) for r in g]
            for _, g in sorted(gs.items())
        ]
        for f, gs in sorted(families.items())
    }
    rng = random.Random(seed)
    samples = []
    n = len(rows)
    for _ in range(repeats):
        total = 0
        for groups in clusters.values():
            for _ in groups:
                total += sum(rng.choice(groups))
        samples.append(total / n)
    return {
        "arm": arm,
        "baseline": baseline,
        "difference": sum(
            int(r[arm]["useful"]) - int(r[baseline]["useful"]) for r in rows
        )
        / n,
        "ci95": [quantile(samples, 0.025), quantile(samples, 0.975)],
        "seed": seed,
        "repeats": repeats,
        "scenario_pairs": sum(len(v) for v in clusters.values()),
        "scope": "Stratified paired synthetic-scenario bootstrap; not independent students or population generalization.",
    }


def validate_judgment(j):
    require(
        all(type(j.get(k)) is bool for k in ["useful", "critical", "uncertain"]),
        "judgment booleans required",
    )
    require(
        isinstance(j.get("reason"), str) and bool(j["reason"].strip()),
        "judgment reason required",
    )
    require(
        not j["useful"] or not (j["critical"] or j["uncertain"]),
        "critical/uncertain cannot be useful",
    )


def aggregate(rows, arm):
    n = len(rows)
    return {
        "n": n,
        "useful": sum(r[arm]["useful"] for r in rows),
        "critical": sum(r[arm]["critical"] for r in rows),
        "uncertain": sum(r[arm]["uncertain"] for r in rows),
        "useful_rate": rate(sum(r[arm]["useful"] for r in rows), n),
    }


def execution_slices(rows, raw, records):
    """Separate provider-reached work from completed semantic decisions and blocked work."""
    ids = {row["id"] for row in rows}
    reached = set()
    reached_by_arm = {arm: set() for arm in ("C1", "C2")}
    for values in records.values():
        for record in values:
            parts = record.get("case", "").rsplit("/", 3)
            require(
                len(parts) == 4 and parts[0] in ids and parts[1] in reached_by_arm,
                "provider record must identify an input and arm",
            )
            reached.add(parts[0])
            reached_by_arm[parts[1]].add(parts[0])
    reached_rows = [row for row in rows if row["id"] in reached]
    completed_reasons = {
        "audit_pass",
        "audit_rejected",
        "reaudit_pass",
        "repair_rejected",
        "unchanged_repair",
    }
    arms = {}
    for arm in ("C1", "C2"):
        completed = [
            row
            for row in rows
            if row["id"] in reached_by_arm[arm]
            and raw[row["id"]][arm].get("reason") in completed_reasons
        ]
        arms[arm] = {
            "provider_reached_inputs": len(reached_by_arm[arm]),
            "completed_semantic_decisions": len(completed),
            "metrics_on_completed_decisions": aggregate(completed, arm),
            "baseline_on_same_completed_inputs": aggregate(completed, "C0"),
            "useful_baseline_lost_on_reached": sum(
                row["C0"]["useful"] and not row[arm]["useful"] for row in reached_rows
            ),
            "useful_baseline_lost_on_completed_decisions": sum(
                row["C0"]["useful"] and not row[arm]["useful"] for row in completed
            ),
        }
    return {
        "reached_input_ids": sorted(reached),
        "reached_inputs": len(reached),
        "not_reached_inputs": len(rows) - len(reached),
        "metrics_on_reached_union": {arm: aggregate(reached_rows, arm) for arm in ARMS},
        "arms": arms,
        "definition": "Reached is the union of input IDs in actual provider records, including failed billed calls. Completed semantic decisions exclude blocked and contract/provider failures, but include semantic rejection, unchanged repair and failed second audit. These order-selected subsets are descriptive, not random samples or replacements for planned denominators.",
    }


def support_detection(rows, raw, labels):
    counts = collections.Counter()
    unknown = collections.Counter()
    operational = 0
    for r in rows:
        arm = raw[r["id"]]["C1"]
        pred = None
        # Only a completed well-formed semantic support audit defines a detection.
        if arm.get("reason") == "audit_pass":
            pred = False
        elif arm.get("reason") == "audit_rejected":
            pred = True
        else:
            operational += 1
        label = labels[r["id"]]["factual_support_defect"]
        if label is None:
            unknown[
                "positive"
                if pred is True
                else "negative"
                if pred is False
                else "operational"
            ] += 1
        elif pred is None:
            counts[
                "known_operational_defect" if label else "known_operational_clean"
            ] += 1
        else:
            counts[
                "tp" if label and pred else "fn" if label else "fp" if pred else "tn"
            ] += 1
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    known_defects = tp + fn + counts["known_operational_defect"]
    return {
        "known_confusion": dict(counts),
        "unknown_labels": sum(unknown.values()),
        "unknown_by_prediction": dict(unknown),
        "operational_nondecisions": operational,
        "precision_known_decisions": rate(tp, tp + fp),
        "recall_known_decisions": rate(tp, tp + fn),
        "recall_known_all_defects": rate(tp, known_defects),
        "conservative_precision_unknown_positives_as_clean": rate(
            tp, tp + fp + unknown["positive"]
        ),
        "conservative_recall_unknown_negative_or_operational_as_defects": rate(
            tp, known_defects + unknown["negative"] + unknown["operational"]
        ),
        "scope": "C1 semantic quarantine, including support uncertainty, is positive detection. Contract/transport/blocked quarantine is a nondecision, never a factual true positive. Unknown truth is never silently clean; policy-only criticals remain distinct.",
    }


def audit_entries(content):
    try:
        value = json.loads(content)
        return (
            value.get("entries", [])
            if isinstance(value, dict) and isinstance(value.get("entries", []), list)
            else []
        )
    except (ValueError, TypeError):
        return []


def analyze(run_dir, review_path, label_path):
    run = Path(run_dir)
    pb = (run / "packet.json").read_bytes()
    cb = (run / "cases.jsonl").read_bytes()
    packet = json.loads(pb)
    manifest = read(run / "manifest.json")
    summary = read(run / "summary.json")
    review = read(review_path)
    ann = read(label_path)
    bank = manifest["bank"]
    n = 128 if bank == "fresh" else 112
    require(
        bank in ["fresh", "exposed"] and packet.get("bank") == bank, "bank mismatch"
    )
    contexts = packet["contexts"]
    ids = [c["id"] for c in contexts]
    require(len(ids) == n and len(set(ids)) == n, "complete fixed bank required")
    require(
        manifest["packet_sha256"] == sha(pb)
        and manifest["planned_inputs"] == n
        and summary["planned_inputs"] == n,
        "packet manifest mismatch",
    )
    require(summary["cases_sha256"] == sha(cb), "cases digest mismatch")
    require(
        review.get("packet_sha256") == sha(pb)
        and review.get("cases_sha256") == sha(cb),
        "manual review must bind packet and cases hashes",
    )
    require(
        sha((run / "source-snapshot.zip").read_bytes())
        == manifest["source_snapshot_sha256"],
        "snapshot digest mismatch",
    )
    with zipfile.ZipFile(run / "source-snapshot.zip") as z:
        require(
            set(z.namelist()) == set(manifest["source_hashes_start"]),
            "source snapshot file coverage mismatch",
        )
        for name, digest in manifest["source_hashes_start"].items():
            require(
                sha(z.read(name)) == digest, "source snapshot content mismatch " + name
            )
    raw = index(
        [json.loads(s) for s in cb.decode().splitlines() if s.strip()], ids, "raw"
    )
    summ = index(summary["cases"], ids, "summary")
    judgments = index(review["cases"], ids, "manual review")
    require(raw == summ, "summary/raw case mismatch")
    if "banks" in ann:
        ann = ann["banks"][bank]
    require(ann["packet_sha256"] == sha(pb), "support labels packet mismatch")
    labels = index(ann["cases"], ids, "support labels")
    for lab in labels.values():
        require(
            lab.get("factual_support_defect") is None
            or type(lab["factual_support_defect"]) is bool,
            "support labels bool/null required",
        )
    # Validate exact baseline and every delivered proposal using the actual local composer.
    from scripts.run_factual_revision_controls import (
        public_revision_input,
        render_control_proposal,
    )
    from src.digital_twin.generation.typed_instruction import TypedInstructionProposal
    from src.digital_twin.generation.final_response_audit import (
        FinalAuditDecision,
        _snapshot,
        _validate_decision,
    )

    rows = []
    integration = []
    for c in contexts:
        ident = c["id"]
        r = raw[ident]
        j = judgments[ident]
        require(r["public_input"] == c["public"], "raw public input mismatch " + ident)
        payload, draft = public_revision_input(c)
        base = render_control_proposal(draft, c["public"])
        require(base["completed"], "baseline composer failure")
        require(
            json.loads(r["C0"]["proposal_json"]) == c["public"]["draft"]
            and r["C0"]["delivered_text"] == base["answer"]["content"],
            "raw baseline mismatch " + ident,
        )
        if "frozen_baseline_render" in c:
            require(
                c["frozen_baseline_render"] == r["C0"]["delivered_text"],
                "exposed baseline mismatch",
            )
        row = {
            "id": ident,
            "pair_id": c["pair_id"],
            "family": c["family"],
            "draft_adequate": c["gold"]["draft_adequate"],
        }
        for arm in ARMS:
            validate_judgment(j[arm])
            row[arm] = j[arm]
            if arm == "C0":
                continue
            a = r[arm]
            events = a.get("events", [])
            require(a.get("calls") == len(events), "arm call/event mismatch")
            require(len(events) <= (1 if arm == "C1" else 3), "arm bound exceeded")
            phases = [e.get("phase") for e in events]
            expected = (
                ["support_audit"]
                if arm == "C1"
                else ["quality_audit", "repair", "post_repair_audit"]
            )
            require(phases == expected[: len(phases)], "invalid role sequence")
            if a["outcome"] in ["passed", "repaired"]:
                require(
                    a.get("proposal_json") is not None and bool(events),
                    "delivered missing proposal/audit",
                )
                proposed = TypedInstructionProposal.model_validate_json(
                    a["proposal_json"]
                )
                render = render_control_proposal(proposed, c["public"])
                require(
                    render["completed"]
                    and render["answer"]["content"] == a["delivered_text"],
                    "delivered render mismatch",
                )
                event = events[-1]
                d = json.loads(event["response"]["content"])
                require(
                    d["proposal_sha256"] == sha(a["proposal_json"].encode())
                    and d["rendered_sha256"] == sha(a["delivered_text"].encode()),
                    "final response audit hash mismatch",
                )
                snapshot = _snapshot(
                    a["proposal_json"],
                    payload,
                    lambda p: render_control_proposal(p, c["public"])["answer"][
                        "content"
                    ],
                )
                require(
                    _validate_decision(
                        FinalAuditDecision.model_validate(d),
                        snapshot,
                        "support" if arm == "C1" else "quality",
                    ),
                    "delivered final audit not passing",
                )
                if a["outcome"] == "passed":
                    require(
                        a["proposal_json"] == r["C0"]["proposal_json"],
                        "pass changed baseline proposal",
                    )
                if a["outcome"] == "repaired":
                    require(
                        arm == "C2"
                        and len(events) == 3
                        and proposed.model_dump() != draft.model_dump(),
                        "unchecked or unchanged repair delivery",
                    )
            else:
                require(a["outcome"] in ["quarantined", "blocked"], "unknown outcome")
                require(
                    a.get("proposal_json") is None and not j[arm]["useful"],
                    "quarantine cannot count as useful",
                )
            if a.get("reason") == "contract_or_provider_failure":
                integration.append({"id": ident, "arm": arm})
        rows.append(row)
    pairs = collections.defaultdict(list)
    for row in rows:
        pairs[row["pair_id"]].append(row)
    require(
        len(pairs) == n // 2
        and all(
            len(g) == 2 and len({r["family"] for r in g}) == 1 for g in pairs.values()
        ),
        "scenario pair structure mismatch",
    )
    if bank == "fresh":
        require(
            all(
                sorted(r["draft_adequate"] for r in g) == [False, True]
                for g in pairs.values()
            ),
            "fresh adequate/flawed pairing mismatch",
        )
    require(
        manifest["maximum_calls"] == 4 * n
        and abs(manifest["maximum_reserved_usd"] - 0.64 * n) < 1e-8,
        "manifest bounds mismatch",
    )
    require(
        manifest["role_maximum_calls"] == {"audit": 3 * n, "repair": n}
        and manifest["per_arm_maximum_calls"] == {"C1": 1, "C2": 3},
        "role bounds mismatch",
    )
    require(1 <= manifest["concurrency"] <= 4, "concurrency bound mismatch")
    require(
        abs(summary["reserved_usd"] - 0.16 * summary["admitted_calls"]) < 1e-8,
        "reservation accounting mismatch",
    )
    require(
        summary["admitted_calls"] <= 4 * n
        and summary["provider_attempts"] <= summary["admitted_calls"]
        and summary["reserved_usd"] <= 0.64 * n + 1e-8,
        "run budget exceeded",
    )
    metrics = {a: aggregate(rows, a) for a in ARMS}
    families = {
        f: {a: aggregate([r for r in rows if r["family"] == f], a) for a in ARMS}
        for f in sorted({r["family"] for r in rows})
    }
    operational = {}
    for arm in ["C1", "C2"]:
        arms = [raw[r["id"]][arm] for r in rows]
        events = [e for a in arms for e in a.get("events", [])]
        operational[arm] = {
            "outcomes": dict(collections.Counter(a["outcome"] for a in arms)),
            "reasons": dict(collections.Counter(a["reason"] for a in arms)),
            "helper_events_including_blocked_attempts": len(events),
            "repair_invocations": sum(e["phase"] == "repair" for e in events),
            "verified_useful_repairs": sum(
                raw[r["id"]][arm]["outcome"] == "repaired" and r[arm]["useful"]
                for r in rows
            ),
            "failed_second_audits": sum(a["reason"] == "repair_rejected" for a in arms),
            "useful_baseline_lost": sum(
                r["C0"]["useful"] and not r[arm]["useful"] for r in rows
            ),
            "quarantine_on_packet_adequate": sum(
                r["draft_adequate"]
                and raw[r["id"]][arm]["outcome"] in ["quarantined", "blocked"]
                for r in rows
            ),
        }
    records = summary["provider_records_by_role"]
    for role, rs in records.items():
        require(
            len(rs) <= manifest["role_maximum_calls"][role], "role call bound exceeded"
        )
        ledger = (
            [
                json.loads(line)
                for line in (run / f"provider-{role}.jsonl").read_text().splitlines()
            ]
            if (run / f"provider-{role}.jsonl").exists()
            else []
        )
        require(
            [r for r in ledger if r["status"] in ["completed", "failed"]] == rs,
            "provider summary/ledger mismatch",
        )
    require(
        sum(len(rs) for rs in records.values()) == summary["provider_attempts"],
        "provider attempt total mismatch",
    )
    require(
        sum(
            (r.get("usage") or {}).get("approximate_cost_usd") is None
            for rs in records.values()
            for r in rs
        )
        == summary["unknown_cost_calls"],
        "unknown usage denominator mismatch",
    )
    cost_latency = {
        role: {
            "attempt_records": len(rs),
            "unknown_cost_calls": sum(
                (r.get("usage") or {}).get("approximate_cost_usd") is None for r in rs
            ),
            "known_cost_usd": sum(
                (r.get("usage") or {}).get("approximate_cost_usd") or 0 for r in rs
            ),
            "latency_ms": describe(
                [r["latency_ms"] for r in rs if r.get("latency_ms") is not None]
            ),
        }
        for role, rs in records.items()
    }
    for arm in ["C1", "C2"]:
        selected = [
            r
            for rs in records.values()
            for r in rs
            if "/" + arm + "/" in r.get("case", "")
        ]
        operational[arm]["known_cost_usd"] = sum(
            (r.get("usage") or {}).get("approximate_cost_usd") or 0 for r in selected
        )
        operational[arm]["unknown_cost_calls"] = sum(
            (r.get("usage") or {}).get("approximate_cost_usd") is None for r in selected
        )
        operational[arm]["end_to_end_arm_seconds"] = describe(
            [
                case[arm]["elapsed_seconds"]
                for case in raw.values()
                if case[arm].get("elapsed_seconds") is not None
            ]
        )
        operational[arm]["provider_latency_ms"] = describe(
            [r["latency_ms"] for r in selected if r.get("latency_ms") is not None]
        )
        operational[arm]["per_unit_audit_verdicts_not_ground_truth"] = dict(
            collections.Counter(
                e["verdict"]
                for row in raw.values()
                for event in row[arm].get("events", [])
                if event.get("phase") != "repair" and "response" in event
                for e in audit_entries(event["response"]["content"])
                if isinstance(e, dict)
                and "verdict" in e
                and e.get("entry_id") != "rendered"
            )
        )
    gates = None
    if bank == "fresh":
        adequate = [r for r in rows if r["draft_adequate"]]
        flawed = [r for r in rows if not r["draft_adequate"]]
        require(
            len(adequate) == len(flawed) == 64
            and len(families) == 4
            and all(v["C0"]["n"] == 32 for v in families.values()),
            "fresh composition mismatch",
        )
        gates = {
            "adequate_at_least61": aggregate(adequate, "C2")["useful"] >= 61,
            "flawed_at_least61": aggregate(flawed, "C2")["useful"] >= 61,
            "each_family_at_least30": all(
                v["C2"]["useful"] >= 30 for v in families.values()
            ),
            "zero_C2_criticals": metrics["C2"]["critical"] == 0,
            "C2_useful_not_below_C0": metrics["C2"]["useful"]
            >= metrics["C0"]["useful"],
            "C2_critical_not_above_C0": metrics["C2"]["critical"]
            <= metrics["C0"]["critical"],
            "known_usage": summary["unknown_cost_calls"] == 0,
            "unchanged_sources": summary["source_files_unchanged"],
            "no_contract_or_provider_failure": not integration
            and not summary["provider_stopped"],
            "all_planned_outputs": all(
                raw[r["id"]]["C2"]["outcome"] != "blocked" for r in rows
            ),
        }
        metrics["C2_adequate"] = aggregate(adequate, "C2")
        metrics["C2_flawed"] = aggregate(flawed, "C2")
    intervals = [bootstrap(rows, arm=a) for a in ["C1", "C2"]] + [
        bootstrap(rows, arm="C2", baseline="C1")
    ]
    for interval in intervals:
        interval["estimand"] = "planned execution coverage including blocked inputs"
        interval["run_stopped"] = summary["provider_stopped"]
        if summary["provider_stopped"]:
            interval["scope"] = (
                "Stratified scenario-pair resampling of this stopped execution, including blocked inputs. Describes combined operational and semantic coverage; not completed model-quality evaluation or population inference."
            )
    return {
        "bank": bank,
        "packet_sha256": sha(pb),
        "cases_sha256": sha(cb),
        "analysis_code_sha256": sha(Path(__file__).read_bytes()),
        "review_sha256": sha(Path(review_path).read_bytes()),
        "support_labels_sha256": sha(Path(label_path).read_bytes()),
        "metrics": metrics,
        "families": families,
        "operational": operational,
        "execution_slices": execution_slices(rows, raw, records),
        "cost_latency_by_role": cost_latency,
        "end_to_end_wall_seconds": summary["wall_seconds"],
        "support_detection": support_detection(rows, raw, labels),
        "paired_bootstrap": intervals,
        "gates": gates,
        "decision": "diagnostic_only_no_promotion"
        if bank == "exposed"
        else "go_deeper_not_release"
        if all(gates.values())
        else "failed_fresh_progression",
        "limitations": [
            "Assistant-reviewed exposed synthetic scenarios, not human validation.",
            "Per-unit verdicts are model assessments, not independent per-unit truth.",
            "Uncertainty and all operational failures remain in denominators.",
            "C2 jointly tests verification and issue-guided repair, not a pure gate effect.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ["run-dir", "review", "support-labels", "output"]:
        p.add_argument("--" + k, required=True, type=Path)
    a = p.parse_args()
    require(not a.output.exists(), "refuse output overwrite")
    result = analyze(a.run_dir, a.review, a.support_labels)
    with a.output.open("x") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
