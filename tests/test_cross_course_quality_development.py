import copy
import json

import pytest

from scripts.cross_course_quality_development import (
    PACKET, public_case, score_case, validate_packet, wilson_interval,
)


@pytest.fixture
def packet():
    return json.loads(PACKET.read_text())


def supported_response(case):
    return {"action": "answer", "text": " ".join(s["quote"] for s in case["gold"]["requirements"]),
            "citations": [{**s, "version": 1} for s in case["gold"]["requirements"]]}


def test_packet_coverage_and_public_gold_separation(packet):
    validate_packet(packet)
    assert len(packet["cases"]) == 44
    assert len({s["course_id"] for s in packet["sources"]}) == 4
    for case in packet["cases"]:
        public = public_case(packet, case["public"]["case_id"])
        assert "gold" not in public and "requirements" not in public
        assert len(public["sources"]) == 2
        assert all(s["course_id"] == public["course_id"] for s in public["sources"])


def test_missing_second_source_does_not_pass_multisource(packet):
    case = next(c for c in packet["cases"] if c["public"]["case_id"] == "scheduler-multi-source")
    response = supported_response(case)
    assert score_case(packet, "scheduler-multi-source", response)["mechanical_pass"]
    response["citations"].pop()
    assert "required-citation-missing" in score_case(packet, "scheduler-multi-source", response)["violations"]


@pytest.mark.parametrize("change", ["foreign-source", "wrong-version", "negative-offset", "wrong-quote"])
def test_citation_corruption_is_rejected(packet, change):
    case = packet["cases"][0]
    response = supported_response(case)
    citation = response["citations"][0]
    if change == "foreign-source": citation["source_id"] = "ledger-1"
    if change == "wrong-version": citation["version"] = 2
    if change == "negative-offset": citation["start"] = -1
    if change == "wrong-quote": citation["quote"] = "fabricated quote"
    assert "citation-lineage" in score_case(packet, case["public"]["case_id"], response)["violations"]


def test_valid_citation_cannot_turn_missing_detail_into_answer(packet):
    response = supported_response(packet["cases"][0])
    result = score_case(packet, "scheduler-missing-detail", response)
    assert "action" in result["violations"]


def test_socratic_solution_leak_detected_even_with_question_action(packet):
    case = next(c for c in packet["cases"] if c["public"]["case_id"] == "scheduler-socratic")
    response = {"action": "diagnostic-question", "text": case["gold"]["forbidden_solution_spans"][0]["quote"], "citations": []}
    assert "premature-solution" in score_case(packet, "scheduler-socratic", response)["violations"]


def test_oracle_explicitly_does_not_claim_semantic_verification(packet):
    response = supported_response(packet["cases"][0])
    response["text"] += " This also cures every disease."
    result = score_case(packet, "scheduler-paraphrase", response)
    assert result["mechanical_pass"]  # Documented blind spot, not a quality pass.
    assert result["semantic_review"] == "required-not-performed"


def test_gold_span_corruption_fails_validation(packet):
    corrupt = copy.deepcopy(packet)
    corrupt["cases"][0]["gold"]["requirements"][0]["end"] -= 1
    with pytest.raises(ValueError, match="invalid source span"):
        validate_packet(corrupt)


def test_interval_does_not_treat_zero_failures_as_certain():
    lower, upper = wilson_interval(200, 200)
    assert 0.98 < lower < 1
    assert upper == pytest.approx(1)
    assert wilson_interval(380, 400)[0] < 0.95


def test_malformed_response_is_failed_instead_of_crashing(packet):
    result = score_case(packet, "scheduler-paraphrase", {"text": None, "citations": [None]})
    assert "empty-response" in result["violations"]
    assert "citation-schema" in result["violations"]
