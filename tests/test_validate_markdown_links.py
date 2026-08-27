from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.validate_markdown_links import find_broken_links, iter_markdown_files


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True)


def test_ignored_markdown_is_not_part_of_repository_link_validation(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init")
    (tmp_path / ".gitignore").write_text("data/external/\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text(
        "[valid](target.md)\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "target.md").write_text("# Target\n", encoding="utf-8")
    ignored = tmp_path / "data" / "external"
    ignored.mkdir(parents=True)
    (ignored / "upstream.md").write_text(
        "[not locally vendored](missing.svg)\n", encoding="utf-8"
    )

    paths = iter_markdown_files(tmp_path)
    checked_links, broken_links = find_broken_links(tmp_path)

    assert tmp_path / "docs" / "guide.md" in paths
    assert ignored / "upstream.md" not in paths
    assert checked_links == 1
    assert broken_links == []


def test_reviewable_untracked_markdown_is_checked(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    (tmp_path / "draft.md").write_text("[broken](missing.md)\n", encoding="utf-8")

    checked_links, broken_links = find_broken_links(tmp_path)

    assert checked_links == 1
    assert broken_links == ["draft.md: missing.md"]
