import json

import pytest

from scripts.cross_course_quality_development import PACKET, public_case
from scripts.run_cross_course_quality_development import run, score_product_response, source_bindings


def test_product_provenance_does_not_claim_exact_spans():
    packet = json.loads(PACKET.read_text())
    case = packet["cases"][0]
    public = public_case(packet, case["public"]["case_id"])
    bindings = source_bindings(public)
    b = bindings[0]
    response = {"action": "answer", "text": case["gold"]["requirements"][0]["quote"],
        "citations": [{"course_id": "c", "release_id": "r", "source_artifact_id": b["runtime_source_id"],
            "source_document_id": b["runtime_document_id"], "source_version": b["version"],
            "source_checksum": b["checksum"], "locator": b["locator"]}]}
    result = score_product_response(public, case["gold"], response, bindings, course_id="c", release_id="r")
    assert result["mechanical_source_containment_pass"]
    assert result["claim_specific_span_score"] is None
    response["citations"][0]["release_id"] = "another-release"
    assert "citation-lineage" in score_product_response(public, case["gold"], response, bindings,
        course_id="c", release_id="r")["violations"]


@pytest.mark.asyncio
async def test_all_88_product_cases_complete_without_external_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    output = tmp_path / "contract"
    summary = await run(output, contract=True)
    assert summary["cases"] == 88
    assert summary["errors"] == 0
    assert summary["actual_external_attempts"] == 0
    assert summary["semantic_quality_pass"] is None
    assert not summary["release_qualified"]
    rows = [json.loads(r) for r in (output / "responses.jsonl").read_text().splitlines()]
    profiles = [r for r in rows if r["kind"] in {"socratic", "explanatory"}]
    assert all(len(r["history"]) == 2 for r in profiles)
    assert all("gold" not in r["public_input"] for r in rows)
    assert summary["provider_ledger_attempts"] <= 500
    with pytest.raises(FileExistsError):
        await run(output, contract=True)
