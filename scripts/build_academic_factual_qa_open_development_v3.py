#!/usr/bin/env python3
"""Build the complete-region 500-case open benchmark development package."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_open_source_plan_v2 import (  # noqa: E402
    INSTRUMENT_ID,
    SOURCE_PLAN_PATH,
    build_source_plan,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import (  # noqa: E402
    normalize_question,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    SourceClusterV2,
    build_reference_cluster_rows,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
DEVELOPMENT_CASES_PATH = (
    DATASET_ROOT
    / "academic_factual_qa_open_10000_v1_development_cases_002.json"
)
DEVELOPMENT_GOLD_PATH = (
    DATASET_ROOT
    / "academic_factual_qa_open_10000_v1_development_gold_002.json"
)
DEVELOPMENT_CONTROL_CASES_PATH = (
    DATASET_ROOT
    / "academic_factual_qa_open_10000_v1_development_control_cases_002.json"
)
DEVELOPMENT_CONTROL_GOLD_PATH = (
    DATASET_ROOT
    / "academic_factual_qa_open_10000_v1_development_control_gold_002.json"
)
COURSE_IDS = [
    "operating-systems",
    "computer-networking",
    "data-structures",
    "python-programming",
]


class CorrectedDevelopmentBuildError(RuntimeError):
    """Raised when the corrected deterministic package violates its contract."""


def _package(
    *,
    rows_key: str,
    rows: list[dict[str, Any]],
    split: str,
    source_plan_sha256: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": f"academic-factual-qa-open-10000-v1-{split}-002",
        "construction_instrument_id": INSTRUMENT_ID,
        "construction_method": "deterministic-complete-region-v3",
        "source_plan_sha256": source_plan_sha256,
        "canonical_wording_status": "development-template-not-final-naturalness-evidence",
        "split": split,
        "case_count": len(rows),
        rows_key: rows,
        "provider_calls": 0,
        "private_data_used": False,
        "final_split_opened": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def _disambiguate_questions(
    cases: list[EvaluationCaseV1],
    clusters: dict[str, SourceClusterV2],
) -> list[EvaluationCaseV1]:
    by_question: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(cases):
        by_question[normalize_question(row.question)].append(index)
    output = list(cases)
    for indices in by_question.values():
        if len(indices) < 2:
            continue
        for index in indices:
            row = output[index]
            cluster = clusters[row.cluster_id]
            locator = Path(cluster.source_path).stem.replace("_", " ").replace("-", " ")
            example = cluster.cluster_id.rsplit("-", 1)[-1]
            output[index] = row.model_copy(
                update={
                    "question": (
                        f"{row.question.rstrip('?.!')} in the {cluster.course_id} "
                        f'source section "{locator}: {cluster.section_heading}" '
                        f"(development source example {example})?"
                    )
                }
            )
    normalized = [normalize_question(row.question) for row in output]
    if len(normalized) != len(set(normalized)):
        raise CorrectedDevelopmentBuildError(
            "source-locator disambiguation left normalized duplicate questions"
        )
    return output


def build_packages() -> dict[str, Any]:
    source_plan = build_source_plan()
    clusters = [
        SourceClusterV2.model_validate(row) for row in source_plan["clusters"]
    ]
    cluster_by_id = {row.cluster_id: row for row in clusters}
    if len(clusters) != 100 or len(cluster_by_id) != 100:
        raise CorrectedDevelopmentBuildError("corrected source plan is not 100 clusters")

    cases: list[EvaluationCaseV1] = []
    gold: list[EvaluationGoldV1] = []
    for cluster in clusters:
        cluster_cases, cluster_gold = build_reference_cluster_rows(
            cluster,
            course_ids=COURSE_IDS,
        )
        cases.extend(cluster_cases)
        gold.extend(cluster_gold)
    cases = _disambiguate_questions(cases, cluster_by_id)
    ordered_cases = sorted(cases, key=lambda row: row.case_id)
    ordered_gold = sorted(gold, key=lambda row: row.case_id)

    if len(ordered_cases) != 500 or len(ordered_gold) != 500:
        raise CorrectedDevelopmentBuildError("corrected package is not 500 by 500")
    if {row.case_id for row in ordered_cases} != {row.case_id for row in ordered_gold}:
        raise CorrectedDevelopmentBuildError("public and hidden-gold IDs differ")
    answerable = [
        row for row in ordered_gold if row.expected_action == EvaluationAction.ANSWER
    ]
    boundary = [
        row for row in ordered_gold if row.expected_action != EvaluationAction.ANSWER
    ]
    if len(answerable) != 400 or len(boundary) != 100:
        raise CorrectedDevelopmentBuildError("corrected action distribution drifted")
    if any(not row.claims for row in answerable) or any(row.claims for row in boundary):
        raise CorrectedDevelopmentBuildError("corrected lineage policy drifted")
    gold_by_id = {row.case_id: row for row in ordered_gold}
    answer_leaks: list[str] = []
    for row in ordered_cases:
        expected = gold_by_id[row.case_id]
        normalized_answer = normalize_question(expected.canonical_answer)
        answer_tokens = normalized_answer.split()
        question_tokens = normalize_question(row.question).split()
        leaked = any(
            question_tokens[index : index + len(answer_tokens)] == answer_tokens
            for index in range(len(question_tokens) - len(answer_tokens) + 1)
        )
        if (
            expected.expected_action == EvaluationAction.ANSWER
            and normalized_answer
            and leaked
        ):
            answer_leaks.append(row.case_id)
    if answer_leaks:
        raise CorrectedDevelopmentBuildError(
            f"corrected questions leak canonical answers: {answer_leaks[:3]}"
        )

    control_cluster_ids = {
        row.cluster_id for row in sorted(clusters, key=lambda value: value.cluster_id)[:20]
    }
    control_cases = [
        row for row in ordered_cases if row.cluster_id in control_cluster_ids
    ]
    control_ids = {row.case_id for row in control_cases}
    control_gold = [row for row in ordered_gold if row.case_id in control_ids]
    if len(control_cases) != 100 or len(control_gold) != 100:
        raise CorrectedDevelopmentBuildError("corrected control subset drifted")

    source_hash = source_plan["content_sha256"]
    packages = {
        "cases": _package(
            rows_key="cases",
            rows=[row.model_dump(mode="json") for row in ordered_cases],
            split="development",
            source_plan_sha256=source_hash,
        ),
        "gold": _package(
            rows_key="gold",
            rows=[row.model_dump(mode="json") for row in ordered_gold],
            split="development-gold",
            source_plan_sha256=source_hash,
        ),
        "control_cases": _package(
            rows_key="cases",
            rows=[row.model_dump(mode="json") for row in control_cases],
            split="development-control",
            source_plan_sha256=source_hash,
        ),
        "control_gold": _package(
            rows_key="gold",
            rows=[row.model_dump(mode="json") for row in control_gold],
            split="development-control-gold",
            source_plan_sha256=source_hash,
        ),
    }
    second = {
        key: canonical_json_sha256(
            {field: value for field, value in package.items() if field != "content_sha256"}
        )
        for key, package in packages.items()
    }
    if any(packages[key]["content_sha256"] != value for key, value in second.items()):
        raise CorrectedDevelopmentBuildError("corrected package is not byte stable")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "source_plan_sha256": source_hash,
        "case_count": len(ordered_cases),
        "control_case_count": len(control_cases),
        "answerable_count": len(answerable),
        "boundary_count": len(boundary),
        "normalized_duplicate_count": 0,
        "canonical_answer_leak_count": 0,
        "course_distribution": dict(
            sorted(Counter(row.course_id for row in ordered_cases).items())
        ),
        "slice_distribution": dict(
            sorted(Counter(row.slice for row in ordered_cases).items())
        ),
        "provider_calls": 0,
        "private_data_used": False,
        "final_cases_constructed": 0,
        "packages": packages,
        "source_plan": source_plan,
    }


def _exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise CorrectedDevelopmentBuildError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_packages() -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
    result = build_packages()
    paths = {
        "source_plan": SOURCE_PLAN_PATH,
        "cases": DEVELOPMENT_CASES_PATH,
        "gold": DEVELOPMENT_GOLD_PATH,
        "control_cases": DEVELOPMENT_CONTROL_CASES_PATH,
        "control_gold": DEVELOPMENT_CONTROL_GOLD_PATH,
    }
    if any(path.exists() for path in paths.values()):
        raise CorrectedDevelopmentBuildError("corrected exclusive output is already used")
    _exclusive_json(SOURCE_PLAN_PATH, result["source_plan"])
    for key in ("cases", "gold", "control_cases", "control_gold"):
        _exclusive_json(paths[key], result["packages"][key])
    return {
        **{
            key: value
            for key, value in result.items()
            if key not in {"packages", "source_plan"}
        },
        "status": "completed-build-only",
        "outputs": {
            key: str(path.relative_to(ROOT)) for key, path in paths.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--write-development", action="store_true")
    arguments = parser.parse_args()
    if arguments.write_development:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
        result = write_packages()
    else:
        result = build_packages()
    if not arguments.write_development:
        result = {
            key: value
            for key, value in result.items()
            if key not in {"packages", "source_plan"}
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
