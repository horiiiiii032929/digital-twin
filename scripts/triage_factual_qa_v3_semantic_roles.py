#!/usr/bin/env python3
"""Apply conservative provenance rules to factual-QA v3 semantic source roles."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/interim/factual_qa_v3/source_dispositions_v4.json"
PORTFOLIO = ROOT / "research/05_evaluation/cross_course_portfolio_v2.manifest.json"
PRIVATE_OUTPUT = ROOT / "data/interim/factual_qa_v3/source_roles_v2.json"
SUMMARY_OUTPUT = ROOT / "reports/generated/factual-qa-v3-source-roles-v2.json"


def approved_hashes(portfolio: dict[str, Any]) -> set[str]:
    return {
        document["sha256"]
        for course in portfolio["courses"]
        for document in course["documents"]
    }


def triage(
    manifest: dict[str, Any], approved: set[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for original in manifest["dispositions"]:
        record = dict(original)
        rule = "preserved_existing_disposition"
        if original["requires_explicit_review"]:
            if original["sha256"] in approved:
                record["source_role"] = "authoritative_evidence"
                record["requires_explicit_review"] = False
                rule = "approved_cross_course_portfolio_v2_hash"
            elif original["inventory_eligibility"] == "eligible_candidate":
                rule = "course_candidate_requires_content_review"
            elif (
                original["disposition_reason"]
                == "unsupported or extensionless format"
                and original["course_id"] != "unassigned"
            ):
                rule = "conversion_resolved_requires_content_review"
            elif original["disposition_reason"] == (
                "assessment-like path requires content review"
            ):
                rule = "assessment_candidate_requires_content_review"
            else:
                rule = "content_level_review_required"
        record["semantic_triage_rule"] = rule
        records.append(record)

    role_counts = Counter(record["source_role"] for record in records)
    rule_counts = Counter(record["semantic_triage_rule"] for record in records)
    unresolved_by_format = Counter(
        record["format_group"] for record in records if record["requires_explicit_review"]
    )
    record_sha = hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    now = datetime.now(UTC).isoformat()
    private = {
        "schema_version": 1,
        "manifest_id": "factual-qa-v3-source-roles-v2",
        "generated_at": now,
        "conversion_manifest_sha256": manifest["manifest_sha256"],
        "approved_portfolio_id": "cross-course-portfolio-v2",
        "record_sha256": record_sha,
        "source_root": manifest["source_root"],
        "dispositions": records,
    }
    summary = {
        "schema_version": 1,
        "manifest_id": private["manifest_id"],
        "generated_at": now,
        "conversion_manifest_sha256": manifest["manifest_sha256"],
        "record_sha256": record_sha,
        "source_count": len(records),
        "role_counts": dict(sorted(role_counts.items())),
        "triage_rule_counts": dict(sorted(rule_counts.items())),
        "unresolved_review_count": sum(unresolved_by_format.values()),
        "unresolved_by_format": dict(sorted(unresolved_by_format.items())),
        "semantic_role_gate": sum(unresolved_by_format.values()) == 0,
        "content_eligibility_complete": False,
        "path_or_format_only_labels_are_final": False,
        "contains_private_paths": False,
        "contains_source_content": False,
        "external_provider_calls": 0,
        "model_calls": 0,
        "cost_usd": 0,
    }
    return private, summary


def main() -> int:
    private, summary = triage(
        json.loads(MANIFEST.read_text()),
        approved_hashes(json.loads(PORTFOLIO.read_text())),
    )
    PRIVATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_OUTPUT.write_text(json.dumps(private, indent=2, sort_keys=True) + "\n")
    SUMMARY_OUTPUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
