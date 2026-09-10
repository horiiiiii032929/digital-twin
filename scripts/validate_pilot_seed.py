"""Validate the proposed synthetic seed pack; never load an application database."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.digital_twin.identity.models import IdentityProfile
from src.digital_twin.student.models import Account, Course, CourseMembership, StudentReleaseStatus
from src.digital_twin.tutor_policy import SourceInventoryItem

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "tests/fixtures/seed_data/pilot-v1"


def validate() -> dict[str, int | str]:
    manifest = json.loads((PACK / "manifest.json").read_text())
    if manifest["schema_version"] != 1 or manifest["synthetic"] is not True:
        raise ValueError("Expected version 1 synthetic pack")
    entities = {}
    for kind in ("accounts", "courses", "sources", "scenarios"):
        items = manifest[kind]
        indexed = {item["id"]: item for item in items}
        if len(indexed) != len(items):
            raise ValueError(f"Duplicate {kind} IDs")
        if any(not key.startswith(manifest["seed_id"] + "-") for key in indexed):
            raise ValueError(f"Unscoped {kind} ID")
        entities[kind] = indexed
    emails = set()
    for account in entities["accounts"].values():
        Account.model_validate(account)
        IdentityProfile.model_validate({**account, "account_id": account["id"]})
        email = account["email"].casefold()
        if not email.endswith("@example.test") or email in emails or account["role"] == "admin":
            raise ValueError("Demo identity collision, non-test email or administrator creation")
        emails.add(email)
    for course in entities["courses"].values():
        Course.model_validate(course)
        StudentReleaseStatus(course["target_release_status"])
        if entities["accounts"][course["owner_professor_id"]]["role"] != "professor":
            raise ValueError("Course owner must be a professor")
    memberships = set()
    for item in manifest["memberships"]:
        CourseMembership.model_validate(item)
        pair = (item["account_id"], item["course_id"])
        if pair in memberships or item["role"] != entities["accounts"][pair[0]]["role"]:
            raise ValueError("Duplicate membership or incompatible role")
        if pair[1] not in entities["courses"]:
            raise ValueError("Unknown membership course")
        memberships.add(pair)
    for source in entities["sources"].values():
        path = (PACK / source["path"]).resolve()
        if not path.is_relative_to((PACK / "sources").resolve()):
            raise ValueError("Source escapes the pack")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != source["sha256"]:
            raise ValueError("Source hash mismatch")
        item = SourceInventoryItem.model_validate({**source, "name": path.name, "size_bytes": len(content)})
        course = entities["courses"][source["course_id"]]
        if course["target_release_status"] == "published" and item.permission_status != "approved":
            raise ValueError("Unapproved source in a published-course candidate")
    for scenario in entities["scenarios"].values():
        if scenario["actor_id"] not in entities["accounts"] or scenario["course_id"] not in entities["courses"]:
            raise ValueError("Unknown scenario actor or course")
        for source_id in scenario["source_ids"]:
            if entities["sources"][source_id]["course_id"] != scenario["course_id"]:
                raise ValueError("Expected evidence crosses course boundaries")
    if any(manifest[key] for key in ("initial_conversations", "initial_learning_metrics", "initial_outreach")):
        raise ValueError("Seed must start without fabricated activity")
    if not (ROOT / manifest["release_profile_path"]).is_file():
        raise ValueError("Missing selected release profile")
    return {"status": "design-valid-not-loaded", **{key: len(value) for key, value in entities.items()}, "memberships": len(memberships)}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
