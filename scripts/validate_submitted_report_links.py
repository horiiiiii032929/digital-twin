"""Check immutable submission bytes, PDF destinations and cited repository files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pymupdf

from scripts.validate_markdown_links import REPOSITORY_ROOT, repository_files


REPOSITORY_URL = "https://github.com/horiiiiii032929/digital-twin"
SUBMISSION = Path("reports/submitted/2026-09-06")
BASELINE = Path("docs/submitted-report-links.json")
EVIDENCE_INDEX = Path("research/06_reports/final/submission-evidence-index.json")


def repository_target(uri: str) -> str | None:
    """Return an actual submitted GitHub file target, or ignore an external URL."""
    parsed = urlsplit(uri)
    own = urlsplit(REPOSITORY_URL)
    if parsed.netloc != own.netloc or not (
        parsed.path == own.path or parsed.path.startswith(own.path + "/")
    ):
        return None
    tail = unquote(parsed.path[len(own.path):]).strip("/")
    if not tail:
        return None  # Repository home; README remains its entry point.
    if not tail.startswith("blob/main/"):
        raise ValueError(f"unsupported submitted repository destination: {uri}")
    path = tail[len("blob/main/"):]
    if not path or path.startswith("/") or ".." in Path(path).parts:
        raise ValueError(f"unsafe submitted repository destination: {uri}")
    return path


def validate(root: Path = REPOSITORY_ROOT) -> dict[str, int]:
    root = root.resolve()
    published = {p.resolve() for p in repository_files(root) if p.is_file()}

    def check_file(relative: str, expected: str) -> Path:
        path = (root / relative).resolve()
        if root not in path.parents or path not in published:
            raise ValueError(f"submission dependency is not publishable: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"submission dependency hash changed: {relative}")
        return path

    baseline = json.loads((root / BASELINE).read_text())["files"]
    manifest = json.loads((root / SUBMISSION / "submission-sha256.json").read_text())
    targets: set[str] = set()
    for name, expected in manifest.items():
        path = check_file(str(SUBMISSION / name), expected)
        if path.suffix != ".pdf":
            continue
        with pymupdf.open(path) as document:
            for page in document:
                for link in page.get_links():
                    kind = link.get("kind")
                    if kind in (pymupdf.LINK_GOTOR, pymupdf.LINK_LAUNCH):
                        raise ValueError(f"local-file link in submitted PDF: {name}")
                    if kind == pymupdf.LINK_GOTO and not (
                        0 <= link.get("page", -1) < len(document)
                    ):
                        raise ValueError(f"invalid internal PDF destination: {name}")
                    if kind == pymupdf.LINK_NAMED and link.get("nameddest") not in document.resolve_names():
                        raise ValueError(f"invalid named PDF destination: {name}")
                    target = repository_target(link.get("uri", ""))
                    if target:
                        targets.add(target)
    if targets != set(baseline):
        raise ValueError("submitted PDF repository targets differ from the preserved baseline")
    for target, expected in baseline.items():
        check_file(target, expected)
    evidence = json.loads((root / EVIDENCE_INDEX).read_text())
    for row in evidence:
        if row["source_path"] not in targets:
            raise ValueError(f"indexed evidence is absent from PDF links: {row['source_path']}")
        check_file(row["source_path"], row["source_sha256"])
    return {"submission_files": len(manifest), "cited_files": len(targets), "indexed_studies": len(evidence)}


def main() -> int:
    print(json.dumps(validate(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
