"""Validate repository-local links in tracked Markdown documents."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def repository_files(root: Path = REPOSITORY_ROOT) -> list[Path]:
    """Return files available to publish, including reviewable untracked work."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted({root / path for path in result.stdout.decode().split("\0") if path})


def iter_markdown_files(root: Path = REPOSITORY_ROOT) -> list[Path]:
    return [path for path in repository_files(root) if path.suffix == ".md"]


def local_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]

    target = unquote(target.split("#", maxsplit=1)[0])
    if not target:
        return None

    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    return target


def find_broken_links(root: Path = REPOSITORY_ROOT) -> tuple[int, list[str]]:
    checked_links = 0
    broken_links: list[str] = []

    root = root.resolve()
    files = repository_files(root)
    publishable = {path.resolve() for path in files if path.is_file()}
    # Git carries directories only through their files. A link to an ignored
    # local artifact must fail even if that artifact happens to exist here.
    directories = {parent for path in publishable for parent in path.parents
                   if parent == root or root in parent.parents}
    for path in files:
        if path.suffix != ".md":
            continue
        content = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(content):
            target = local_target(raw_target)
            if target is None:
                continue

            checked_links += 1
            destination = (path.parent / target).resolve()
            if (not destination.exists()
                    or (destination not in publishable and destination not in directories)
                    or (destination != root and root not in destination.parents)):
                relative_path = path.relative_to(root)
                broken_links.append(f"{relative_path}: {target}")

    return checked_links, broken_links


def main() -> int:
    checked_links, broken_links = find_broken_links()
    if broken_links:
        print("Broken local Markdown links:")
        for link in broken_links:
            print(f"- {link}")
        return 1

    print(f"Validated {checked_links} local Markdown links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
