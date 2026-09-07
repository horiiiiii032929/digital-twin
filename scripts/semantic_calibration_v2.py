"""Validate/export synthetic advisory controls; never expose private gold to a judge."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path

from scripts.cross_course_quality_development import ROOT

PACKET = (
    ROOT / "research/05_evaluation/datasets/completion-semantic-calibration-v2.json"
)


def public_payload(row: dict) -> dict:
    """Allowlisted judge input, excluding even outer control identifiers."""
    return copy.deepcopy(
        {
            k: row["payload"][k]
            for k in ("question", "profile", "history", "sources", "response")
        }
    )


def validate_packet(packet: dict) -> None:
    rows = packet["cases"]
    if len(rows) != 32 or len({r["id"] for r in rows}) != 32:
        raise ValueError("exactly32 unique controls required")
    if Counter(r["course_id"] for r in rows) != dict.fromkeys(
        ["scheduler", "ledger", "ecology", "protocol"], 8
    ):
        raise ValueError("four course coverage required")
    for row in rows:
        payload = public_payload(row)
        if set(row["payload"]) != set(payload):
            raise ValueError("unexpected payload field; possible gold leakage")
        sources = {s["source_id"]: s for s in payload["sources"]}
        if any(s["course_id"] != row["course_id"] for s in sources.values()):
            raise ValueError("cross-course source")
        for span in row["gold"]["support_spans"] + payload["response"]["citations"]:
            source = sources[span["source_id"]]
            if source["text"][span["start"] : span["end"]] != span["quote"]:
                raise ValueError("invalid source span")
        positive = row["gold"]["overall"] == "acceptable"
        for citation in payload["response"]["citations"]:
            version_ok = (
                citation["version"] == sources[citation["source_id"]]["version"]
            )
            if positive and not version_ok:
                raise ValueError("positive citation version invalid")
            if row["control_kind"] == "wrong-citation-version" and version_ok:
                raise ValueError("intentional citation defect missing")
        if not payload["profile"].get("current_turn_requirements"):
            raise ValueError("missing explicit turn profile")
        if positive and row["gold"]["defect_axis"] is not None:
            raise ValueError("inconsistent positive gold")
        if not positive and row["gold"]["axes"].get(row["gold"]["defect_axis"]) != [
            "defective"
        ]:
            raise ValueError("missing mandatory defect axis")
    for course in {r["course_id"] for r in rows}:
        subset = [r for r in rows if r["course_id"] == course]
        if (
            len({r["control_kind"] for r in subset}) != 8
            or sum(r["gold"]["overall"] == "acceptable" for r in subset) != 4
        ):
            raise ValueError("per-course control balance invalid")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-output", type=Path)
    args = parser.parse_args()
    p = json.loads(PACKET.read_text())
    validate_packet(p)
    if args.public_output:
        with args.public_output.open("x") as f:
            for row in p["cases"]:
                f.write(json.dumps(public_payload(row)) + "\n")
    print(
        json.dumps(
            {
                "packet_id": p["packet_id"],
                "cases": 32,
                "validation": "passed",
                "human_review": False,
            }
        )
    )


if __name__ == "__main__":
    main()
