from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from scripts import build_whole_system_architecture_tranches as builder
from src.digital_twin.evaluation.architecture_evolution import (
    ArchitectureDevelopmentFreezeV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question


def test_builds_three_distinct_development_folds() -> None:
    freeze, outputs = builder.build()

    validated = ArchitectureDevelopmentFreezeV1.model_validate(freeze)
    assert [row.case_count for row in validated.tranches] == [495, 497, 481]
    assert [len(row.removed_duplicate_case_ids) for row in validated.tranches] == [
        5,
        3,
        19,
    ]
    assert len(outputs) == 7


def test_public_questions_are_unique_across_all_rounds() -> None:
    _, outputs = builder.build()
    questions: list[str] = []
    for round_number in (1, 2, 3):
        package = outputs[builder.OUTPUT_ROOT / f"round-{round_number}-cases.json"]
        questions.extend(normalize_question(row["question"]) for row in package["rows"])

    assert len(questions) == len(set(questions))


def test_public_packages_never_contain_hidden_gold_fields() -> None:
    _, outputs = builder.build()
    forbidden = {
        "expected_action",
        "canonical_answer",
        "claims",
        "boundary_reason",
    }
    for round_number in (1, 2, 3):
        package = outputs[builder.OUTPUT_ROOT / f"round-{round_number}-cases.json"]
        assert all(not (forbidden & set(row)) for row in package["rows"])


def test_source_ranges_are_disjoint_between_rounds() -> None:
    freeze, _ = builder.build()
    ranges: list[list[tuple[str, int, int, int]]] = []
    for tranche in freeze["tranches"]:
        source = json.loads((builder.ROOT / tranche["source"]["path"]).read_text())
        current = builder._range_rows(source)
        assert all(not builder._ranges_overlap(current, prior) for prior in ranges)
        ranges.append(current)


def test_freeze_rejects_reordered_rounds() -> None:
    freeze, _ = builder.build()
    freeze["tranches"] = list(reversed(freeze["tranches"]))

    with pytest.raises(ValidationError, match="exactly rounds 1, 2, and 3"):
        ArchitectureDevelopmentFreezeV1.model_validate(freeze)
