"""Verify preserved file bytes and create the final shareable ZIP."""

import json
import shutil
import sqlite3
import zipfile
from pathlib import Path

from build_professor_evidence import ROOT, DEST, BUILD, digest


def main():
    validation = json.loads((BUILD / "restore-validation.json").read_text())
    c = sqlite3.connect(DEST / "database/evidence.sqlite")
    c.row_factory = sqlite3.Row
    files = [dict(r) for r in c.execute("SELECT * FROM files ORDER BY original_path")]
    for item in files:
        if item["package_path"]:
            p = DEST / item["package_path"]
            assert p.exists(), item["original_path"]
            assert item["packaged_sha256"] == digest(p), item["original_path"]
            if item["status"] == "included":
                assert item["sha256"] == item["packaged_sha256"], item["original_path"]
    tools = DEST / "records/archive-tools"
    tools.mkdir(exist_ok=True)
    for name in [
        "build_professor_evidence.py",
        "supplement_professor_evidence.py",
        "finalize_professor_evidence.py",
        "package_professor_evidence.py",
    ]:
        shutil.copy2(ROOT / "scripts" / name, tools / name)
    shutil.copy2(
        ROOT / "tests/test_professor_evidence_archive.py",
        tools / "test_professor_evidence_archive.py",
    )
    shutil.copy2(
        BUILD / "restore-validation.json", DEST / "snapshots/restore-validation.json"
    )
    summary = {
        "archive_version": 1,
        "created_date": "2026-09-09",
        "scope": "Latest 70-slide Final Presentation and 6 September submitted report, plus linked historical supporting records",
        "document_index_pages": 4,
        "presentation": dict(
            c.execute(
                "SELECT key,value FROM archive_info WHERE key LIKE 'presentation%'"
            ).fetchall()
        ),
        "report_sha256": c.execute(
            "SELECT value FROM archive_info WHERE key='report_sha256'"
        ).fetchone()[0],
        "original_file_catalog": files,
        "counts": {
            table: c.execute("SELECT count(*) FROM " + table).fetchone()[0]
            for table in ["files", "records", "payloads", "runs", "evidence_groups"]
        },
        "validation": validation,
        "limitations": [
            "48 unresolved referenced paths are catalogued; some are historical or moved references, not proven lost original results.",
            "The historical persona confirmation, earlier learner simulation and other missing raw ledgers cannot be reconstructed from summaries alone.",
            "Original metrics are preserved; only the explicitly listed saved-data arithmetic checks were recalculated.",
            "Authentication/session tables are excluded. Binary checkpoint values remain in sanitized SQLite companions.",
            "Source permissions are for private professor research review; this archive is not public redistribution.",
            "Source-code snapshots remain inside original ZIPs and are also text indexed; current code is not substituted for historical execution.",
            "Model weight caches and redundant presentation media were not copied. Model/configuration identities remain in records.",
            "Original source documents can retain repository-relative links; use the index, file catalog and file_links table for archive destinations.",
        ],
    }
    # List and hash every delivered member. The manifest itself is covered by the ZIP hash.
    summary["archive_members"] = [
        {
            "path": str(p.relative_to(DEST)),
            "bytes": p.stat().st_size,
            "sha256": digest(p),
        }
        for p in sorted(DEST.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    ]
    (DEST / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    c.close()
    out = ROOT / "reports/generated/professor-evidence.zip"
    with zipfile.ZipFile(
        out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True
    ) as z:
        for p in sorted(DEST.rglob("*")):
            if p.is_file():
                z.write(p, "professor-evidence/" + str(p.relative_to(DEST)))
    print("ZIP written; checking every member", flush=True)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
    (ROOT / "reports/generated/professor-evidence.zip.sha256").write_text(
        digest(out) + "  professor-evidence.zip\n"
    )
    print(
        json.dumps(
            {
                "zip": str(out),
                "bytes": out.stat().st_size,
                "sha256": digest(out),
                "files": len(summary["archive_members"]) + 1,
            }
        )
    )


if __name__ == "__main__":
    main()
