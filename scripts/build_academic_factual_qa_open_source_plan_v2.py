#!/usr/bin/env python3
"""Build the prospective complete-region development source plan.

This build is intentionally network free and development-only.  It preserves
the historical 2,100-cluster source plan while proving the corrected planner on
100 clusters before any final split or provider execution is opened.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_confirmation_v2 import (  # noqa: E402
    COURSES,
    SNAPSHOT_ROOT,
    Section,
    _load_sections,
    canonical_sha256,
    file_sha256,
)
from scripts.build_academic_factual_qa_open_10000 import (  # noqa: E402
    BOUNDARY_SLICES,
    DEVELOPMENT_ALLOCATION,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationSplit,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    ReferenceModality,
    ReferenceTargetV1,
    SemanticRegion,
    SourceClusterV2,
    extract_complete_text_regions,
    extract_structured_atoms,
    extract_structured_regions,
    target_from_regions,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-open-10000-deterministic-development-002"
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_deterministic_development_002.json"
)
SOURCE_PLAN_PATH = (
    ROOT
    / "data/processed/"
    "academic_factual_qa_open_10000_v1_development_sources_002.json"
)
MAX_CLUSTERS_PER_SECTION = 5
MAX_CLUSTER_CHARACTERS = 8000
TARGET_MODALITY_COUNTS: dict[ReferenceModality, int] = {
    "text": 56,
    "structured-code": 35,
    "structured-equation": 6,
    "structured-table": 3,
}
COURSE_MODALITY_ALLOCATION: dict[str, dict[ReferenceModality, int]] = {
    "operating-systems": {
        "text": 12,
        "structured-code": 13,
        "structured-equation": 0,
        "structured-table": 0,
    },
    "computer-networking": {
        "text": 18,
        "structured-code": 4,
        "structured-equation": 0,
        "structured-table": 3,
    },
    "data-structures": {
        "text": 19,
        "structured-code": 0,
        "structured-equation": 6,
        "structured-table": 0,
    },
    "python-programming": {
        "text": 7,
        "structured-code": 18,
        "structured-equation": 0,
        "structured-table": 0,
    },
}


class CorrectedSourcePlanError(RuntimeError):
    """Raised when the prospective source plan violates a frozen invariant."""


@dataclass(frozen=True)
class Candidate:
    course_id: str
    section: Section
    modality: ReferenceModality
    start: int
    end: int
    target_regions: tuple[tuple[SemanticRegion, ...], ...]

    @property
    def identity(self) -> tuple[str, str, int, int, str]:
        return (
            self.course_id,
            self.section.family_key,
            self.start,
            self.end,
            self.modality,
        )


def _instrument() -> dict[str, Any]:
    value = json.loads(INSTRUMENT_PATH.read_text(encoding="utf-8"))
    if value.get("instrument_id") != INSTRUMENT_ID:
        raise CorrectedSourcePlanError("corrected source-plan identity drifted")
    observed = canonical_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise CorrectedSourcePlanError("corrected source-plan instrument hash drifted")
    return value


def _text_candidates(course_id: str, section: Section) -> list[Candidate]:
    regions = extract_complete_text_regions(section.text)
    rows: list[Candidate] = []
    for offset in range(0, len(regions) - 2, 3):
        group = regions[offset : offset + 3]
        start = group[0].start
        end = group[-1].end
        if end - start > MAX_CLUSTER_CHARACTERS:
            continue
        rows.append(
            Candidate(
                course_id=course_id,
                section=section,
                modality="text",
                start=start,
                end=end,
                target_regions=(
                    (group[0],),
                    (group[1],),
                    (group[2],),
                    (group[0], group[1]),
                ),
            )
        )
    return rows[:MAX_CLUSTERS_PER_SECTION]


def _structured_candidates(course_id: str, section: Section) -> list[Candidate]:
    text_regions = extract_complete_text_regions(section.text)
    rows: list[Candidate] = []
    for structured in extract_structured_regions(section.text):
        atoms = extract_structured_atoms(structured)
        if len(atoms) >= 3:
            rows.append(
                Candidate(
                    course_id=course_id,
                    section=section,
                    modality=structured.modality,
                    start=structured.start,
                    end=structured.end,
                    target_regions=(
                        (atoms[0],),
                        (atoms[1],),
                        (atoms[2],),
                        (structured,),
                    ),
                )
            )
            continue
        nearest = sorted(
            text_regions,
            key=lambda row: (
                min(abs(row.end - structured.start), abs(row.start - structured.end)),
                row.start,
            ),
        )[:3]
        if len(nearest) != 3:
            continue
        ordered_text = sorted(nearest, key=lambda row: row.start)
        start = min(structured.start, *(row.start for row in ordered_text))
        end = max(structured.end, *(row.end for row in ordered_text))
        if end - start > MAX_CLUSTER_CHARACTERS:
            continue
        rows.append(
            Candidate(
                course_id=course_id,
                section=section,
                modality=structured.modality,
                start=start,
                end=end,
                target_regions=(
                    (ordered_text[0],),
                    (ordered_text[1],),
                    (ordered_text[2],),
                    (structured,),
                ),
            )
        )
    return rows


def build_candidate_inventory() -> dict[str, list[Candidate]]:
    inventory: dict[str, list[Candidate]] = defaultdict(list)
    for course in COURSES:
        course_id = course["course_id"]
        for section in _load_sections(course):
            inventory[course_id].extend(_text_candidates(course_id, section))
            inventory[course_id].extend(_structured_candidates(course_id, section))
    return {
        key: sorted(
            rows,
            key=lambda row: (
                row.section.path,
                row.section.start,
                row.start,
                row.end,
                row.modality,
            ),
        )
        for key, rows in inventory.items()
    }


def _overlaps(candidate: Candidate, selected: list[Candidate]) -> bool:
    return any(
        candidate.course_id == row.course_id
        and candidate.section.family_key == row.section.family_key
        and max(candidate.start, row.start) < min(candidate.end, row.end)
        for row in selected
    )


def _assignments() -> list[tuple[list[str], str]]:
    extended = (
        ["multi-evidence"] * TARGET_MODALITY_COUNTS["text"]
        + ["structured-code"] * TARGET_MODALITY_COUNTS["structured-code"]
        + ["structured-equation"]
        * TARGET_MODALITY_COUNTS["structured-equation"]
        + ["structured-table"] * TARGET_MODALITY_COUNTS["structured-table"]
    )
    return [
        (
            ["direct-factual", "paraphrased", "definition-explanation", extra],
            BOUNDARY_SLICES[index % len(BOUNDARY_SLICES)],
        )
        for index, extra in enumerate(extended)
    ]


def _select_candidates(
    inventory: dict[str, list[Candidate]],
) -> list[tuple[Candidate, tuple[list[str], str]]]:
    assignments = _assignments()
    selected: list[Candidate] = []
    section_counts: Counter[tuple[str, str]] = Counter()
    selected_by_modality: dict[ReferenceModality, list[Candidate]] = defaultdict(list)

    # Reserve complete prose windows first.  This is material for the sparse
    # operating-systems source, where most code examples sit inside the same
    # short slide sections as the only usable explanatory statements.
    for course_id in sorted(COURSE_MODALITY_ALLOCATION):
        required = COURSE_MODALITY_ALLOCATION[course_id]["text"]
        candidates = [row for row in inventory[course_id] if row.modality == "text"]
        candidates.sort(
            key=lambda row: (
                sum(
                    _overlaps(row, [other])
                    for other in inventory[course_id]
                    if other.modality != "text"
                ),
                row.end - row.start,
                row.identity,
            )
        )
        for row in candidates:
            if len(selected_by_modality["text"]) >= sum(
                COURSE_MODALITY_ALLOCATION[key]["text"]
                for key in sorted(COURSE_MODALITY_ALLOCATION)
                if key <= course_id
            ):
                break
            if section_counts[(row.course_id, row.section.family_key)] >= MAX_CLUSTERS_PER_SECTION:
                continue
            if _overlaps(row, selected):
                continue
            selected.append(row)
            selected_by_modality["text"].append(row)
            section_counts[(row.course_id, row.section.family_key)] += 1
        observed = sum(
            row.course_id == course_id for row in selected_by_modality["text"]
        )
        if observed != required:
            raise CorrectedSourcePlanError(
                f"{course_id} has {observed}/{required} complete text candidates"
            )

    for modality in (
        "structured-table",
        "structured-equation",
        "structured-code",
    ):
        for course_id in sorted(COURSE_MODALITY_ALLOCATION):
            required = COURSE_MODALITY_ALLOCATION[course_id][modality]
            for _ in range(required):
                options = [
                    row
                    for row in inventory[course_id]
                    if row.modality == modality
                    and section_counts[(row.course_id, row.section.family_key)]
                    < MAX_CLUSTERS_PER_SECTION
                    and not _overlaps(row, selected)
                ]
                options.sort(key=lambda row: (row.end - row.start, row.identity))
                if not options:
                    break
                row = options[0]
                selected.append(row)
                selected_by_modality[modality].append(row)
                section_counts[(row.course_id, row.section.family_key)] += 1
            observed = sum(
                row.course_id == course_id
                for row in selected_by_modality[modality]
            )
            if observed != required:
                raise CorrectedSourcePlanError(
                    f"{course_id} has {observed}/{required} {modality} candidates"
                )

    output: list[tuple[Candidate, tuple[list[str], str]]] = []
    cursors: Counter[ReferenceModality] = Counter()
    for slices in assignments:
        modality: ReferenceModality = (
            "text" if slices[0][-1] == "multi-evidence" else slices[0][-1]  # type: ignore[assignment]
        )
        index = cursors[modality]
        output.append((selected_by_modality[modality][index], slices))
        cursors[modality] += 1
    return output


def _cluster(
    candidate: Candidate,
    *,
    cluster_id: str,
    slices: tuple[list[str], str],
) -> SourceClusterV2:
    course = next(row for row in COURSES if row["course_id"] == candidate.course_id)
    source_path = SNAPSHOT_ROOT / course["snapshot"] / candidate.section.path
    absolute_start = candidate.section.start + candidate.start
    absolute_end = candidate.section.start + candidate.end
    targets: list[ReferenceTargetV1] = [
        target_from_regions(
            slice_name=slice_name,
            cluster_start=candidate.start,
            regions=list(regions),
        )
        for slice_name, regions in zip(
            slices[0], candidate.target_regions, strict=True
        )
    ]
    family_value = f"{candidate.course_id}:{candidate.section.family_key}"
    return SourceClusterV2(
        cluster_id=cluster_id,
        source_family_id=hashlib.sha256(family_value.encode()).hexdigest()[:24],
        course_id=candidate.course_id,
        source_artifact_id=f"{candidate.course_id}:{candidate.section.path}",
        source_version=1,
        source_sha256=file_sha256(source_path),
        source_path=candidate.section.path,
        section_heading=candidate.section.heading,
        char_start=absolute_start,
        char_end=absolute_end,
        text=candidate.section.text[candidate.start : candidate.end],
        source_modality=candidate.modality,
        split=EvaluationSplit.DEVELOPMENT,
        answerable_slices=slices[0],
        boundary_slice=slices[1],
        author_family="deterministic-reference-planner-v3",
        verifier_family="deterministic-reference-auditor-v3",
        license_spdx=course["license_spdx"],
        repository_url=course["repository_url"],
        repository_commit=course["commit"],
        reference_targets=targets,
    )


def build_source_plan() -> dict[str, Any]:
    _instrument()
    inventory = build_candidate_inventory()
    selected = _select_candidates(inventory)
    clusters = [
        _cluster(
            candidate,
            cluster_id=f"academic-open-dev2-{index:04d}",
            slices=slices,
        )
        for index, (candidate, slices) in enumerate(selected, start=1)
    ]
    ranges: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for cluster in clusters:
        key = (cluster.course_id, cluster.source_path)
        candidate = (cluster.char_start, cluster.char_end)
        if any(
            max(candidate[0], start) < min(candidate[1], end)
            for start, end in ranges[key]
        ):
            raise CorrectedSourcePlanError("selected complete-region clusters overlap")
        ranges[key].append(candidate)
    payload: dict[str, Any] = {
        "schema_version": 2,
        "source_plan_id": "academic-factual-qa-open-10000-development-sources-002",
        "successor_of": "academic-factual-qa-open-10000-v1-sources",
        "instrument_id": INSTRUMENT_ID,
        "split": "development",
        "cluster_count": len(clusters),
        "case_count_after_deterministic_build": len(clusters) * 5,
        "course_distribution": dict(
            sorted(Counter(row.course_id for row in clusters).items())
        ),
        "modality_distribution": dict(
            sorted(Counter(row.source_modality for row in clusters).items())
        ),
        "clusters": [row.model_dump(mode="json") for row in clusters],
        "provider_calls": 0,
        "private_data_read": False,
        "final_split_opened": False,
        "raw_source_committed": False,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    return payload


def validate_plan() -> dict[str, Any]:
    first = build_source_plan()
    second = build_source_plan()
    if first["content_sha256"] != second["content_sha256"]:
        raise CorrectedSourcePlanError("corrected source plan is not byte stable")
    if first["cluster_count"] != 100:
        raise CorrectedSourcePlanError("corrected source plan is not 100 clusters")
    if first["course_distribution"] != DEVELOPMENT_ALLOCATION:
        raise CorrectedSourcePlanError("corrected course allocation drifted")
    if first["modality_distribution"] != TARGET_MODALITY_COUNTS:
        raise CorrectedSourcePlanError("corrected modality allocation drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "source_plan_sha256": first["content_sha256"],
        "cluster_count": first["cluster_count"],
        "case_count": first["case_count_after_deterministic_build"],
        "course_distribution": first["course_distribution"],
        "modality_distribution": first["modality_distribution"],
        "provider_calls": 0,
        "private_data_read": False,
        "final_split_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--write-source-plan", action="store_true")
    arguments = parser.parse_args()
    if arguments.write_source_plan:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
        if SOURCE_PLAN_PATH.exists():
            raise CorrectedSourcePlanError("corrected source-plan output already exists")
        SOURCE_PLAN_PATH.write_text(
            json.dumps(build_source_plan(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result = {
            **validate_plan(),
            "status": "completed-build-only",
            "output": str(SOURCE_PLAN_PATH.relative_to(ROOT)),
        }
    else:
        result = validate_plan()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
