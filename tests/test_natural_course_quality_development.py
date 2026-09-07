import hashlib
import json

import pytest

from scripts.natural_course_quality_development import load_packet, run_packet, score_response


def response_for(source):
    return {"action": "answer", "text": source["text"], "citations": [{
        "course_id": "course", "release_id": "release",
        "source_artifact_id": source["source_id"],
        "source_document_id": "document-" + source["source_id"],
        "source_version": source["source_version"], "locator": source["locator"],
        "source_checksum": hashlib.sha256(source["text"].encode()).hexdigest(),
    }]}


def test_authored_packet_has_supported_spans_and_explicit_pending_review():
    packet = load_packet()
    assert len(packet["cases"]) == 16
    assert len(packet["sources"]) == 4
    assert "pending" in packet["review_status"]
    assert sum(c["kind"] == "answerable" for c in packet["cases"]) == 12


def test_independent_scoring_rejects_wrong_source_and_missing_explanation():
    packet = load_packet()
    case, source = packet["cases"][0], packet["sources"][0]
    response = response_for(source)
    def score():
        return score_response(case, source, response, course_id="course", release_id="release")
    assert score()["extractive_support_pass"]
    response["citations"][0]["source_artifact_id"] = "another-source"
    assert score()["failure_class"] == "citation-lineage"
    response = response_for(source)
    response["text"] = case["expected_spans"][0]["text"]
    assert score()["failure_class"] == "exact-span-coverage"


def test_boundary_does_not_pass_merely_because_there_are_no_citations():
    case = next(c for c in load_packet()["cases"] if c["id"] == "ncq-graded-work")
    response = {"text": "Here is the final answer.", "action": "answer", "citations": []}
    assert not score_response(case, None, response, course_id="c", release_id="r")["boundary_pass"]


@pytest.mark.asyncio
async def test_actual_runtime_baseline_emits_all_cases_without_network(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    output = tmp_path / "baseline"
    summary = await run_packet(output)
    rows = [json.loads(line) for line in (output / "responses.jsonl").read_text().splitlines()]
    assert len(rows) == summary["cases"] == 16
    assert summary["network_mode"] == "fake-client-no-network"
    assert summary["answerable_cases"] == 12
    assert summary["boundary_cases"] == 4
    assert all("text" in row and "citations" in row for row in rows)
    assert "not semantic quality" in summary["interpretation"]
