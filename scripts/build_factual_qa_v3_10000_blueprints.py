#!/usr/bin/env python3
"""Build and validate deterministic blueprints for the 10,000-case QA pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/factual_qa_v3_10000_pipeline_001.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated/factual-qa-v3-10000-blueprints-001.json"
INSTRUMENT_ID = "factual-qa-v3-10000-pipeline-001"
COURSE_COUNT = 20
CLAIMS_PER_SOURCE = 8
SOURCE_MODALITIES = {
    "text": 25,
    "code": 6,
    "table": 6,
    "diagram": 4,
    "equation": 3,
    "screenshot": 3,
    "scanned": 3,
}
SLICE_COUNTS = {
    "direct-text": 2_000,
    "paraphrase-text": 1_500,
    "multi-source": 1_500,
    "code": 800,
    "table": 800,
    "diagram": 500,
    "equation": 400,
    "visual-other": 500,
    "no-evidence": 500,
    "ambiguous": 500,
    "cross-course-confusion": 500,
    "academic-integrity": 500,
}
ANSWERABLE_SLICES = frozenset(
    {
        "direct-text",
        "paraphrase-text",
        "multi-source",
        "code",
        "table",
        "diagram",
        "equation",
        "visual-other",
    }
)
STAGE_COUNTS = {"pilot-100": 100, "checkpoint-1000": 900, "scale-10000": 9_000}


class BlueprintDesignError(ValueError):
    """Raised when the deterministic corpus or blueprint contract drifts."""


def validate_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise BlueprintDesignError("unexpected 10,000-case instrument ID")
    if instrument.get("model_leaderboard") is not False:
        raise BlueprintDesignError("the pipeline cannot become a model leaderboard")
    source_design = instrument.get("dummy_source_universe", {})
    if (
        source_design.get("course_count") != COURSE_COUNT
        or source_design.get("source_unit_count") != 1_000
        or source_design.get("claim_count") != 8_000
        or source_design.get("source_modalities_per_course") != SOURCE_MODALITIES
    ):
        raise BlueprintDesignError("dummy source design drifted")
    if instrument.get("case_design", {}).get("slice_counts") != SLICE_COUNTS:
        raise BlueprintDesignError("case slice design drifted")
    safety = instrument.get("execution_safety", {})
    if safety.get("provider_execution_authorized") is not False:
        raise BlueprintDesignError("provider execution must remain unauthorized")
    if safety.get("dataset_write_authorized") is not False:
        raise BlueprintDesignError("dataset writing must remain unauthorized")
    if instrument.get("decision_rule", {}).get("authorize_10000_by_this_instrument") is not False:
        raise BlueprintDesignError("instrument cannot self-authorize 10,000 cases")
    return instrument


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _claim_text(course_number: int, source_number: int, claim_number: int) -> str:
    marker = f"C{course_number:02d}-U{source_number:02d}-K{claim_number:02d}"
    value = course_number * 1_000 + source_number * 10 + claim_number
    templates = (
        f"Rule {marker} uses threshold {value} units.",
        f"Mapping {marker} sends input P{value} to output Q{value + 7}.",
        f"Sequence {marker} places step S{claim_number} before step S{claim_number + 1}.",
        f"Exception {marker} applies only when flag F{value % 17} is active.",
        f"Schedule {marker} repeats every {(value % 11) + 2} intervals.",
        f"Dependency {marker} requires component D{value % 31} first.",
        f"Policy {marker} permits the action when condition B{value % 19} is true.",
        f"Allocation {marker} reserves {(value % 73) + 20} percent for group G{value % 13}.",
    )
    return templates[claim_number - 1]


def _representation(modality: str, claims: list[dict[str, str]]) -> dict[str, Any]:
    statements = [claim["text"] for claim in claims]
    if modality == "text":
        return {"kind": "paragraph", "content": " ".join(statements)}
    if modality == "code":
        lines = ["def synthetic_rules():", "    return {"]
        lines.extend(
            f'        "{claim["claim_id"]}": {json.dumps(claim["text"])},'
            for claim in claims
        )
        lines.append("    }")
        return {"kind": "code", "language": "python", "content": "\n".join(lines)}
    if modality == "table":
        return {
            "kind": "table",
            "columns": ["claim_id", "statement"],
            "rows": [[claim["claim_id"], claim["text"]] for claim in claims],
        }
    if modality == "diagram":
        return {
            "kind": "diagram",
            "nodes": [
                {"node_id": claim["claim_id"], "label": claim["text"]}
                for claim in claims
            ],
            "edges": [
                {
                    "from": claims[index]["claim_id"],
                    "to": claims[index + 1]["claim_id"],
                    "label": "precedes",
                }
                for index in range(len(claims) - 1)
            ],
        }
    if modality == "equation":
        return {
            "kind": "equation",
            "latex": "y_i = a_i x_i + b_i",
            "annotations": [
                {"symbol": f"a_{index}", "statement": claim["text"]}
                for index, claim in enumerate(claims, start=1)
            ],
        }
    if modality == "screenshot":
        return {
            "kind": "screenshot-layout",
            "canvas": {"width": 1200, "height": 800},
            "regions": [
                {
                    "bbox": [40, 40 + index * 85, 1160, 105 + index * 85],
                    "text": claim["text"],
                }
                for index, claim in enumerate(claims)
            ],
        }
    if modality == "scanned":
        return {
            "kind": "scanned-document",
            "scan_quality": "synthetic-degraded",
            "ocr_lines": statements,
        }
    raise BlueprintDesignError(f"unsupported modality: {modality}")


def build_sources() -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for course_number in range(1, COURSE_COUNT + 1):
        course_id = f"dummy-course-{course_number:02d}"
        source_number = 0
        for modality, count in SOURCE_MODALITIES.items():
            for _ in range(count):
                source_number += 1
                source_id = f"{course_id}-unit-{source_number:02d}"
                claims = []
                for claim_number in range(1, CLAIMS_PER_SOURCE + 1):
                    text = _claim_text(course_number, source_number, claim_number)
                    claims.append(
                        {
                            "claim_id": f"{source_id}-claim-{claim_number:02d}",
                            "text": text,
                            "evidence_quote": text,
                        }
                    )
                sources.append(
                    {
                        "source_unit_id": source_id,
                        "course_id": course_id,
                        "document_id": f"{course_id}-document-{source_number:02d}",
                        "modality": modality,
                        "source_truth": " ".join(claim["text"] for claim in claims),
                        "representation": _representation(modality, claims),
                        "claims": claims,
                    }
                )
    return sources


def _claim_pool(
    course_sources: list[dict[str, Any]], modalities: Iterable[str]
) -> list[tuple[dict[str, Any], dict[str, str]]]:
    accepted = set(modalities)
    return [
        (source, claim)
        for source in course_sources
        if source["modality"] in accepted
        for claim in source["claims"]
    ]


def _blueprint(
    *,
    case_id: str,
    slice_name: str,
    course_id: str,
    expected_action: str,
    targets: list[tuple[dict[str, Any], dict[str, str]]],
    distractors: list[dict[str, Any]],
    intent: str,
) -> dict[str, Any]:
    return {
        "blueprint_id": case_id,
        "slice": slice_name,
        "course_id": course_id,
        "expected_action": expected_action,
        "target_claim_ids": [claim["claim_id"] for _, claim in targets],
        "evidence_unit_ids": list(dict.fromkeys(source["source_unit_id"] for source, _ in targets)),
        "distractor_unit_ids": [source["source_unit_id"] for source in distractors],
        "intent": intent,
    }


def _course_blueprints(
    course_number: int,
    sources_by_course: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    course_id = f"dummy-course-{course_number:02d}"
    course_sources = sources_by_course[course_id]
    other_course_id = f"dummy-course-{(course_number % COURSE_COUNT) + 1:02d}"
    other_sources = sources_by_course[other_course_id]
    pools = {
        "text": _claim_pool(course_sources, ("text",)),
        "code": _claim_pool(course_sources, ("code",)),
        "table": _claim_pool(course_sources, ("table",)),
        "diagram": _claim_pool(course_sources, ("diagram",)),
        "equation": _claim_pool(course_sources, ("equation",)),
        "visual-other": _claim_pool(course_sources, ("screenshot", "scanned")),
    }
    counts = {
        "direct-text": 100,
        "paraphrase-text": 75,
        "multi-source": 75,
        "code": 40,
        "table": 40,
        "diagram": 25,
        "equation": 20,
        "visual-other": 25,
    }
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    case_number = 0

    for slice_name, count in counts.items():
        pool_name = slice_name if slice_name in pools else "text"
        pool = pools[pool_name]
        for local_index in range(count):
            case_number += 1
            if slice_name == "multi-source":
                first = pool[local_index % len(pool)]
                second = pool[(local_index + 103) % len(pool)]
                if first[0]["source_unit_id"] == second[0]["source_unit_id"]:
                    second = pool[(local_index + 111) % len(pool)]
                targets = [first, second]
            else:
                offset = 100 if slice_name == "paraphrase-text" else 0
                targets = [pool[(local_index + offset) % len(pool)]]
            target_sources = {source["source_unit_id"] for source, _ in targets}
            distractor = next(
                source
                for source in reversed(course_sources)
                if source["source_unit_id"] not in target_sources
            )
            buckets[slice_name].append(
                _blueprint(
                    case_id=f"fqa10k-c{course_number:02d}-{case_number:03d}",
                    slice_name=slice_name,
                    course_id=course_id,
                    expected_action="answer",
                    targets=targets,
                    distractors=[distractor],
                    intent=f"Author one {slice_name} factual question from the exact target claims.",
                )
            )

    text_pool = pools["text"]
    for boundary_name, expected_action in (
        ("no-evidence", "abstain"),
        ("ambiguous", "clarify"),
        ("cross-course-confusion", "answer"),
        ("academic-integrity", "refuse"),
    ):
        for local_index in range(25):
            case_number += 1
            target = text_pool[(local_index * 7) % len(text_pool)]
            other = other_sources[(local_index * 3) % len(other_sources)]
            if boundary_name in {"no-evidence", "academic-integrity"}:
                targets: list[tuple[dict[str, Any], dict[str, str]]] = []
                distractors = [other]
            elif boundary_name == "ambiguous":
                targets = [target, text_pool[(local_index * 7 + 9) % len(text_pool)]]
                distractors = []
            else:
                targets = [target]
                distractors = [other]
            buckets[boundary_name].append(
                _blueprint(
                    case_id=f"fqa10k-c{course_number:02d}-{case_number:03d}",
                    slice_name=boundary_name,
                    course_id=course_id,
                    expected_action=expected_action,
                    targets=targets,
                    distractors=distractors,
                    intent=f"Test the {boundary_name} boundary without inventing evidence.",
                )
            )
    if case_number != 500:
        raise BlueprintDesignError(f"{course_id} produced {case_number} cases")
    return buckets


def _assign_checkpoint_stages(
    by_slice: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    course_ids = [f"dummy-course-{number:02d}" for number in range(1, 21)]
    available = {
        slice_name: {
            course_id: [item for item in items if item["course_id"] == course_id]
            for course_id in course_ids
        }
        for slice_name, items in by_slice.items()
    }
    staged: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for stage, per_course_capacity, percentage in (
        ("pilot-100", 5, 1),
        ("checkpoint-1000", 45, 9),
    ):
        capacity = {course_id: per_course_capacity for course_id in course_ids}
        for slice_index, (slice_name, total) in enumerate(SLICE_COUNTS.items()):
            quota = total * percentage // 100
            for item_index in range(quota):
                cyclic_order = [
                    course_ids[(slice_index + item_index + offset) % COURSE_COUNT]
                    for offset in range(COURSE_COUNT)
                ]
                candidates = [
                    course_id
                    for course_id in cyclic_order
                    if capacity[course_id] > 0 and available[slice_name][course_id]
                ]
                if not candidates:
                    raise BlueprintDesignError(
                        f"cannot stratify {slice_name} into {stage}"
                    )
                course_id = max(candidates, key=lambda value: capacity[value])
                item = available[slice_name][course_id].pop(0)
                capacity[course_id] -= 1
                staged[stage].append({**item, "checkpoint_stage": stage})
        if any(capacity.values()):
            raise BlueprintDesignError(f"{stage} course capacities were not filled")

    for slice_name in SLICE_COUNTS:
        for course_id in course_ids:
            staged["scale-10000"].extend(
                {**item, "checkpoint_stage": "scale-10000"}
                for item in available[slice_name][course_id]
            )
    return [
        item
        for stage in STAGE_COUNTS
        for item in sorted(
            staged[stage], key=lambda value: (value["slice"], value["blueprint_id"])
        )
    ]


def build_blueprints(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in sources:
        sources_by_course[source["course_id"]].append(source)
    course_buckets = {
        course_number: _course_blueprints(course_number, sources_by_course)
        for course_number in range(1, COURSE_COUNT + 1)
    }
    by_slice: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for slice_index, slice_name in enumerate(SLICE_COUNTS):
        course_order = [
            ((slice_index + offset) % COURSE_COUNT) + 1
            for offset in range(COURSE_COUNT)
        ]
        per_course = [course_buckets[number][slice_name] for number in course_order]
        for local_index in range(max(len(items) for items in per_course)):
            for items in per_course:
                if local_index < len(items):
                    by_slice[slice_name].append(items[local_index])

    for slice_name, expected_count in SLICE_COUNTS.items():
        items = by_slice[slice_name]
        if len(items) != expected_count:
            raise BlueprintDesignError(f"{slice_name} produced {len(items)} cases")
    return _assign_checkpoint_stages(by_slice)


def validate_design(
    sources: list[dict[str, Any]], blueprints: list[dict[str, Any]]
) -> dict[str, Any]:
    source_ids = [source["source_unit_id"] for source in sources]
    claim_index = {
        claim["claim_id"]: (source["source_unit_id"], claim)
        for source in sources
        for claim in source["claims"]
    }
    case_ids = [case["blueprint_id"] for case in blueprints]
    errors: list[str] = []
    if len(sources) != 1_000 or len(source_ids) != len(set(source_ids)):
        errors.append("source IDs must contain exactly 1,000 unique values")
    if len(claim_index) != 8_000:
        errors.append("claim IDs must contain exactly 8,000 unique values")
    if len(blueprints) != 10_000 or len(case_ids) != len(set(case_ids)):
        errors.append("blueprint IDs must contain exactly 10,000 unique values")
    if Counter(case["slice"] for case in blueprints) != Counter(SLICE_COUNTS):
        errors.append("slice distribution drifted")
    if Counter(case["checkpoint_stage"] for case in blueprints) != Counter(STAGE_COUNTS):
        errors.append("checkpoint distribution drifted")
    expected_stage_course_counts = {
        "pilot-100": 5,
        "checkpoint-1000": 45,
        "scale-10000": 450,
    }
    for stage, per_course_count in expected_stage_course_counts.items():
        counts = Counter(
            case["course_id"]
            for case in blueprints
            if case["checkpoint_stage"] == stage
        )
        if set(counts.values()) != {per_course_count} or len(counts) != COURSE_COUNT:
            errors.append(f"{stage} course stratification drifted")
            break
    for slice_name, total in SLICE_COUNTS.items():
        stage_counts = Counter(
            case["checkpoint_stage"]
            for case in blueprints
            if case["slice"] == slice_name
        )
        expected = {
            "pilot-100": total // 100,
            "checkpoint-1000": total * 9 // 100,
            "scale-10000": total * 90 // 100,
        }
        if stage_counts != Counter(expected):
            errors.append(f"{slice_name} checkpoint stratification drifted")
            break
    known_sources = set(source_ids)
    for case in blueprints:
        targets = case["target_claim_ids"]
        evidence = case["evidence_unit_ids"]
        if not set(evidence + case["distractor_unit_ids"]).issubset(known_sources):
            errors.append(f"{case['blueprint_id']} references an unknown source")
            break
        if not set(targets).issubset(claim_index):
            errors.append(f"{case['blueprint_id']} references an unknown claim")
            break
        expected_evidence = {claim_index[target][0] for target in targets}
        if set(evidence) != expected_evidence:
            errors.append(f"{case['blueprint_id']} claim/source lineage drifted")
            break
        if case["slice"] == "multi-source" and len(set(evidence)) != 2:
            errors.append(f"{case['blueprint_id']} is not truly multi-source")
            break
        if case["slice"] in ANSWERABLE_SLICES and case["expected_action"] != "answer":
            errors.append(f"{case['blueprint_id']} has the wrong answer action")
            break
    for source in sources:
        representation = json.dumps(source["representation"], sort_keys=True)
        if any(claim["evidence_quote"] not in representation for claim in source["claims"]):
            errors.append(f"{source['source_unit_id']} representation lost source truth")
            break
    if errors:
        raise BlueprintDesignError("; ".join(errors))
    return {
        "instrument_id": INSTRUMENT_ID,
        "source_count": len(sources),
        "claim_count": len(claim_index),
        "case_count": len(blueprints),
        "slice_counts": dict(sorted(Counter(case["slice"] for case in blueprints).items())),
        "stage_counts": dict(sorted(Counter(case["checkpoint_stage"] for case in blueprints).items())),
        "course_counts": dict(sorted(Counter(case["course_id"] for case in blueprints).items())),
        "source_modality_counts": dict(sorted(Counter(source["modality"] for source in sources).items())),
        "content_sha256": _canonical_sha256({"sources": sources, "blueprints": blueprints}),
        "external_calls": 0,
        "private_data_read": False,
        "status": "passed",
    }


def build_artifact() -> dict[str, Any]:
    instrument = validate_instrument()
    sources = build_sources()
    blueprints = build_blueprints(sources)
    summary = validate_design(sources, blueprints)
    return {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": _canonical_sha256(instrument),
        "summary": summary,
        "sources": sources,
        "blueprints": blueprints,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.write:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
    artifact = build_artifact()
    if args.write:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite existing artifact: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(json.dumps(artifact["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
