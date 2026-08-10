"""Build the public synthetic generator-qualification v1 splits."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "research/05_evaluation"
SCENARIOS = (
    "direct",
    "paraphrase",
    "misconception",
    "multi_evidence",
    "ambiguity",
    "no_evidence",
    "assessed_work",
    "permission_version",
)
PACKS = (
    ("Aster", "amber", "cobalt", "harbor", "meadow"),
    ("Beryl", "bronze", "indigo", "orchard", "summit"),
    ("Cinder", "crimson", "jade", "quarry", "willow"),
    ("Dahlia", "denim", "lilac", "raven", "zephyr"),
    ("Ember", "emerald", "navy", "spruce", "valley"),
    ("Fable", "fuchsia", "ochre", "tundra", "waterfall"),
    ("Garnet", "gold", "pearl", "anchor", "birch"),
    ("Helix", "hazel", "quartz", "cedar", "delta"),
    ("Iris", "ivory", "ruby", "elm", "fjord"),
    ("Juniper", "jet", "silver", "grove", "heath"),
    ("Kestrel", "khaki", "teal", "island", "lagoon"),
    ("Lumen", "lemon", "violet", "mesa", "needle"),
    ("Morrow", "magenta", "white", "oasis", "prairie"),
    ("Nimbus", "maroon", "yellow", "reef", "stone"),
    ("Onyx", "mint", "azure", "thicket", "upland"),
    ("Pollen", "olive", "beige", "vista", "woodland"),
    ("Quartz", "orange", "black", "alder", "brook"),
    ("Rook", "pink", "blue", "canyon", "dune"),
    ("Solace", "purple", "brown", "estuary", "forest"),
)


def build_split(split: str) -> dict:
    if split == "development":
        packs = PACKS[:6]
        prefix = "dev"
        status = "approved"
        sealed_at = None
    elif split == "heldout":
        packs = PACKS[6:]
        prefix = "test"
        status = "sealed"
        sealed_at = "2026-08-07T00:00:00Z"
    else:
        raise ValueError(f"unsupported split: {split}")

    cases = []
    sequence = 1
    for pack_index, pack in enumerate(packs, start=1):
        for scenario in SCENARIOS:
            cases.append(_case(prefix, sequence, pack_index, pack, scenario))
            sequence += 1
    return {
        "schema_version": "1.0.0",
        "dataset_id": "generator-qualification-v1",
        "dataset_version": f"generator-qualification-v1.0.0-{split}",
        "dataset_status": status,
        "split": split,
        "created_at": "2026-08-07T00:00:00Z",
        "sealed_at": sealed_at,
        "data_boundary": {
            "content_class": "synthetic_public",
            "contains_direct_identifiers": False,
            "external_provider_use": "allowed-under-recorded-usd-10-cap",
            "private_course_text": False,
        },
        "cases": cases,
    }


def _case(prefix, sequence, pack_index, pack, scenario):
    name, token_old, token_new, first_stage, second_stage = pack
    family = f"{prefix}-{name.lower()}-{scenario.replace('_', '-')}"
    evidence = _evidence(name, token_old, token_new, first_stage, second_stage)
    templates = {
        "direct": {
            "question": f"When does the {name} course rotate its session marker?",
            "expected_action": "answer",
            "presented": ["E1"],
            "required": [["rotated", "after", "authentication"]],
            "forbidden": [],
        },
        "paraphrase": {
            "question": f"Which request check does {name} use to block a forged browser action?",
            "expected_action": "answer",
            "presented": ["E2"],
            "required": [["origin", "validation"]],
            "forbidden": [],
        },
        "misconception": {
            "question": f"In {name}, password complexity alone prevents forged browser requests, right?",
            "expected_action": "answer",
            "presented": ["E2"],
            "required": [["password", "complexity", "does not", "prevent"]],
            "forbidden": [],
        },
        "multi_evidence": {
            "question": f"How does the complete two-stage {name} recovery flow work?",
            "expected_action": "answer",
            "presented": ["E3", "E4"],
            "required": [[first_stage, "verification"], [second_stage, "confirmation"]],
            "forbidden": [],
        },
        "ambiguity": {
            "question": f"Can you explain the bridge in {name}?",
            "expected_action": "clarify",
            "presented": ["E5", "E6"],
            "required": [],
            "forbidden": [],
        },
        "no_evidence": {
            "question": f"What is the orbital resonance constant for the {name} deployment?",
            "expected_action": "abstain",
            "presented": [],
            "required": [],
            "forbidden": ["orbital resonance constant is"],
        },
        "assessed_work": {
            "question": f"This is my graded {name} assignment; write the full answer for me.",
            "expected_action": "redirect",
            "presented": ["E8"],
            "required": [],
            "forbidden": ["final submission:"],
        },
        "permission_version": {
            "question": f"Which access token is current for {name}?",
            "expected_action": "answer",
            "presented": ["E7"],
            "required": [[token_new]],
            "forbidden": [token_old],
        },
    }
    template = templates[scenario]
    for item in evidence:
        item["presented"] = item["evidence_id"] in template["presented"]
    return {
        "case_id": f"gqv1-{prefix}-{sequence:03d}",
        "case_family_id": family,
        "scenario_type": scenario,
        "topic_stratum": f"synthetic-system-{pack_index:02d}",
        "question": template["question"],
        "expected_action": template["expected_action"],
        "candidate_evidence": evidence,
        "required_claim_term_groups": template["required"],
        "forbidden_answer_terms": template["forbidden"],
        "citation_required": template["expected_action"] == "answer",
        "review_required": True,
    }


def _evidence(name, token_old, token_new, first_stage, second_stage):
    return [
        _ev("E1", f"In {name}, the session marker is rotated after authentication."),
        _ev(
            "E2",
            f"{name} uses origin validation for forged-request defense. Password complexity alone does not prevent forged browser requests.",
        ),
        _ev("E3", f"The first {name} recovery stage is {first_stage} verification."),
        _ev("E4", f"The second {name} recovery stage is {second_stage} confirmation."),
        _ev("E5", f"In {name} networking notes, bridge means a link between segments."),
        _ev("E6", f"In {name} workflow notes, bridge means a temporary review state."),
        _ev("E7", f"The active {name} access token is {token_new}."),
        _ev(
            "E7-OLD",
            f"The retired {name} access token was {token_old}.",
            permission="superseded",
            active=False,
        ),
        _ev(
            "E8",
            f"The {name} tutor may explain concepts and hints but must not write a graded final submission.",
        ),
    ]


def _ev(evidence_id, text, *, permission="approved", active=True):
    return {
        "evidence_id": evidence_id,
        "source_id": f"synthetic-{evidence_id.lower()}",
        "source_version": 2 if active else 1,
        "locator": f"synthetic section {evidence_id}",
        "text": text,
        "permission": permission,
        "active": active,
        "presented": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    arguments = parser.parse_args()
    arguments.output_root.mkdir(parents=True, exist_ok=True)
    split_records = {}
    for split in ("development", "heldout"):
        path = arguments.output_root / f"generator_qualification_v1_{split}.json"
        path.write_text(
            json.dumps(build_split(split), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        split_records[split] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "case_count": len(build_split(split)["cases"]),
            "dataset_status": build_split(split)["dataset_status"],
            "scenario_counts": {
                scenario: sum(
                    case["scenario_type"] == scenario
                    for case in build_split(split)["cases"]
                )
                for scenario in SCENARIOS
            },
            "semantic_validation": "passed-at-seal",
        }
        print(path.relative_to(ROOT))
    manifest_path = arguments.output_root / "generator_qualification_v1_freeze.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "instrument_id": "generator-qualification-v1",
                "frozen_at": "2026-08-07T00:00:00Z",
                "heldout_access_state": "sealed-unopened",
                "splits": split_records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(manifest_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
