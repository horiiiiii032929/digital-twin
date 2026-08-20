"""Render the frozen held-out second-review sample as a local Markdown packet."""

from __future__ import annotations

import json
from pathlib import Path

from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "research/05_evaluation/generator_qualification_v1_heldout.json"
RUN = ROOT / "reports/generated/generator-qualification-v1-heldout-001.json"
JUDGMENT = (
    ROOT
    / "research/05_evaluation/judgments/generator-qualification-v1-heldout-001-first-review.json"
)
OUTPUT = (
    ROOT / "reports/generated/generator-qualification-v1-heldout-001-second-review.md"
)
SECOND_REVIEW = (
    ROOT
    / "research/05_evaluation/judgments/generator-qualification-v1-heldout-001-second-review.json"
)


def main() -> None:
    require_pre_evaluation_operation_allowed("dataset_generation")
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    run = json.loads(RUN.read_text(encoding="utf-8"))
    judgment = json.loads(JUDGMENT.read_text(encoding="utf-8"))
    second_review = (
        json.loads(SECOND_REVIEW.read_text(encoding="utf-8"))
        if SECOND_REVIEW.exists()
        else None
    )
    sample_ids = judgment["second_review"]["case_ids"]
    second_by_id = {
        item["case_id"]: item
        for item in (second_review or {}).get("case_judgments", [])
    }
    cases = {case["case_id"]: case for case in dataset["cases"]}
    results = {result["case_id"]: result for result in run["results"]}

    lines = [
        "# Generator qualification held-out second-review packet",
        "",
        "Reviewer: "
        + (
            second_review["reviewer_boundary"]
            if second_review
            else "____________________"
        ),
        "",
        "Review date: "
        + (second_review["reviewed_at"] if second_review else "____________________"),
        "",
        "For each case, compare the response with only the presented evidence. "
        "Mark PASS only when the required claim is retained, every factual claim "
        "is supported, and the citations identify the supporting sources.",
        "",
    ]
    for index, case_id in enumerate(sample_ids, start=1):
        case = cases[case_id]
        result = results[case_id]
        reviewed_case = second_by_id.get(case_id)
        passed = reviewed_case is not None and reviewed_case["decision"] == "pass"
        lines.extend(
            [
                f"## {index}. {case_id} — {case['scenario_type']}",
                "",
                f"Question: {case['question']}",
                "",
                "Presented evidence:",
                "",
            ]
        )
        for evidence in case["candidate_evidence"]:
            if evidence["presented"]:
                lines.append(f"- `{evidence['source_id']}`: {evidence['text']}")
        lines.extend(
            [
                "",
                f"Response: {result['answer']}",
                "",
                "Citations: " + (", ".join(result["citation_sources"]) or "none"),
                "",
                "- [x] PASS" if passed else "- [ ] PASS",
                "- [ ] FAIL — required claim recall",
                "- [ ] FAIL — unsupported claim or citation correctness",
                "- [ ] FAIL — citation completeness",
                "- [ ] FAIL — other action/policy issue",
                "",
                "Notes: "
                + (
                    reviewed_case.get("note", "No issue found.")
                    if reviewed_case
                    else "________________________________________________"
                ),
                "",
            ]
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
