#!/usr/bin/env python3
"""Prepare private human-review packets for course-tutor v1.2 authoring."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/processed/course_tutor_v1/review_v1_2"
DEFAULT_OUTPUT = ROOT / "reports/generated/course-tutor-v1.2-authoring-review"
EVIDENCE_ROOT = ROOT / "data/interim/course_tutor_v1/evidence"
CHECKS = (
    "question_authentic_and_synthetic",
    "expected_behavior_correct",
    "claims_atomic_and_correct",
    "evidence_supports_claims",
    "permission_and_version_correct",
    "split_assignment_acceptable",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_text_exclusive(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(value)
    except FileExistsError as error:
        raise ValueError(f"refusing to overwrite review artifact: {path}") from error


def _render_case(case: dict[str, Any], index: int) -> list[str]:
    expected = case["ground_truth"]["expected_behavior"]
    lines = [
        f"## {index}. {case['case_id']}",
        "",
        f"- Scenario: `{case['scenario_type']}`",
        f"- Topic: `{case['topic_stratum']}`",
        f"- Difficulty: `{case['difficulty']}` — {case['difficulty_rationale']}",
        f"- Corpus answerability: `{case['ground_truth']['corpus_answerability']}`",
        f"- Student question: {case['student_input']['question']}",
        f"- Expected primary action: `{expected['primary_action']}`",
        f"- Acceptable alternatives: {', '.join(expected['acceptable_alternatives']) or 'none'}",
        f"- Forbidden actions: {', '.join(expected['forbidden_actions']) or 'none'}",
        f"- Allowed support: `{expected['allowed_support_level']}`",
        f"- Required tutoring moves: {', '.join(expected['required_tutoring_moves']) or 'none'}",
        f"- Citation requirement: `{expected['citation_requirement']}`",
        "",
        "### Required claims",
        "",
    ]
    claims = case["ground_truth"]["required_claims"]
    if claims:
        for claim in claims:
            lines.append(
                f"- `{claim['claim_id']}` ({claim['severity']}): "
                f"{claim['claim_text']} — evidence "
                f"{', '.join(claim['evidence_unit_ids'])}"
            )
    else:
        lines.append("- None; verify that the non-answer behavior is appropriate.")
    lines.extend(["", "### Evidence", ""])
    evidence = case["ground_truth"]["evidence_units"]
    if not evidence:
        lines.append("No authored evidence. Confirm that this is intentional.")
    for item in evidence:
        lines.extend(
            [
                f"#### {item['evidence_unit_id']} — {item['passage_id']}",
                "",
                f"- Source: `{item['source_artifact_id']}@{item['source_version']}`",
                f"- Locator: {item['locator']}",
                f"- Role/permission: `{item['role']}` / `{item['permission_status']}`",
                f"- Supports: {', '.join(item['supports_claim_ids']) or 'none'}",
                f"- SHA-256: `{item['content_sha256']}`",
                "",
                (EVIDENCE_ROOT / f"{item['passage_id']}.txt").read_text(
                    encoding="utf-8"
                ).strip(),
                "",
            ]
        )
    lines.extend(
        [
            "### Review checklist",
            "",
            *[f"- [ ] {check.replace('_', ' ')}" for check in CHECKS],
            "- [ ] Set this case's decision and notes in `review_template.json`.",
            "",
        ]
    )
    return lines


def prepare(input_root: Path, output_root: Path) -> dict[str, Any]:
    manifest = load_json(input_root / "review_manifest.json")
    split_templates: dict[str, Any] = {}
    packet_paths: dict[str, str] = {}
    for split in ("development", "heldout"):
        dataset = load_json(input_root / f"{split}.json")
        expected_hash = manifest["splits"][split]["dataset_sha256"]
        actual_hash = hashlib.sha256(
            (input_root / f"{split}.json").read_bytes()
        ).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"{split} review draft hash drifted")
        lines = [
            f"# Course-tutor v1.2 {split} authoring review",
            "",
            "This is private course material. Do not commit or share this packet.",
            "Review each case against the exact evidence shown. Do not run or inspect model outputs while authoring-reviewing the held-out split.",
            "Approve only when all six checks pass. Mark any uncertain or incorrect case `revise` and explain why.",
            "",
        ]
        decisions = []
        for index, case in enumerate(dataset["cases"], start=1):
            lines.extend(_render_case(case, index))
            decisions.append(
                {
                    "case_id": case["case_id"],
                    **{check: None for check in CHECKS},
                    "decision": None,
                    "notes": "",
                }
            )
        packet_path = output_root / f"{split}_packet.md"
        write_text_exclusive(packet_path, "\n".join(lines) + "\n")
        packet_paths[split] = str(packet_path)
        split_templates[split] = {"case_decisions": decisions}

    template = {
        "schema_version": "1.0.0-draft",
        "review_id": "course-tutor-v1.2-authoring-review-001",
        "status": "draft",
        "reviewed_at": None,
        "reviewer": {
            "reviewer_id": None,
            "role": None,
            "human_review": True,
            "codex_assisted": False,
        },
        "draft_hashes": manifest["splits"],
        "splits": split_templates,
    }
    template_path = output_root / "review_template.json"
    write_text_exclusive(
        template_path,
        f"{json.dumps(template, indent=2, ensure_ascii=False)}\n",
    )
    return {
        "review_id": template["review_id"],
        "development_cases": len(
            split_templates["development"]["case_decisions"]
        ),
        "heldout_cases": len(split_templates["heldout"]["case_decisions"]),
        "packets": packet_paths,
        "template": str(template_path),
        "seal_created": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.input_root, arguments.output_root), indent=2))


if __name__ == "__main__":
    main()
