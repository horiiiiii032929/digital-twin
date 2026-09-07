"""Development schema tests; confirmation is checked by sealed bytes, never parsed."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/05_evaluation/datasets"


def development():
    return json.loads(
        (DATA / "meaningful-continuation-development-v2.json").read_text()
    )


def test_balanced_distinct_development_contexts():
    packet = development()
    assert len(packet["contexts"]) == 48
    assert len({c["id"] for c in packet["contexts"]}) == 48
    courses = {s["course_id"] for s in packet["sources"]}
    assert len(courses) == 4
    assert all(
        len([c for c in packet["contexts"] if c["course_id"] == course]) == 12
        for course in courses
    )
    assert all(
        len({c["category"] for c in packet["contexts"] if c["course_id"] == course})
        == 12
        for course in courses
    )


def test_explicit_gold_spans_and_target_are_bound():
    packet = development()
    sources = {s["source_id"]: s for s in packet["sources"]}
    for case in packet["contexts"]:
        public = case["public"]
        assert public["target_turn_index"] == len(public["student_turns"]) - 1
        assert set(public) == {"profile_values", "student_turns", "target_turn_index"}
        assert case["gold"]["required_meanings"]
        for span in case["gold"]["support_spans"]:
            source = sources[span["source_id"]]
            assert source["course_id"] == case["course_id"]
            assert source["version"] == span["version"]
            assert source["text"][span["start"] : span["end"]] == span["quote"]


def test_real_topic_change_and_attempt_history_are_present():
    packet = development()
    for case in packet["contexts"]:
        turns = [t["content"] for t in case["public"]["student_turns"]]
        if case["category"] == "topic-switch":
            assert len(turns) == 3 and turns[2].startswith("New topic:")
            labels = [
                s["label"]
                for s in packet["sources"]
                if s["course_id"] == case["course_id"]
            ]
            assert labels[0] in turns[1] and labels[1] not in turns[1]
            assert labels[1] in turns[2]
        if case["category"] in {
            "correct-attempt",
            "incorrect-attempt",
            "stuck-application",
            "repeated-stuck",
        }:
            assert turns[1].startswith("My attempt")


def test_confirmation_seal_without_reading_or_parsing_its_cases():
    seal = json.loads(
        (DATA / "meaningful-continuation-confirmation-v2-seal.json").read_text()
    )
    assert not seal["executed"] and not seal["candidate_runtime_exposure"]
    assert seal["contexts"] == 48 and seal["source_clusters"] == 4
    assert (
        hashlib.sha256((ROOT / seal["path"]).read_bytes()).hexdigest() == seal["sha256"]
    )


def test_anchors_separate_labels_and_cover_key_semantic_failures():
    anchors = json.loads(
        (DATA / "meaningful-continuation-calibration-anchors-v2.json").read_text()
    )["cases"]
    assert len(anchors) == 16
    assert sum(c["gold"]["overall"] == "adequate" for c in anchors) == 8
    assert {c["gold"]["defect_axis"] for c in anchors if c["gold"]["defect_axis"]} == {
        "factual_support",
        "attempt_use",
        "teaching_move",
        "boundaries",
    }
    for c in anchors:
        assert not {"gold", "id", "source_context_id"} & set(c["payload"])


def test_every_development_profile_constructs_actual_product_model():
    from src.digital_twin.student.teaching_profile import new_teaching_profile

    for case in development()["contexts"]:
        profile = new_teaching_profile(
            course_id=case["course_id"],
            version=1,
            values=case["public"]["profile_values"],
        )
        assert profile.course_id == case["course_id"]
        assert len(profile.help_ladder) >= 2


def test_v1_setup_failure_remains_reproducible_without_weakening_product():
    import pytest
    from pydantic import ValidationError
    from src.digital_twin.student.teaching_profile import new_teaching_profile

    old = json.loads((DATA / "meaningful-continuation-development-v1.json").read_text())
    case = next(c for c in old["contexts"] if c["category"] == "explanation-first")
    with pytest.raises(ValidationError):
        new_teaching_profile(
            course_id=case["course_id"],
            version=1,
            values=case["public"]["profile_values"],
        )


def test_v2_preserves_sources_gold_and_initial_turn_expectations():
    old = json.loads((DATA / "meaningful-continuation-development-v1.json").read_text())
    new = development()
    assert old["sources"] == new["sources"]
    for before, after in zip(old["contexts"], new["contexts"], strict=True):
        assert before["gold"] == after["gold"]
        assert before["public"]["student_turns"] == after["public"]["student_turns"]
        a, b = before["public"]["profile_values"], after["public"]["profile_values"]
        assert all(a[k] == b[k] for k in a if k != "help_ladder")
        assert b["help_ladder"][: len(a["help_ladder"])] == a["help_ladder"]
