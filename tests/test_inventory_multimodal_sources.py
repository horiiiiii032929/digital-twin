from __future__ import annotations

from pathlib import Path

from scripts.inventory_multimodal_sources import inventory_sources


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_inventory_separates_private_paths_from_sanitized_counts(tmp_path: Path) -> None:
    write(
        tmp_path / "semester_1/IT5002_computer_architecture/lecture.pdf",
        "synthetic pdf",
    )
    write(tmp_path / "semester_1/IT5002/diagram.drawio", "synthetic diagram")
    write(tmp_path / "semester_1/IT5002/__pycache__/module.pyc", "generated")

    private, sanitized = inventory_sources(tmp_path)

    assert len(private["sources"]) == 3
    assert private["sources"][0]["relative_path"]
    assert sanitized["files"] == 3
    assert sanitized["contains_paths"] is False
    assert "sources" not in sanitized
    assert sanitized["counts_by_eligibility"] == {
        "eligible_candidate": 2,
        "excluded_generated": 1,
    }
    assert sanitized["counts_by_course"]["IT5002"] == 3


def test_inventory_requires_review_for_assessment_and_unassigned_files(tmp_path: Path) -> None:
    write(tmp_path / "semester_1/IT5002/final/lecture_1.pdf", "lecture")
    write(tmp_path / "shared/diagram.png", "image")

    private, _ = inventory_sources(tmp_path)
    eligibility = {
        source["relative_path"]: source["eligibility"]
        for source in private["sources"]
    }

    assert eligibility["semester_1/IT5002/final/lecture_1.pdf"] == "review_required"
    assert eligibility["shared/diagram.png"] == "review_required"


def test_inventory_excludes_secret_indicators(tmp_path: Path) -> None:
    write(tmp_path / "semester_1/IT5002/api_key.txt", "synthetic secret")

    private, sanitized = inventory_sources(tmp_path)

    assert private["sources"][0]["eligibility"] == "excluded_sensitive"
    assert sanitized["counts_by_eligibility"] == {"excluded_sensitive": 1}


def test_inventory_does_not_follow_symlinks_outside_source_root(tmp_path: Path) -> None:
    external = tmp_path.parent / "external-private.txt"
    write(external, "outside source root")
    link = tmp_path / "semester_1/IT5002/external.txt"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(external)

    private, sanitized = inventory_sources(tmp_path)

    assert private["sources"] == []
    assert sanitized["files"] == 0
