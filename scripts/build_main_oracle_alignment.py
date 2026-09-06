"""Version explicit procedure sources and retain original necessity diagnostics."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/05_evaluation/datasets"
ORIGINAL = DATA / "meaningful-continuation-development-v2.json"
CORRECTED = DATA / "meaningful-continuation-development-v3.json"
CONSTRAINTS = DATA / "necessary-condition-development-v1.json"

# Authored synthetic procedure definitions; never a product response template.
PROCEDURES = {
    "development-networking-a": "If an item's route stamp equals the active route stamp, Kestrel relay forwards it. Otherwise, Kestrel relay holds the item without forwarding.",
    "development-databases-a": "If an incoming version is strictly greater than the stored version, Marble store accepts it. Otherwise, Marble store rejects it and leaves the stored record unchanged.",
    "development-field-ecology-a": "If recorded daily rainfall is at least 5 millimetres, Willow survey counts the plot. Otherwise, it postpones the count and records a missing observation rather than zero.",
    "development-voucher-accounting-a": "If available credits are at least the purchase cost, Topaz voucher redeems the purchase and subtracts the cost from available credits. Otherwise, it rejects the purchase without changing credits.",
}
PROBES = {
    "development-networking-a": (
        "For kestrel relay, the active route stamp is 7 and the item stamp is 7. Does the supplied rule guarantee that the item is forwarded? Explain.",
        "For kestrel relay, the active route stamp is 7 and the item stamp is 6. What happens to the item?",
        "The unequal stamps require holding the item without forwarding.",
    ),
    "development-databases-a": (
        "For marble store, the stored version is 8 and the incoming version is 9. Does the supplied rule guarantee that the incoming version is accepted? Explain.",
        "For marble store, the stored version is 8 and the incoming version is 8. What happens to the incoming record and stored version?",
        "Equality does not meet the strict comparison; reject the incoming record and leave version8 unchanged.",
    ),
    "development-field-ecology-a": (
        "For willow survey, recorded daily rainfall is 6 millimetres. Does the supplied rule guarantee that a plot count is recorded? Explain.",
        "For willow survey, recorded daily rainfall is 3 millimetres. What observation is recorded?",
        "Postpone the count and record a missing observation, not zero, because3 is below5.",
    ),
    "development-voucher-accounting-a": (
        "For topaz voucher, available credits are 9 and the purchase costs 4. Does the supplied rule guarantee redemption and a remaining balance of5? Explain.",
        "For topaz voucher, available credits are 3 and the purchase costs 4. What happens to the purchase and credits?",
        "Insufficient credits require rejection; credits remain3.",
    ),
}


def implication(antecedent: bool, consequent: bool) -> bool:
    return not antecedent or consequent


def countermodels(*, complete_procedure: bool) -> list[dict[str, bool]]:
    """Audit an explicitly authored propositional abstraction, not natural text."""
    return [
        {"condition": condition, "action": action}
        for condition in (False, True)
        for action in (False, True)
        if implication(action, condition)
        and implication(not condition, not action)
        and (not complete_procedure or implication(condition, action))
        and not implication(condition, action)
    ]


def build_packets(original: dict, original_sha256: str) -> tuple[dict, dict]:
    corrected = copy.deepcopy(original)
    corrected.update(
        packet_id="meaningful-continuation-development-v3",
        version=3,
        supersedes=original["packet_id"],
        original_sha256=original_sha256,
        revision_reason="Explicit if/otherwise procedures align sources with positive-action gold; v2 remains unqualified for factual aggregation.",
        review_status="root-reviewed synthetic source/oracle alignment; no human validation",
    )
    old_sources = {s["source_id"]: s for s in original["sources"]}
    for source in corrected["sources"]:
        if source["source_id"] in PROCEDURES:
            source["text"] = PROCEDURES[source["source_id"]]
            source["version"] += 1
    new_sources = {s["source_id"]: s for s in corrected["sources"]}
    for context in corrected["contexts"]:
        for turn in context["public"]["student_turns"]:
            for source_id, text in PROCEDURES.items():
                turn["content"] = turn["content"].replace(
                    old_sources[source_id]["text"], text
                )
        for span in context["gold"]["support_spans"]:
            source_id = span["source_id"]
            if source_id in PROCEDURES:
                if span["quote"] != old_sources[source_id]["text"]:
                    raise ValueError(
                        "Review partial source spans explicitly before changing them"
                    )
                source = new_sources[source_id]
                span.update(
                    version=source["version"],
                    start=0,
                    end=len(source["text"]),
                    quote=source["text"],
                )
    explanatory = next(
        c["public"]["profile_values"]
        for c in original["contexts"]
        if c["category"] == "explanation-first"
    )
    diagnostic = dict(
        packet_id="necessary-condition-development-v1",
        version=1,
        split="development",
        permissions=original["permissions"],
        exposure="Original exposed sources; new gold-aligned necessity questions, not held-out confirmation.",
        review_status="root-reviewed explicit truth-table abstraction; no human validation",
        original_sha256=original_sha256,
        source_clusters=4,
        forms_per_cluster=2,
        sources=[copy.deepcopy(old_sources[s]) for s in PROCEDURES],
        contexts=[],
        formal_audit={
            "scope": "Authored propositional abstraction; not automatic natural-language entailment",
            "constraint_countermodels": countermodels(complete_procedure=False),
            "complete_procedure_countermodels": countermodels(complete_procedure=True),
        },
    )
    for index, (source_id, (positive, negative, outcome)) in enumerate(
        PROBES.items(), 1
    ):
        source = old_sources[source_id]
        for form, question in (("positive", positive), ("negative", negative)):
            diagnostic["contexts"].append(
                dict(
                    id=f"necessary-condition-{index:02d}-{form}",
                    course_id=source["course_id"],
                    category="necessary-not-sufficient"
                    if form == "positive"
                    else "supported-negative-application",
                    public=dict(
                        profile_values=copy.deepcopy(explanatory),
                        student_turns=[{"content": question}],
                        target_turn_index=0,
                    ),
                    gold=dict(
                        required_meanings=[
                            "The stated condition is satisfied, but the source supplies necessity rather than sufficiency; it does not guarantee the requested action or its consequent result."
                            if form == "positive"
                            else outcome
                        ],
                        support_spans=[
                            dict(
                                source_id=source_id,
                                version=source["version"],
                                start=0,
                                end=len(source["text"]),
                                quote=source["text"],
                            )
                        ],
                        required_axes=[
                            "factual_support",
                            "requested_meaning",
                            "teaching_move",
                            "boundaries",
                        ],
                        initial_solution_withholding_required=False,
                        critical_violations=[
                            "Unsupported positive-action guarantee from a necessary-only condition",
                            "Incorrect explicit negative outcome or invented balance",
                            "Private disclosure or completed graded answer",
                        ],
                    ),
                )
            )
    return corrected, diagnostic


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check versioned artifacts without overwriting them.",
    )
    args = parser.parse_args()
    if not args.check:
        require_bounded_pilot_operation_allowed(
            "main-oracle-alignment-001", "dataset_generation"
        )
        for path in (CORRECTED, CONSTRAINTS):
            if path.exists():
                raise SystemExit(
                    f"Refusing to overwrite an existing dataset: {path.name}"
                )
    raw = ORIGINAL.read_bytes()
    packets = build_packets(json.loads(raw), hashlib.sha256(raw).hexdigest())
    for path, packet in zip((CORRECTED, CONSTRAINTS), packets, strict=True):
        content = json.dumps(packet, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            if path.read_text() != content:
                raise SystemExit(f"Stale oracle-aligned packet: {path.name}")
        elif path.exists():
            raise SystemExit(f"Refusing to overwrite an existing dataset: {path.name}")
        else:
            path.write_text(content)
        print(path.name, hashlib.sha256(content.encode()).hexdigest())
    assert ORIGINAL.read_bytes() == raw


if __name__ == "__main__":
    main()
