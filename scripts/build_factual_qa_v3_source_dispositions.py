#!/usr/bin/env python3
"""Build private v3 source dispositions and a sanitized aggregate summary."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = (
    ROOT / "data/interim/multimodal_retrieval_v1/source_inventory_v1.json"
)
DEFAULT_PRIVATE_OUTPUT = (
    ROOT / "data/interim/factual_qa_v3/source_dispositions_v2.json"
)
DEFAULT_SUMMARY_OUTPUT = (
    ROOT / "reports/generated/factual-qa-v3-source-dispositions-v2.json"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_inventory(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except FileNotFoundError as error:
        raise ValueError(f"missing private source inventory: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid private source inventory: {error}") from error
    require(isinstance(payload.get("sources"), list), "inventory sources must be a list")
    return payload


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def is_generated_metadata(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/").lower()
    parts = normalized.split("/")
    name = parts[-1]
    return (
        ".pytest_cache" in parts
        or name == ".ds_store"
        or name.endswith(".swp")
        or name.endswith(".bkp")
    )


def build_dispositions(inventory: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    sources = inventory["sources"]
    require(len(sources) > 0, "inventory cannot be empty")
    required = {
        "source_id",
        "relative_path",
        "sha256",
        "bytes",
        "course_id",
        "format_group",
        "eligibility",
        "eligibility_reason",
    }
    for source in sources:
        require(required <= set(source), "inventory source is missing required fields")

    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in sources:
        by_hash[source["sha256"]].append(source)

    canonical_by_hash: dict[str, str] = {}
    sensitive_hashes: set[str] = set()
    priority = {
        "eligible_candidate": 0,
        "review_required": 1,
        "excluded_generated": 2,
        "excluded_sensitive": 3,
    }
    for content_hash, group in by_hash.items():
        if any(item["eligibility"] == "excluded_sensitive" for item in group):
            sensitive_hashes.add(content_hash)
            continue
        canonical = min(
            group,
            key=lambda item: (priority[item["eligibility"]], item["relative_path"]),
        )
        canonical_by_hash[content_hash] = canonical["source_id"]

    dispositions: list[dict[str, Any]] = []
    for source in sorted(sources, key=lambda item: item["relative_path"]):
        content_hash = source["sha256"]
        canonical_source_id = canonical_by_hash.get(content_hash)
        if content_hash in sensitive_hashes:
            role = "excluded_integrity_or_privacy"
            reason = "sensitive-indicated content hash group"
        elif is_generated_metadata(source["relative_path"]):
            role = "excluded_duplicate_generated_tool_state"
            reason = "generated metadata or transient tool-state artifact"
        elif source["source_id"] != canonical_source_id:
            role = "excluded_duplicate_generated_tool_state"
            reason = "exact-content duplicate; canonical lineage retained"
        elif source["eligibility"] == "excluded_generated":
            role = "excluded_duplicate_generated_tool_state"
            reason = source["eligibility_reason"]
        else:
            role = "review_or_conversion_required"
            reason = (
                "content role and conversion readiness require explicit review"
                if source["eligibility"] == "eligible_candidate"
                else source["eligibility_reason"]
            )

        dispositions.append(
            {
                "source_id": source["source_id"],
                "relative_path": source["relative_path"],
                "sha256": content_hash,
                "bytes": source["bytes"],
                "course_id": source["course_id"],
                "format_group": source["format_group"],
                "inventory_eligibility": source["eligibility"],
                "source_role": role,
                "disposition_reason": reason,
                "canonical_source_id": canonical_source_id,
                "requires_explicit_review": role == "review_or_conversion_required",
            }
        )

    role_counts = Counter(item["source_role"] for item in dispositions)
    review_counts = Counter(
        item["inventory_eligibility"]
        for item in dispositions
        if item["requires_explicit_review"]
    )
    disposition_sha = _canonical_json_sha256(dispositions)
    now = datetime.now(UTC).isoformat()
    private_payload = {
        "schema_version": 1,
        "manifest_id": "factual-qa-v3-source-dispositions-v2",
        "generated_at": now,
        "source_inventory_id": inventory.get("inventory_id"),
        "source_inventory_sha256": inventory.get("inventory_sha256"),
        "source_root": inventory.get("source_root"),
        "disposition_sha256": disposition_sha,
        "dispositions": dispositions,
    }
    summary = {
        "schema_version": 1,
        "manifest_id": private_payload["manifest_id"],
        "generated_at": now,
        "source_inventory_id": inventory.get("inventory_id"),
        "source_inventory_sha256": inventory.get("inventory_sha256"),
        "disposition_sha256": disposition_sha,
        "source_count": len(dispositions),
        "unique_content_hashes": len(by_hash),
        "duplicate_file_count": len(dispositions) - len(by_hash),
        "source_role_counts": dict(sorted(role_counts.items())),
        "pending_review_by_inventory_class": dict(sorted(review_counts.items())),
        "complete_accounting_gate": len(dispositions) == len(sources),
        "release_ready_gate": role_counts["review_or_conversion_required"] == 0,
        "contains_private_paths": False,
        "contains_source_content": False,
        "external_provider_calls": 0,
        "model_calls": 0,
        "cost_usd": 0,
    }
    return private_payload, summary


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--private-output", type=Path, default=DEFAULT_PRIVATE_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    private_payload, summary = build_dispositions(load_inventory(args.inventory))
    write_json(args.private_output, private_payload)
    write_json(args.summary_output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
