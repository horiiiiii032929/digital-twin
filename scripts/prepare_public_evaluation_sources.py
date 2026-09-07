"""Fetch the five revision-pinned public inputs required by repository checks.

This prepares ignored source checkouts only; it does not generate datasets,
rescore historical results, or call a model provider.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from scripts.build_academic_factual_qa_confirmation_v2 import COURSES, SNAPSHOT_ROOT
from scripts.build_academic_factual_qa_semantic_target_successor import (
    THINK_OS_COMMIT, THINK_OS_REPOSITORY, THINK_OS_ROOT,
)


def _git(directory: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def verify_checkout(path: Path, revision: str) -> None:
    """Reject changed or incorrectly pinned inputs without modifying them."""
    if path.is_symlink() or not (path / ".git").is_dir():
        raise ValueError(f"expected an independent Git checkout: {path}")
    if _git(path, "rev-parse", "HEAD") != revision:
        raise ValueError(f"source revision differs from the pinned revision: {path}")
    if _git(path, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(f"source checkout contains local changes: {path}")


def prepare_source(destination: Path, url: str, revision: str) -> str:
    """Fetch a missing checkout atomically, or verify an existing one."""
    if destination.exists() or destination.is_symlink():
        verify_checkout(destination, revision)
        return "verified-existing"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".source-", dir=destination.parent) as temp:
        checkout = Path(temp) / "checkout"
        checkout.mkdir()
        _git(checkout, "init", "--quiet")
        _git(checkout, "remote", "add", "origin", url)
        _git(checkout, "fetch", "--quiet", "--depth=1", "origin", revision)
        _git(checkout, "checkout", "--quiet", "--detach", "FETCH_HEAD")
        verify_checkout(checkout, revision)
        checkout.rename(destination)
    return "fetched-pinned-revision"


def main() -> int:
    outcomes = [
        {
            "course_id": course["course_id"],
            "revision": course["commit"],
            "status": prepare_source(
                SNAPSHOT_ROOT / course["snapshot"],
                course["repository_url"],
                course["commit"],
            ),
        }
        for course in COURSES
    ]
    outcomes.append({
        "course_id": "think-os-semantic-successor",
        "revision": THINK_OS_COMMIT,
        "status": prepare_source(THINK_OS_ROOT, THINK_OS_REPOSITORY, THINK_OS_COMMIT),
    })
    print(json.dumps({"sources": outcomes, "provider_calls": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
