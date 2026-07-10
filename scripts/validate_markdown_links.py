"""Validate repository-local links in tracked Markdown documents."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {".git", ".venv", "dist", "node_modules"}
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def iter_markdown_files() -> list[Path]:
    return sorted(
        path
        for path in REPOSITORY_ROOT.rglob("*.md")
        if not IGNORED_DIRECTORIES.intersection(path.parts)
    )


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


def find_broken_links() -> tuple[int, list[str]]:
    checked_links = 0
    broken_links: list[str] = []

    for path in iter_markdown_files():
        content = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(content):
            target = local_target(raw_target)
            if target is None:
                continue

            checked_links += 1
            destination = (path.parent / target).resolve()
            if not destination.exists():
                relative_path = path.relative_to(REPOSITORY_ROOT)
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
