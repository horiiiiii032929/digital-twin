from scripts.finalize_factual_qa_v3_conversion import finalize


def test_finalize_resolves_ocr_empty_and_redundant_archive() -> None:
    dispositions = {
        "manifest_id": "v3",
        "source_root": "/private",
        "dispositions": [
            {"source_id": "ocr", "format_group": "pdf", "source_role": "review_or_conversion_required", "requires_explicit_review": True},
            {"source_id": "empty", "format_group": "text", "source_role": "review_or_conversion_required", "requires_explicit_review": True},
            {"source_id": "zip", "format_group": "archive", "source_role": "review_or_conversion_required", "requires_explicit_review": True},
        ],
    }
    readiness = {
        "record_sha256": "readiness",
        "records": [
            {"source_id": "ocr", "conversion_status": "needs_ocr"},
            {"source_id": "empty", "conversion_status": "empty_source"},
            {"source_id": "zip", "conversion_status": "unsupported_format"},
        ],
    }
    ocr = {"record_sha256": "ocr-sha", "records": [{"source_id": "ocr", "status": "ocr_ready"}]}
    archive = {
        "record_sha256": "archive-sha",
        "entries": [{"source_role": "excluded_duplicate_generated_tool_state"}],
    }

    private, summary = finalize(dispositions, readiness, ocr, archive)

    assert summary["conversion_gate"] is True
    assert summary["semantic_role_review_count"] == 1
    assert private["dispositions"][0]["conversion_status"] == "ready_local_ocr"
    assert private["dispositions"][1]["requires_explicit_review"] is False
    assert private["dispositions"][2]["requires_explicit_review"] is False
