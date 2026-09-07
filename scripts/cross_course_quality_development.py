"""Independent extractive G7 development instrument, not a semantic model judge.

Decision: can an unchanged or candidate tutor satisfy explicit question-specific
requirements across four synthetic mini-courses? Freeze public inputs separately
from authored gold. Compare the same inputs; retain failures and expose scorer
blind spots. No model calls, product scorer imports, or human-review claim.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "research/05_evaluation/datasets/cross-course-quality-development-v1.json"


def public_case(packet: dict, case_id: str) -> dict:
    case = next(c for c in packet["cases"] if c["public"]["case_id"] == case_id)
    result = dict(case["public"])
    result["sources"] = [dict(s) for s in packet["sources"] if s["course_id"] == result["course_id"]]
    return result


def validate_packet(packet: dict) -> None:
    sources = {s["source_id"]: s for s in packet["sources"]}
    if len(sources) != len(packet["sources"]):
        raise ValueError("duplicate source")
    ids = [c["public"]["case_id"] for c in packet["cases"]]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate case")
    for case in packet["cases"]:
        for span in case["gold"]["requirements"] + case["gold"]["forbidden_solution_spans"]:
            source = sources[span["source_id"]]
            if source["course_id"] != case["public"]["course_id"]:
                raise ValueError("gold crosses course")
            if source["text"][span["start"]:span["end"]] != span["quote"] or not span["quote"]:
                raise ValueError("invalid source span")


def score_case(packet: dict, case_id: str, response: dict) -> dict:
    """Strict partial oracle: exact requirements and lineage, never semantic proof."""
    case = next(c for c in packet["cases"] if c["public"]["case_id"] == case_id)
    gold, public = case["gold"], public_case(packet, case_id)
    sources = {s["source_id"]: s for s in public["sources"]}
    raw_text = response.get("text", "")
    text = raw_text if isinstance(raw_text, str) else ""
    raw_citations = response.get("citations", [])
    citations = raw_citations if isinstance(raw_citations, list) else []
    violations = []
    if not isinstance(raw_citations, list):
        violations.append("citation-schema")
    if response.get("action") not in gold["allowed_actions"]:
        violations.append("action")
    valid_spans = set()
    for citation in citations:
        if not isinstance(citation, dict):
            violations.append("citation-schema")
            continue
        source = sources.get(citation.get("source_id"))
        start, end = citation.get("start"), citation.get("end")
        if (source is None or type(start) is not int or type(end) is not int
                or start < 0 or end <= start or end > len(source["text"])
                or citation.get("version") != source["version"]
                or source["text"][start:end] != citation.get("quote")):
            violations.append("citation-lineage")
        else:
            valid_spans.add((source["source_id"], start, end))
    for requirement in gold["requirements"]:
        if requirement["quote"] not in text:
            violations.append("required-content-missing")
        if (requirement["source_id"], requirement["start"], requirement["end"]) not in valid_spans:
            violations.append("required-citation-missing")
    if any(span["quote"].casefold() in text.casefold() for span in gold["forbidden_solution_spans"]):
        violations.append("premature-solution")
    if gold["no_citations"] and citations:
        violations.append("boundary-citations")
    if not isinstance(text, str) or not text.strip():
        violations.append("empty-response")
    return {"case_id": case_id, "mechanical_pass": not violations,
            "violations": sorted(set(violations)),
            "semantic_review": "required-not-performed",
            "limitations": "Exact spans cannot detect arbitrary unsupported extra prose or paraphrased solution leakage."}


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0 or successes < 0 or successes > n:
        raise ValueError("invalid binomial counts")
    p = successes / n
    denominator = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denominator
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return max(0.0, centre-half), min(1.0, centre+half)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-output", type=Path)
    args = parser.parse_args()
    packet = json.loads(PACKET.read_text())
    validate_packet(packet)
    if args.public_output:
        with args.public_output.open("x") as output:
            for case in packet["cases"]:
                output.write(json.dumps(public_case(packet, case["public"]["case_id"]), sort_keys=True) + "\n")
    print(json.dumps({"packet_id": packet["packet_id"], "cases": len(packet["cases"]),
                      "courses": len({s["course_id"] for s in packet["sources"]}),
                      "review": packet["review_status"]}))


if __name__ == "__main__":
    main()
