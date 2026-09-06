"""Regression for an answer key that inferred sufficiency from necessity."""

import copy
import hashlib
import json

from scripts.build_main_oracle_alignment import (
    ORIGINAL,
    PROCEDURES,
    build_packets,
    countermodels,
)
from scripts.run_paired_pedagogy_development import normalized_packet, validate_packet


def packets():
    raw = ORIGINAL.read_bytes()
    original = json.loads(raw)
    return original, build_packets(original, hashlib.sha256(raw).hexdigest())


def test_positive_action_gold_has_a_countermodel_until_procedure_is_explicit():
    # Sufficient funds without a redemption is allowed by the old Topaz source.
    assert countermodels(complete_procedure=False) == [
        {"condition": True, "action": False}
    ]
    assert countermodels(complete_procedure=True) == []


def test_correction_preserves_old_packet_and_context_purposes_with_versioned_spans():
    raw = ORIGINAL.read_bytes()
    original = json.loads(raw)
    untouched = copy.deepcopy(original)
    corrected, constraints = build_packets(original, hashlib.sha256(raw).hexdigest())
    assert corrected["version"] == 3 and len(corrected["contexts"]) == 48
    old_sources = {s["source_id"]: s for s in original["sources"]}
    new_sources = {s["source_id"]: s for s in corrected["sources"]}
    for old, new in zip(original["contexts"], corrected["contexts"], strict=True):
        assert (new["id"], new["category"], new["course_id"]) == (
            old["id"],
            old["category"],
            old["course_id"],
        )
        assert new["public"]["profile_values"] == old["public"]["profile_values"]
        assert new["public"]["target_turn_index"] == old["public"]["target_turn_index"]
        assert len(new["public"]["student_turns"]) == len(
            old["public"]["student_turns"]
        )
        assert new["gold"]["required_meanings"] == old["gold"]["required_meanings"]
        for span in new["gold"]["support_spans"]:
            source = new_sources[span["source_id"]]
            assert source["version"] == span["version"]
            assert source["text"][span["start"] : span["end"]] == span["quote"]
        for turn in new["public"]["student_turns"]:
            if (
                turn["content"].startswith("My attempt")
                and "Is this correct?" in turn["content"]
            ):
                primary = next(
                    s
                    for s in corrected["sources"]
                    if s["course_id"] == new["course_id"]
                    and s["source_id"] in PROCEDURES
                )
                assert primary["text"] in turn["content"]
    for source_id, source in new_sources.items():
        assert source["version"] == old_sources[source_id]["version"] + (
            source_id in PROCEDURES
        )
    assert original == untouched
    assert constraints["sources"] == [old_sources[s] for s in PROCEDURES]


def test_gold_and_formal_annotations_never_reach_runtime_and_comparison_remains_balanced():
    _, (corrected, constraints) = packets()
    assert len(constraints["contexts"]) == 8
    assert (
        sum(
            c["category"] == "necessary-not-sufficient" for c in constraints["contexts"]
        )
        == 4
    )
    for packet in (corrected, constraints):
        packet = copy.deepcopy(packet)
        for case in packet["contexts"]:
            case["gold"]["secret_marker"] = "DO_NOT_EXPOSE_ORACLE"
        runtime = validate_packet(normalized_packet(packet))
        assert "DO_NOT_EXPOSE_ORACLE" not in json.dumps(runtime)
        assert "formal_audit" not in runtime
        for case in runtime["cases"]:
            assert set(case) == {
                "id",
                "split",
                "category",
                "target_turn_index",
                "profile",
                "prompts",
                "cards",
            }
