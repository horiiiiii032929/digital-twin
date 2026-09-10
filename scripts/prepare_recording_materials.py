"""Build small synthetic PDFs and a cast manifest for product recording."""
import json
from pathlib import Path

import pymupdf

from scripts.recording_app import ACTORS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/presentation/recording"
COURSES = (
    ("systems-notes", "Systems", "Professor A", (
        ("Cache coherence", "Cache coherence keeps replicated processor data consistent."),
        ("Virtual memory", "Virtual memory maps process addresses to physical memory pages."),
    )),
    ("release-governance-notes", "Release governance", "Professor B", (
        ("Release policy", "A release policy defines approval and withdrawal controls."),
    )),
)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, title, professor, sections in COURSES:
        document = pymupdf.open()
        # Provenance belongs in metadata/manifest, not the retrieved lesson text.
        # One text-only concept per page avoids a decorative page being ingested
        # as one diagram containing headers, permissions and unrelated concepts.
        document.set_metadata({"title": title, "author": professor,
                               "subject": "Synthetic recording material; version 2"})
        for index, (heading, body) in enumerate(sections):
            page = document.new_page(width=960, height=540)
            remaining = page.insert_textbox(pymupdf.Rect(80, 190, 880, 380), body,
                                           fontsize=26, lineheight=1.5)
            if remaining < 0:
                raise ValueError(f"Text overflow: {slug}, page {index + 1}")
            preview = ROOT / "reports/generated/recording-workspace" / f"{slug}-page-{index + 1}.png"
            preview.parent.mkdir(parents=True, exist_ok=True)
            page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(preview)
        document.save(OUT / f"{slug}.pdf", garbage=4, deflate=True)
        document.close()
    (OUT / "source-permissions.json").write_text(json.dumps({
        "version": 2, "synthetic": True,
        "permissions": {"processing": True, "tutoring": True, "display": True},
        "scope": "Recording fixture, not a complete course or evaluation dataset",
        "files": [slug + ".pdf" for slug, *_ in COURSES],
    }, indent=2) + "\n")
    manifest = [{"label": label, "account_id": account_id, "role": role,
                 "url": f"http://127.0.0.1:{port}" + ("/professor/setup" if role == "professor" else "/student")}
                for label, account_id, port, role in ACTORS]
    (OUT / "cast.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared two synthetic PDFs and six actor URLs in {OUT}")


if __name__ == "__main__":
    main()
