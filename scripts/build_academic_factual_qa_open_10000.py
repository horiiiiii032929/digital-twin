#!/usr/bin/env python3
"""Plan and validate the open-source 10,000-question benchmark.

This entrypoint is intentionally network free.  It inventories the pinned
course snapshots, constructs deterministic non-overlapping source windows, and
validates the public-input/hidden-gold split.  Provider-backed dataset writing
remains blocked until the instrument allocation and execution authority are
both frozen explicitly.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_confirmation_v2 import (
    COURSES,
    SNAPSHOT_ROOT,
    Section,
    _load_sections,
    canonical_sha256,
    file_sha256,
)
from src.digital_twin.evaluation import EvaluationSplit, SourceClusterV1
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


INSTRUMENT_ID = "academic-factual-qa-open-10000-v1"
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_v1.json"
)
SOURCE_PLAN_PATH = (
    ROOT / "data/processed/academic_factual_qa_open_10000_v1_sources.json"
)

DEVELOPMENT_ALLOCATION = {
    "operating-systems": 25,
    "computer-networking": 25,
    "data-structures": 25,
    "python-programming": 25,
}
REQUESTED_FINAL_ALLOCATION = {
    "operating-systems": 100,
    "computer-networking": 1050,
    "data-structures": 400,
    "python-programming": 450,
}
RECOMMENDED_FINAL_ALLOCATION = {
    "operating-systems": 375,
    "computer-networking": 425,
    "data-structures": 325,
    "python-programming": 875,
}
MAX_CLUSTERS_PER_SECTION = 5
MIN_TEXT_WINDOW_CHARACTERS = 80
BOUNDARY_SLICES = ("no-evidence", "cross-course", "ambiguity", "academic-integrity")

SEMANTIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "structured-table": (
        r"\\begin\{tabular\}[\s\S]*?\\end\{tabular\}",
        r"(?m)^(?:\s*\|.+\|\s*\n){2,20}",
        r"(?m)^\s*\.\.\s+(?:csv-)?table::[^\n]*(?:\n(?:\s{3,}[^\n]*|\s*)?){1,25}",
    ),
    "structured-equation": (
        r"\$\$[\s\S]{2,900}?\$\$",
        r"\\\[[\s\S]{2,900}?\\\]",
        r"\\begin\{(?:equation|align|cases)\*?\}[\s\S]{2,900}?\\end\{(?:equation|align|cases)\*?\}",
        r"(?m)^\s*\.\.\s+math::(?:\n(?:\s{3,}[^\n]*|\s*)?){1,15}",
        r"\$[^\n$]{2,250}(?:=|\\frac|\\sum|\\sqrt)[^\n$]{0,250}\$",
        r"\$[^\n$]{2,250}\$",
    ),
    "structured-code": (
        r"```[^\n]*\n[\s\S]{5,1800}?```",
        r"(?m)^\s*\.\.\s+code-block::[^\n]*(?:\n(?:\s{3,}[^\n]*|\s*)?){1,40}",
        r"(?:\\(?:codeimport|javaimport|cppimport)\{[^\n]+\})",
    ),
}


class OpenBenchmarkBuildError(ValueError):
    """Raised when the prospective benchmark violates a frozen invariant."""


@dataclass(frozen=True)
class SourceWindow:
    course_id: str
    section: Section
    window_index: int
    relative_start: int
    relative_end: int
    modality: str

    @property
    def text(self) -> str:
        return self.section.text[self.relative_start : self.relative_end]

    @property
    def source_family_id(self) -> str:
        value = f"{self.course_id}:{self.section.family_key}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _load_instrument() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT_PATH.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise OpenBenchmarkBuildError("open benchmark instrument identity drifted")
    return instrument


def _semantic_ranges(text: str) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    for modality, patterns in SEMANTIC_PATTERNS.items():
        for pattern in patterns:
            rows.extend((match.start(), match.end(), modality) for match in re.finditer(pattern, text))
    rows.sort(key=lambda row: (row[0], -(row[1] - row[0]), row[2]))
    accepted: list[tuple[int, int, str]] = []
    for row in rows:
        if any(max(row[0], prior[0]) < min(row[1], prior[1]) for prior in accepted):
            continue
        accepted.append(row)
    return sorted(accepted)


def _trimmed_range(text: str, start: int, end: int) -> tuple[int, int] | None:
    raw = text[start:end]
    left = len(raw) - len(raw.lstrip())
    right = len(raw.rstrip())
    trimmed = (start + left, start + right)
    if trimmed[1] <= trimmed[0]:
        return None
    return trimmed


def _text_fill_ranges(
    text: str,
    occupied: list[tuple[int, int, str]],
    slots: int,
) -> list[tuple[int, int, str]]:
    if slots <= 0:
        return []
    merged: list[tuple[int, int]] = []
    for start, end, _ in sorted(occupied):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    gaps: list[tuple[int, int]] = []
    cursor = 0
    for start, end in merged:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < len(text):
        gaps.append((cursor, len(text)))

    candidates: list[tuple[int, int, str]] = []
    for gap_start, gap_end in sorted(gaps, key=lambda row: (-(row[1] - row[0]), row[0])):
        length = gap_end - gap_start
        count = min(slots - len(candidates), length // MIN_TEXT_WINDOW_CHARACTERS)
        if count <= 0:
            continue
        cuts = [gap_start + round(index * length / count) for index in range(count + 1)]
        for index in range(count):
            trimmed = _trimmed_range(text, cuts[index], cuts[index + 1])
            if trimmed is None or trimmed[1] - trimmed[0] < MIN_TEXT_WINDOW_CHARACTERS:
                continue
            candidates.append((trimmed[0], trimmed[1], "text"))
        if len(candidates) == slots:
            break
    return candidates[:slots]


def _windows_for_section(section: Section) -> list[SourceWindow]:
    candidates = _semantic_ranges(section.text)
    priority = {
        "structured-table": 0,
        "structured-equation": 1,
        "structured-code": 2,
    }
    candidates.sort(key=lambda row: (priority[row[2]], row[0], -(row[1] - row[0])))
    selected: list[tuple[int, int, str]] = []
    for start, end, modality in candidates:
        if any(max(start, left) < min(end, right) for left, right, _ in selected):
            continue
        selected.append((start, end, modality))
        if len(selected) == MAX_CLUSTERS_PER_SECTION:
            break
    selected.extend(
        _text_fill_ranges(
            section.text,
            selected,
            MAX_CLUSTERS_PER_SECTION - len(selected),
        )
    )
    if not selected:
        selected = [(0, len(section.text), "text")]
    selected.sort(key=lambda row: row[0])
    return [
        SourceWindow(
            course_id=section.course_id,
            section=section,
            window_index=index,
            relative_start=start,
            relative_end=end,
            modality=modality,
        )
        for index, (start, end, modality) in enumerate(selected, start=1)
    ]


def build_window_inventory() -> dict[str, list[SourceWindow]]:
    inventory: dict[str, list[SourceWindow]] = {}
    for course in COURSES:
        windows = [
            window
            for section in _load_sections(course)
            for window in _windows_for_section(section)
        ]
        inventory[course["course_id"]] = sorted(
            windows,
            key=lambda row: (
                row.window_index,
                row.section.path,
                row.section.start,
                row.relative_start,
            ),
        )
    return inventory


def feasibility_report() -> dict[str, Any]:
    inventory = build_window_inventory()
    section_counts = {
        course["course_id"]: len(_load_sections(course)) for course in COURSES
    }
    theoretical_caps = {
        course_id: count * MAX_CLUSTERS_PER_SECTION
        for course_id, count in section_counts.items()
    }
    available = {course_id: len(rows) for course_id, rows in inventory.items()}
    modality_capacity = {
        course_id: dict(Counter(row.modality for row in rows))
        for course_id, rows in inventory.items()
    }
    requested_total = {
        key: DEVELOPMENT_ALLOCATION[key] + REQUESTED_FINAL_ALLOCATION[key]
        for key in DEVELOPMENT_ALLOCATION
    }
    recommended_total = {
        key: DEVELOPMENT_ALLOCATION[key] + RECOMMENDED_FINAL_ALLOCATION[key]
        for key in DEVELOPMENT_ALLOCATION
    }
    requested_failures = {
        course_id: {
            "requested": requested_total[course_id],
            "theoretical_cap": theoretical_caps[course_id],
        }
        for course_id in requested_total
        if requested_total[course_id] > theoretical_caps[course_id]
    }
    recommended_inventory_failures = {
        course_id: {
            "requested": recommended_total[course_id],
            "available_non_overlapping_windows": available[course_id],
        }
        for course_id in recommended_total
        if recommended_total[course_id] > available[course_id]
    }
    return {
        "instrument_id": INSTRUMENT_ID,
        "section_counts": section_counts,
        "theoretical_caps": theoretical_caps,
        "available_non_overlapping_windows": available,
        "modality_capacity": modality_capacity,
        "requested_total": requested_total,
        "requested_feasible": not requested_failures,
        "requested_failures": requested_failures,
        "recommended_total": recommended_total,
        "recommended_inventory_feasible": not recommended_inventory_failures,
        "recommended_inventory_failures": recommended_inventory_failures,
        "provider_calls": 0,
        "private_data_read": False,
    }


def _slice_assignments(cluster_count: int, *, split: EvaluationSplit) -> list[tuple[list[str], str]]:
    if split == EvaluationSplit.FINAL:
        if cluster_count != 2000:
            raise OpenBenchmarkBuildError("final slice assignment requires 2,000 clusters")
        extended = (
            ["multi-evidence"] * 1000
            + ["structured-code"] * 700
            + ["structured-equation"] * 250
            + ["structured-table"] * 50
        )
    else:
        if cluster_count != 100:
            raise OpenBenchmarkBuildError("development slice assignment requires 100 clusters")
        extended = (
            ["multi-evidence"] * 50
            + ["structured-code"] * 35
            + ["structured-equation"] * 12
            + ["structured-table"] * 3
        )
    return [
        (
            ["direct-factual", "paraphrased", "definition-explanation", extra],
            BOUNDARY_SLICES[index % len(BOUNDARY_SLICES)],
        )
        for index, extra in enumerate(extended)
    ]


def _allocate_windows_for_slices(
    inventory: dict[str, list[SourceWindow]],
    allocation: dict[str, int],
    assignments: list[tuple[list[str], str]],
) -> list[tuple[SourceWindow, tuple[list[str], str]]]:
    if sum(allocation.values()) != len(assignments):
        raise OpenBenchmarkBuildError("course allocation and slice count differ")
    remaining_quota = dict(allocation)
    available = {course_id: list(rows) for course_id, rows in inventory.items()}
    selected: dict[int, SourceWindow] = {}

    def take_matching(index: int, modality: str) -> None:
        options: list[tuple[int, int, str, SourceWindow]] = []
        for course_id, quota in remaining_quota.items():
            if quota <= 0:
                continue
            matching = [row for row in available[course_id] if row.modality == modality]
            if matching:
                options.append((len(matching), quota, course_id, matching[0]))
        if not options:
            raise OpenBenchmarkBuildError(
                f"insufficient {modality} windows for slice assignment {index}"
            )
        _, _, course_id, chosen = max(options, key=lambda row: (row[0], row[1], row[2]))
        available[course_id].remove(chosen)
        remaining_quota[course_id] -= 1
        selected[index] = chosen

    # Allocate scarce structured evidence first. The remaining multi-evidence
    # slots can use any source window and therefore cannot starve these strata.
    for modality in ("structured-table", "structured-equation", "structured-code"):
        for index, (answerable, _) in enumerate(assignments):
            if answerable[-1] == modality:
                take_matching(index, modality)

    for index in range(len(assignments)):
        if index in selected:
            continue
        course_id = max(
            (key for key, quota in remaining_quota.items() if quota > 0),
            key=lambda key: (remaining_quota[key], key),
        )
        if not available[course_id]:
            raise OpenBenchmarkBuildError(f"{course_id} exhausted before its quota")
        chosen = available[course_id].pop(0)
        remaining_quota[course_id] -= 1
        selected[index] = chosen
    if any(remaining_quota.values()):
        raise OpenBenchmarkBuildError(f"unfilled course quotas: {remaining_quota}")
    return [(selected[index], assignments[index]) for index in range(len(assignments))]


def _cluster_record(
    window: SourceWindow,
    *,
    cluster_id: str,
    split: EvaluationSplit,
    slices: tuple[list[str], str],
    author_index: int,
) -> SourceClusterV1:
    course = next(row for row in COURSES if row["course_id"] == window.course_id)
    snapshot = SNAPSHOT_ROOT / course["snapshot"]
    source_path = snapshot / window.section.path
    absolute_start = window.section.start + window.relative_start
    absolute_end = window.section.start + window.relative_end
    return SourceClusterV1(
        cluster_id=cluster_id,
        source_family_id=window.source_family_id,
        course_id=window.course_id,
        source_artifact_id=f"{window.course_id}:{window.section.path}",
        source_version=1,
        source_sha256=file_sha256(source_path),
        source_path=window.section.path,
        section_heading=window.section.heading,
        char_start=absolute_start,
        char_end=absolute_end,
        text=window.text,
        source_modality=window.modality,
        split=split,
        answerable_slices=slices[0],
        boundary_slice=slices[1],
        author_family=("deepseek-v4-flash" if author_index % 2 == 0 else "gemini-3.7-flash"),
        verifier_family=("gemini-3.7-flash" if author_index % 2 == 0 else "deepseek-v4-flash"),
        license_spdx=course["license_spdx"],
        repository_url=course["repository_url"],
        repository_commit=course["commit"],
    )


def build_recommended_source_plan() -> dict[str, Any]:
    inventory = build_window_inventory()
    dev_slices = _slice_assignments(100, split=EvaluationSplit.DEVELOPMENT)
    development_pairs = _allocate_windows_for_slices(
        inventory, DEVELOPMENT_ALLOCATION, dev_slices
    )
    development = [row for row, _ in development_pairs]
    used = {
        (row.course_id, row.section.family_key, row.relative_start, row.relative_end)
        for row in development
    }
    remaining = {
        course_id: [
            row
            for row in rows
            if (row.course_id, row.section.family_key, row.relative_start, row.relative_end)
            not in used
        ]
        for course_id, rows in inventory.items()
    }
    final_slices = _slice_assignments(2000, split=EvaluationSplit.FINAL)
    final_pairs = _allocate_windows_for_slices(
        remaining, RECOMMENDED_FINAL_ALLOCATION, final_slices
    )
    final = [row for row, _ in final_pairs]
    clusters = [
        _cluster_record(
            row,
            cluster_id=f"academic-open-dev-{index:04d}",
            split=EvaluationSplit.DEVELOPMENT,
            slices=slices,
            author_index=index - 1,
        )
        for index, (row, slices) in enumerate(development_pairs, start=1)
    ] + [
        _cluster_record(
            row,
            cluster_id=f"academic-open-final-{index:05d}",
            split=EvaluationSplit.FINAL,
            slices=slices,
            author_index=index - 1,
        )
        for index, (row, slices) in enumerate(final_pairs, start=1)
    ]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "source_plan_id": "academic-factual-qa-open-10000-v1-sources",
        "instrument_id": INSTRUMENT_ID,
        "allocation": {
            "development": DEVELOPMENT_ALLOCATION,
            "final": RECOMMENDED_FINAL_ALLOCATION,
            "researcher_approved": False,
        },
        "cluster_count": len(clusters),
        "case_count_after_accepted_generation": len(clusters) * 5,
        "clusters": [row.model_dump(mode="json") for row in clusters],
        "raw_source_committed": False,
        "provider_calls": 0,
        "private_data_read": False,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    return payload


def validate_design() -> dict[str, Any]:
    instrument = _load_instrument()
    report = feasibility_report()
    if instrument["allocation"]["status"] != "pending-researcher-decision":
        raise OpenBenchmarkBuildError("unexpected allocation status")
    if report["requested_feasible"]:
        raise OpenBenchmarkBuildError("requested allocation unexpectedly became feasible")
    if not report["recommended_inventory_feasible"]:
        raise OpenBenchmarkBuildError(
            f"recommended allocation is infeasible: {report['recommended_inventory_failures']}"
        )
    plan = build_recommended_source_plan()
    if plan["cluster_count"] != 2100 or plan["case_count_after_accepted_generation"] != 10500:
        raise OpenBenchmarkBuildError("prospective source-plan size drifted")
    families: dict[str, int] = Counter(row["source_family_id"] for row in plan["clusters"])
    if max(families.values()) > MAX_CLUSTERS_PER_SECTION:
        raise OpenBenchmarkBuildError("source-section reuse cap exceeded")
    ranges: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for row in plan["clusters"]:
        key = (row["course_id"], row["source_path"])
        candidate = (row["char_start"], row["char_end"])
        if any(max(candidate[0], left) < min(candidate[1], right) for left, right in ranges[key]):
            raise OpenBenchmarkBuildError("selected source clusters overlap")
        ranges[key].append(candidate)
    return {
        **report,
        "status": "passed-build-only-allocation-pending",
        "prospective_cluster_count": plan["cluster_count"],
        "prospective_case_count": plan["case_count_after_accepted_generation"],
        "source_plan_sha256": plan["content_sha256"],
    }


def preflight() -> dict[str, Any]:
    instrument = _load_instrument()
    validation = validate_design()
    blockers: list[str] = []
    if instrument["allocation"]["status"] != "frozen-approved":
        blockers.append("source-allocation-not-approved")
    execution = instrument["execution"]
    for key in (
        "dataset_construction_authorized",
        "development_execution_authorized",
        "provider_execution_authorized",
        "paid_execution_authorized",
    ):
        if not execution[key]:
            blockers.append(f"{key.replace('_', '-')}-false")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "blocked-not-authorized" if blockers else "ready",
        "blockers": blockers,
        "validation": validation,
        "provider_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--write-source-plan", action="store_true")
    arguments = parser.parse_args()
    if arguments.write_source_plan:
        require_pre_evaluation_operation_allowed("dataset_generation")
        instrument = _load_instrument()
        if instrument["allocation"]["status"] != "frozen-approved" or not instrument[
            "execution"
        ]["dataset_construction_authorized"]:
            raise OpenBenchmarkBuildError("source-plan writing is not authorized")
        if SOURCE_PLAN_PATH.exists():
            raise OpenBenchmarkBuildError("source-plan output already exists")
        SOURCE_PLAN_PATH.write_text(
            json.dumps(build_recommended_source_plan(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result = {"status": "written", "path": str(SOURCE_PLAN_PATH), "provider_calls": 0}
    elif arguments.preflight:
        result = preflight()
    else:
        result = validate_design()
        if arguments.simulate:
            result = {**result, "status": "simulated-network-free"}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
