from scripts.triage_factual_qa_v3_semantic_roles import triage


def record(
    source_id: str,
    eligibility: str,
    reason: str,
    format_group: str = "pdf",
    course_id: str = "COURSE",
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "sha256": source_id,
        "inventory_eligibility": eligibility,
        "disposition_reason": reason,
        "format_group": format_group,
        "course_id": course_id,
        "source_role": "review_or_conversion_required",
        "requires_explicit_review": True,
    }


def test_triage_promotes_only_approved_hashes_and_keeps_path_labels_provisional() -> None:
    manifest = {
        "manifest_sha256": "conversion",
        "source_root": "/private",
        "dispositions": [
            record("approved", "review_required", "assessment-like path requires content review"),
            record("candidate", "eligible_candidate", "content role and conversion readiness require explicit review"),
            record("code", "review_required", "assessment-like path requires content review", "code"),
            record("text", "review_required", "assessment-like path requires content review", "text"),
        ],
    }

    private, summary = triage(manifest, {"approved"})
    by_id = {item["source_id"]: item for item in private["dispositions"]}

    assert by_id["approved"]["source_role"] == "authoritative_evidence"
    assert by_id["candidate"]["source_role"] == "review_or_conversion_required"
    assert by_id["candidate"]["requires_explicit_review"] is True
    assert by_id["code"]["source_role"] == "review_or_conversion_required"
    assert by_id["code"]["requires_explicit_review"] is True
    assert by_id["text"]["requires_explicit_review"] is True
    assert summary["unresolved_review_count"] == 3
    assert summary["semantic_role_gate"] is False
    assert summary["content_eligibility_complete"] is False
    assert summary["path_or_format_only_labels_are_final"] is False
