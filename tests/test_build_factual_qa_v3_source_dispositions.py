from __future__ import annotations

from scripts.build_factual_qa_v3_source_dispositions import (
    build_dispositions,
    is_generated_metadata,
)


def source(
    source_id: str,
    path: str,
    content_hash: str,
    eligibility: str,
    reason: str,
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "relative_path": path,
        "sha256": content_hash,
        "bytes": 10,
        "course_id": "COURSE1",
        "format_group": "pdf",
        "eligibility": eligibility,
        "eligibility_reason": reason,
    }


def test_dispositions_account_for_all_sources_and_preserve_duplicate_lineage() -> None:
    inventory = {
        "inventory_id": "fixture",
        "inventory_sha256": "inventory-hash",
        "source_root": "/private/root",
        "sources": [
            source("eligible", "course/lecture.pdf", "same", "eligible_candidate", "recognized"),
            source("generated", "course/cache.pdf", "same", "excluded_generated", "generated"),
            source("review", "course/final.pdf", "review", "review_required", "assessment-like"),
        ],
    }

    private, summary = build_dispositions(inventory)
    by_id = {item["source_id"]: item for item in private["dispositions"]}

    assert summary["source_count"] == 3
    assert summary["complete_accounting_gate"] is True
    assert summary["release_ready_gate"] is False
    assert by_id["eligible"]["source_role"] == "review_or_conversion_required"
    assert by_id["generated"]["source_role"] == "excluded_duplicate_generated_tool_state"
    assert by_id["generated"]["canonical_source_id"] == "eligible"
    assert summary["contains_private_paths"] is False


def test_sensitive_hash_taints_every_exact_copy() -> None:
    inventory = {
        "inventory_id": "fixture",
        "inventory_sha256": "inventory-hash",
        "source_root": "/private/root",
        "sources": [
            source("secret", ".env", "secret-hash", "excluded_sensitive", "secret"),
            source("copy", "course/config.txt", "secret-hash", "eligible_candidate", "recognized"),
        ],
    }

    private, summary = build_dispositions(inventory)

    assert {item["source_role"] for item in private["dispositions"]} == {
        "excluded_integrity_or_privacy"
    }
    assert summary["source_role_counts"] == {"excluded_integrity_or_privacy": 2}


def test_output_is_stable_for_input_order() -> None:
    sources = [
        source("b", "course/b.pdf", "b", "eligible_candidate", "recognized"),
        source("a", "course/a.pdf", "a", "review_required", "review"),
    ]
    first, first_summary = build_dispositions({"sources": sources})
    second, second_summary = build_dispositions({"sources": list(reversed(sources))})

    assert first["disposition_sha256"] == second["disposition_sha256"]
    assert first_summary["source_role_counts"] == second_summary["source_role_counts"]


def test_nested_and_extensionless_tool_metadata_is_excluded() -> None:
    assert is_generated_metadata("course/.DS_Store")
    assert is_generated_metadata("course/.pytest_cache/v/cache/nodeids")
    assert is_generated_metadata("course/report.swp")
    assert is_generated_metadata("course/old.bkp")
    assert not is_generated_metadata("course/lecture.md")
