"""Fresh network-free confirmation of multi-concept learner assessment.

This successor does not reuse extension 014's concepts or seeds.  It drives the
real T1-v2 product through the closed-loop learner adapter for 30 virtual days
and records whether a turn-level assessment is confined to its unambiguous
primary concept.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from scripts.run_governed_full_autonomy_v2_1_hidden_state_learner_014 import (
    DEFAULT_SEEDS as HISTORICAL_SEEDS,
    run_program,
)
from src.digital_twin.evaluation.learner_simulator import PERSONAS, SimulatorFamily
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "governed-full-autonomy-v2-1-multi-concept-confirmation-025"
FIXTURE_ID = "multi-concept-confirmation-025"
SEEDS = (3101, 3102, 3103)
CONDITIONS = ("t1-v2-reactive", "t1-v2-autonomous")
CONTRASTS = [("t1-v2-autonomous", "t1-v2-reactive")]

CONCEPT_CARDS: tuple[ConceptCardV1, ...] = (
    ConceptCardV1(
        "concept-token-bucket",
        "token bucket",
        "Token bucket shaping adds tokens at a fixed rate, spends one token per admitted packet, permits a bounded burst up to bucket capacity, and delays packets when the bucket is empty.",
        "Explain how token bucket shaping controls bursts.",
    ),
    ConceptCardV1(
        "concept-red-black-repair",
        "red black repair",
        "Red black repair restores tree invariants after insertion by recoloring a red parent and uncle or rotating around a black uncle until the root is black and no red node has a red child.",
        "Explain how red black repair restores insertion invariants.",
    ),
    ConceptCardV1(
        "concept-copy-on-write",
        "copy on write",
        "Copy on write lets processes share read-only physical pages, marks their page-table entries protected, and allocates a private copy only when a process first attempts to write.",
        "Explain how copy on write delays page copying.",
    ),
    ConceptCardV1(
        "concept-sliding-window",
        "sliding window",
        "Sliding window transmission numbers outstanding frames, advances the sender window after acknowledgements, retransmits missing sequence numbers, and limits unacknowledged data to the negotiated window size.",
        "Explain how a sliding window bounds outstanding frames.",
    ),
    ConceptCardV1(
        "concept-path-compression",
        "path compression",
        "Path compression follows parent pointers to a disjoint-set root and rewrites every visited node to point directly to that root, reducing the cost of later find operations.",
        "Explain how path compression accelerates later finds.",
    ),
    ConceptCardV1(
        "concept-lexical-closure",
        "lexical closure",
        "A lexical closure stores a function together with bindings from its defining scope, so later calls can resolve captured variables after that outer scope has returned.",
        "Explain how a lexical closure retains captured variables.",
    ),
)


def _validate_design() -> dict[str, object]:
    if set(SEEDS) & set(HISTORICAL_SEEDS):
        raise ValueError("fresh confirmation seeds overlap extension 014")
    ids = [card.concept_id for card in CONCEPT_CARDS]
    labels = [card.label for card in CONCEPT_CARDS]
    if len(ids) != len(set(ids)) or len(labels) != len(set(labels)):
        raise ValueError("confirmation concepts and labels must be unique")
    if len(CONCEPT_CARDS) != 6:
        raise ValueError("confirmation 025 requires six fresh concepts")
    return {
        "program_id": PROGRAM_ID,
        "status": "valid",
        "network_free": True,
        "cases": len(CONDITIONS) * len(PERSONAS) * len(SimulatorFamily) * len(SEEDS),
        "conditions": list(CONDITIONS),
        "concepts": ids,
        "seeds": list(SEEDS),
    }


def _decision(summary: dict) -> tuple[str, dict[str, dict[str, object]]]:
    gates: dict[str, dict[str, object]] = {}
    for condition in CONDITIONS:
        row = summary["aggregate"][condition]
        for metric, threshold in (
            ("attribution_accuracy", 0.95),
            ("assessment_agreement", 0.95),
            ("attempts_recognised", 1.0),
        ):
            value = float(row[metric])
            gates[f"{condition}:{metric}"] = {
                "threshold": threshold,
                "observed": value,
                "pass": value >= threshold,
            }
        for metric in (
            "quiet_hour_violations",
            "frequency_violations",
            "cooldown_violations",
            "provider_calls",
        ):
            value = float(row[metric])
            gates[f"{condition}:{metric}"] = {
                "threshold": 0,
                "observed": value,
                "pass": value == 0,
            }
    decision = (
        "completed-keep"
        if all(bool(gate["pass"]) for gate in gates.values())
        else "completed-refine"
    )
    return decision, gates


async def _run(output_dir: Path, *, smoke: bool) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"exclusive output already exists: {output_dir}")
    summary = await run_program(
        output_dir=output_dir,
        conditions=CONDITIONS,
        personas=PERSONAS[:1] if smoke else PERSONAS,
        families=tuple(SimulatorFamily),
        seeds=SEEDS[:1] if smoke else SEEDS,
        days=7 if smoke else 30,
        provider_backed=False,
        resamples=50 if smoke else 1000,
        program_id=PROGRAM_ID,
        concept_cards=CONCEPT_CARDS,
        fixture_id=FIXTURE_ID,
        contrasts=CONTRASTS,
    )
    decision, gates = _decision(summary)
    result = {"decision": decision, "gates": gates, "summary": summary}
    (output_dir / "decision.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "reports" / "generated" / PROGRAM_ID,
    )
    args = parser.parse_args()
    design = _validate_design()
    if args.validate or not (args.simulate or args.smoke):
        print(json.dumps(design, indent=2, sort_keys=True))
        return 0
    result = asyncio.run(_run(args.output_dir, smoke=args.smoke))
    print(json.dumps({"program_id": PROGRAM_ID, "decision": result["decision"]}, indent=2))
    return 0 if result["decision"] == "completed-keep" else 1


if __name__ == "__main__":
    raise SystemExit(main())
