import hashlib
import json
from pathlib import Path
import subprocess

import pymupdf
import pytest

from scripts.validate_submitted_report_links import (
    BASELINE, EVIDENCE_INDEX, REPOSITORY_URL, SUBMISSION, repository_target, validate,
)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    target = "research/result.md"
    (tmp_path / target).parent.mkdir()
    (tmp_path / target).write_text("Synthetic result\n")
    digest = hashlib.sha256((tmp_path / target).read_bytes()).hexdigest()
    (tmp_path / SUBMISSION).mkdir(parents=True)
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(10, 10, 100, 30),
                          "uri": REPOSITORY_URL + "/blob/main/" + target})
        document.save(tmp_path / SUBMISSION / "report.pdf")
    artifacts = {"report.pdf": hashlib.sha256((tmp_path / SUBMISSION / "report.pdf").read_bytes()).hexdigest()}
    (tmp_path / SUBMISSION / "submission-sha256.json").write_text(json.dumps(artifacts))
    (tmp_path / BASELINE).parent.mkdir()
    (tmp_path / BASELINE).write_text(json.dumps({"files": {target: digest}}))
    (tmp_path / EVIDENCE_INDEX).parent.mkdir(parents=True)
    (tmp_path / EVIDENCE_INDEX).write_text(json.dumps([{"source_path": target, "source_sha256": digest}]))
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    return tmp_path


def test_preserved_submission_and_cited_evidence_pass(repository):
    assert validate(repository) == {"submission_files": 1, "cited_files": 1, "indexed_studies": 1}


def test_deleted_cited_file_is_rejected(repository):
    (repository / "research/result.md").unlink()
    with pytest.raises(ValueError, match="not publishable"):
        validate(repository)


def test_changed_evidence_is_rejected(repository):
    (repository / "research/result.md").write_text("Different result")
    with pytest.raises(ValueError, match="hash changed"):
        validate(repository)


def test_changed_pdf_is_rejected(repository):
    with (repository / SUBMISSION / "report.pdf").open("ab") as file:
        file.write(b"changed")
    with pytest.raises(ValueError, match="hash changed"):
        validate(repository)


def test_incomplete_link_baseline_is_rejected(repository):
    (repository / BASELINE).write_text('{"files": {}}')
    with pytest.raises(ValueError, match="targets differ"):
        validate(repository)


def test_external_links_are_distinguished_from_unsafe_repository_paths():
    assert repository_target("https://example.org/paper") is None
    assert repository_target(REPOSITORY_URL) is None
    assert repository_target(REPOSITORY_URL + "/blob/main/docs/a%20b.md") == "docs/a b.md"
    with pytest.raises(ValueError, match="unsafe"):
        repository_target(REPOSITORY_URL + "/blob/main/%2E%2E/secret")
