from pathlib import Path
import subprocess

import pytest

from scripts.prepare_public_evaluation_sources import prepare_source


@pytest.fixture
def upstream(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "upstream"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
    (repo / "chapter.md").write_text("Synthetic public chapter\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run([
        "git", "-C", str(repo), "-c", "user.name=Fixture",
        "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "Fixture",
    ], check=True)
    revision = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
    ).strip()
    return repo, revision


def test_fetches_pinned_source_and_reuses_it_without_network(tmp_path, upstream):
    repo, revision = upstream
    destination = tmp_path / "snapshot"
    assert prepare_source(destination, str(repo), revision) == "fetched-pinned-revision"
    assert (destination / "chapter.md").read_text() == "Synthetic public chapter\n"
    assert prepare_source(destination, "unreachable", revision) == "verified-existing"


def test_rejects_local_changes_without_overwriting_them(tmp_path, upstream):
    repo, revision = upstream
    destination = tmp_path / "snapshot"
    prepare_source(destination, str(repo), revision)
    (destination / "chapter.md").write_text("Local changes")
    with pytest.raises(ValueError, match="local changes"):
        prepare_source(destination, str(repo), revision)
    assert (destination / "chapter.md").read_text() == "Local changes"


def test_rejects_revision_drift(tmp_path, upstream):
    repo, revision = upstream
    destination = tmp_path / "snapshot"
    prepare_source(destination, str(repo), revision)
    with pytest.raises(ValueError, match="pinned revision"):
        prepare_source(destination, str(repo), "0" * 40)


def test_failed_fetch_leaves_no_partial_destination(tmp_path, upstream):
    repo, _ = upstream
    destination = tmp_path / "snapshot"
    with pytest.raises(subprocess.CalledProcessError):
        prepare_source(destination, str(repo), "0" * 40)
    assert not destination.exists()
    assert not list(tmp_path.glob(".source-*"))
