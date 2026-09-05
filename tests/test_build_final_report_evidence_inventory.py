from pathlib import Path

from scripts.build_final_report_evidence_inventory import (
    classify_path,
    decision_class,
    markdown_link_targets,
    parse_registry,
    write_csv,
)


def test_classify_path_separates_evidence_roles() -> None:
    assert (
        classify_path("research/05_evaluation/records/example.json")
        == "machine-result-record"
    )
    assert (
        classify_path("research/05_evaluation/datasets/example.json")
        == "committed-evaluation-dataset"
    )
    assert classify_path("tests/test_example.py") == "automated-or-manual-verification"


def test_decision_class_preserves_invalid_and_no_release() -> None:
    assert decision_class("Invalid execution", "No quality result") == "invalid"
    assert decision_class("Completed Refine", "No Release") == "no-release"
    assert decision_class("Completed Keep", "Select candidate") == "keep"


def test_decision_class_uses_the_status_label_not_diagnostic_words() -> None:
    assert (
        decision_class(
            "Completed Keep: zero invalid citations or duplicate turns",
            "Retain the qualified candidate",
        )
        == "keep"
    )
    assert (
        decision_class(
            "Completed Refine: five evidence invalidations were recorded",
            "Return to the bounded rollback",
        )
        == "refine"
    )
    assert (
        decision_class(
            "Completed Go Deeper: all development checks passed",
            "Keep the method as a hypothesis only",
        )
        == "go-deeper"
    )


def test_markdown_link_targets_preserves_multiple_evidence_links() -> None:
    cell = "[Instrument](instruments/run.json); [Record](records/run.json)"

    assert markdown_link_targets(cell) == [
        "instruments/run.json",
        "records/run.json",
    ]


def test_parse_registry_reads_complete_rows(tmp_path: Path) -> None:
    registry = tmp_path / "result-registry.md"
    registry.write_text(
        "# Registry\n\n"
        "| Result ID | Date | Component | Dataset / corpus | Status | Decision | Summary | Machine record | Reproduction |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| `result-001` | 2026-09-02 | grounding | dataset-v1 | Completed Keep | Keep candidate | [Results](result-001-results.md) | [Record](records/result-001.json) | command |\n"
    )

    rows = parse_registry(registry)

    assert len(rows) == 1
    assert rows[0].result_id == "result-001"
    assert rows[0].line_number == 5


def test_write_csv_uses_repository_safe_lf_endings(tmp_path: Path) -> None:
    output = tmp_path / "inventory.csv"

    write_csv(output, ["path", "status"], [{"path": "example.py", "status": "ok"}])

    assert output.read_bytes() == b"path,status\nexample.py,ok\n"
