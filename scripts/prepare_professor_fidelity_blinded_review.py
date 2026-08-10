#!/usr/bin/env python3
"""Prepare a condition-blinded private review packet and response template."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from scripts.execute_professor_fidelity import _load_course_chunks


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "experiments/runs/professor_fidelity_v1/anchor/result.json"
DEFAULT_DATASET = ROOT / "data/processed/course_tutor_v1/sealed_v1/anchor.json"
DEFAULT_OUTPUT = ROOT / "reports/generated/professor-fidelity-anchor-blinded-review-v2"
CONDITIONS = ("C0", "C1", "C2", "C3")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text_exclusive(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(value)
    except FileExistsError as error:
        raise ValueError(f"refusing to overwrite review artifact: {path}") from error


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    write_text_exclusive(path, f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")


def _mapping(case_id: str) -> dict[str, str]:
    conditions = list(CONDITIONS)
    rng = random.Random(f"5002:{case_id}:human-review")
    rng.shuffle(conditions)
    return dict(zip(("A", "B", "C", "D"), conditions, strict=True))


def prepare_packet(
    run_path: Path,
    dataset_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    run = load_json(run_path)
    dataset = load_json(dataset_path)
    if sha256(dataset_path) != run["dataset_sha256"]:
        raise ValueError("dataset hash does not match source run")
    cases = {case["case_id"]: case for case in dataset["cases"]}
    rows: dict[str, dict[str, dict[str, Any]]] = {}
    for row in run["results"]:
        rows.setdefault(row["case_id"], {})[row["condition"]] = row
    if set(rows) != set(cases):
        raise ValueError("run and dataset case IDs do not match")
    chunks = {chunk.id: chunk.text for chunk in _load_course_chunks()}
    for case in dataset["cases"]:
        for evidence in case["ground_truth"]["evidence_units"]:
            if evidence["permission_status"] != "approved":
                continue
            evidence_path = (
                ROOT
                / "data/interim/course_tutor_v1/evidence"
                / f"{evidence['passage_id']}.txt"
            )
            chunks[f"{case['case_id']}-{evidence['evidence_unit_id']}"] = (
                evidence_path.read_text(encoding="utf-8").strip()
            )

    mapping_records = []
    template_records = []
    packet = [
        "# Professor-fidelity blinded review packet",
        "",
        "Do not open `mapping.json` while reviewing. Conditions, model names, and provider names are intentionally hidden.",
        "",
        "For every response, judge semantic claim expression, support precision, citation alignment, citation completeness, presented-evidence completeness, and each listed pedagogical dimension. Use only the supplied authored gold evidence and presented context.",
        "",
    ]
    for case_index, case_id in enumerate(sorted(cases), start=1):
        case = cases[case_id]
        mapping = _mapping(case_id)
        if set(rows[case_id]) != set(CONDITIONS):
            raise ValueError(f"incomplete condition portfolio: {case_id}")
        packet.extend(
            [
                f"## Case {case_index}: {case_id}",
                "",
                f"Scenario: {case['scenario_type']}",
                "",
                f"Question: {case['student_input']['question']}",
                "",
                "Expected behavior:",
                "",
                f"- Primary action: {case['ground_truth']['expected_behavior']['primary_action']}",
                f"- Required moves: {', '.join(case['ground_truth']['expected_behavior']['required_tutoring_moves'])}",
                f"- Forbidden actions: {', '.join(case['ground_truth']['expected_behavior']['forbidden_actions'])}",
                "",
                "Required claims:",
                "",
            ]
        )
        claims = case["ground_truth"]["required_claims"]
        if claims:
            packet.extend(f"- `{claim['claim_id']}`: {claim['claim_text']}" for claim in claims)
        else:
            packet.append("- None; evaluate the required non-answer behavior.")
        packet.extend(["", "Authored gold evidence:", ""])
        approved = [
            item
            for item in case["ground_truth"]["evidence_units"]
            if item["permission_status"] == "approved"
        ]
        if approved:
            for item in approved:
                evidence_path = (
                    ROOT
                    / "data/interim/course_tutor_v1/evidence"
                    / f"{item['passage_id']}.txt"
                )
                packet.extend(
                    [
                        f"### Gold {item['evidence_unit_id']} — {item['locator']}",
                        "",
                        evidence_path.read_text(encoding="utf-8").strip(),
                        "",
                    ]
                )
        else:
            packet.extend(["No approved answer evidence.", ""])

        for response_label, condition in mapping.items():
            row = rows[case_id][condition]
            task_id = f"review-{case_id}-{response_label.lower()}"
            mapping_records.append(
                {
                    "task_id": task_id,
                    "case_id": case_id,
                    "response_label": response_label,
                    "condition": condition,
                }
            )
            template_records.append(
                {
                    "task_id": task_id,
                    "case_id": case_id,
                    "response_label": response_label,
                    "required_claim_expression": None,
                    "supported_claim_precision": None,
                    "citation_semantic_alignment": None,
                    "citation_completeness": None,
                    "presented_evidence_completeness": None,
                    "pedagogy_dimensions": [
                        {"dimension": dimension, "label": None}
                        for dimension in case["rubric"]["required_pedagogy_dimensions"]
                    ],
                }
            )
            packet.extend(
                [
                    f"### Response {response_label}",
                    "",
                    f"Action: {row['score']['actual_action']}",
                    "",
                    row["answer"],
                    "",
                    "Citations: " + (", ".join(row["citation_ids"]) or "none"),
                    "",
                    "Presented context:",
                    "",
                ]
            )
            if row["retrieved"]:
                for index, hit in enumerate(row["retrieved"], start=1):
                    packet.extend(
                        [
                            f"#### S{index} — {hit['source_id']} — {hit['locator']}",
                            "",
                            chunks.get(hit["chunk_id"], "[Context text unavailable; mark citation alignment unresolved.]"),
                            "",
                        ]
                    )
            else:
                packet.extend(["No context was presented.", ""])
            packet.extend(
                [
                    f"Complete `{task_id}` in `review_template.json`.",
                    "",
                ]
            )

    mapping = {
        "mapping_id": f"{run['run_id']}-blinded-review-mapping-v1",
        "source_run_id": run["run_id"],
        "dataset_sha256": run["dataset_sha256"],
        "seed": 5002,
        "assignments": mapping_records,
    }
    template = {
        "schema_version": "1.0.0-draft",
        "review_id": f"{run['run_id']}-blinded-review-001",
        "source_run_id": run["run_id"],
        "dataset_sha256": run["dataset_sha256"],
        "status": "draft",
        "reviewed_at": None,
        "reviewer": {
            "reviewer_id": None,
            "role": None,
            "blinded_to_conditions": True,
            "independent_human_review": None,
        },
        "judgments": template_records,
    }
    write_text_exclusive(output_root / "packet.md", "\n".join(packet) + "\n")
    write_json_exclusive(output_root / "review_template.json", template)
    write_json_exclusive(output_root / "mapping.json", mapping)
    return {
        "source_run_id": run["run_id"],
        "case_count": len(cases),
        "response_count": len(template_records),
        "packet": str(output_root / "packet.md"),
        "template": str(output_root / "review_template.json"),
        "mapping": str(output_root / "mapping.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    print(
        json.dumps(
            prepare_packet(arguments.run, arguments.dataset, arguments.output_root),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
