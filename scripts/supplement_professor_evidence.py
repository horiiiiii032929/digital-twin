"""Recover hash-identical moved materials and index PDF/archive text."""

import json
import shutil
import sqlite3
import zipfile
from pathlib import Path

from pypdf import PdfReader
from build_professor_evidence import (
    ROOT,
    BUILD,
    DEST,
    DECK,
    aid,
    digest,
    key,
    category,
    add_record,
    SECRET,
)


def main():
    c = sqlite3.connect(DEST / "database/evidence.sqlite")
    c.execute("PRAGMA journal_mode=MEMORY")
    c.execute("PRAGMA synchronous=OFF")
    corpus = json.loads(
        (
            ROOT / "research/05_evaluation/cross_course_portfolio_v2.manifest.json"
        ).read_text()
    )
    vault = Path("/Users/hikaru/Documents/academia_vault")
    recovered = []
    for course in corpus["courses"]:
        for item in course["documents"]:
            h = item["sha256"]
            if c.execute(
                "SELECT 1 FROM files WHERE sha256=? AND packaged_sha256 IS NOT NULL",
                (h,),
            ).fetchone():
                continue
            found = [
                p for p in vault.rglob(Path(item["filename"]).name) if digest(p) == h
            ]
            if not found:
                continue
            suffix = course["relative_root"].split("/", 1)[-1] + "/" + item["filename"]
            p = next((p for p in found if str(p).endswith(suffix)), sorted(found)[0])
            k = key(p)
            fid = aid(k)
            rel = "materials/" + k
            out = DEST / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)
            c.execute(
                "INSERT OR IGNORE INTO files VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    fid,
                    k,
                    rel,
                    "materials",
                    "included",
                    h,
                    h,
                    p.stat().st_size,
                    "Hash-identical recovery from relocated canonical collection",
                ),
            )
            c.execute("INSERT OR IGNORE INTO group_files VALUES (?,?)", ("E01", fid))
            old = "academia_vault/" + course["relative_root"] + "/" + item["filename"]
            c.execute(
                "UPDATE files SET package_path=?,status=?,sha256=?,packaged_sha256=?,bytes=?,note=? WHERE original_path=?",
                (
                    rel,
                    "included",
                    h,
                    h,
                    p.stat().st_size,
                    "Old recorded path resolved by exact SHA-256 match; duplicate canonical copies have identical bytes",
                    old,
                ),
            )
            recovered.append(k)
    errors = []
    rows = c.execute(
        "SELECT file_id,original_path,package_path FROM files WHERE package_path LIKE '%.pdf'"
    ).fetchall()
    for n, (fid, k, rel) in enumerate(rows):
        if c.execute(
            "SELECT 1 FROM records WHERE file_id=? AND locator LIKE 'page:%'", (fid,)
        ).fetchone():
            continue
        try:
            for page_no, page in enumerate(PdfReader(DEST / rel).pages, 1):
                add_record(
                    c,
                    fid,
                    f"page:{page_no}",
                    {
                        "page": page_no,
                        "text": page.extract_text() or "",
                        "extraction": "pypdf plain text; original PDF retained",
                    },
                )
            c.execute(
                "UPDATE files SET packaged_sha256=?,note=? WHERE file_id=?",
                (
                    digest(DEST / rel),
                    "Original PDF retained; page text indexed using pypdf",
                    fid,
                ),
            )
        except Exception as e:
            errors.append({"file": k, "error": str(e)})
        if n % 20 == 0:
            c.commit()
            print("PDF text", n, "/", len(rows), flush=True)
    # Actual historical source snapshots are searchable without substituting current code.
    for fid, k, rel in c.execute(
        "SELECT file_id,original_path,package_path FROM files WHERE package_path LIKE '%.zip'"
    ).fetchall():
        try:
            with zipfile.ZipFile(DEST / rel) as z:
                for info in z.infolist():
                    if info.is_dir() or Path(info.filename).suffix not in {
                        ".py",
                        ".md",
                        ".json",
                        ".jsonl",
                        ".tex",
                        ".txt",
                        ".mjs",
                        ".ts",
                        ".tsx",
                        ".sql",
                        ".bib",
                    }:
                        continue
                    text = z.read(info).decode("utf-8", errors="replace")
                    if SECRET.search(text):
                        raise ValueError(
                            "Secret-like value in archive member; package requires exclusion"
                        )
                    add_record(
                        c,
                        fid,
                        "member-text:" + info.filename,
                        {
                            "member": info.filename,
                            "text": text,
                            "extraction": "UTF-8 source archive member; original ZIP retained",
                        },
                    )
        except Exception as e:
            errors.append({"file": k, "error": str(e)})
    for p in [DECK.parent / "references.html", DECK.parent / "SHA256.json"]:
        k = "presentation-final/" + p.name
        fid = aid(k)
        rel = "records/" + k
        out = DEST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
        c.execute(
            "INSERT OR IGNORE INTO files VALUES (?,?,?,?,?,?,?,?,?)",
            (
                fid,
                k,
                rel,
                "records",
                "included",
                digest(p),
                digest(p),
                p.stat().st_size,
                "Final presentation reference metadata; slide files not included",
            ),
        )
        c.execute(
            "INSERT OR IGNORE INTO texts VALUES (?,?,?)",
            (fid, p.read_text(), "Original text"),
        )
        c.execute("INSERT OR IGNORE INTO group_files VALUES (?,?)", ("R01", fid))
    # Give all extracted submitted source members a document group.
    c.execute(
        "INSERT OR IGNORE INTO group_files SELECT 'R01',file_id FROM files WHERE original_path LIKE 'submitted-source/%'"
    )
    for fid, k, text in c.execute(
        "SELECT f.file_id,f.original_path,t.text FROM texts t JOIN files f USING(file_id) WHERE f.original_path LIKE 'submitted-source/%.tex'"
    ).fetchall():
        c.execute(
            "INSERT OR REPLACE INTO document_locations VALUES (?,?,?,?)",
            (
                "Submitted report source",
                k,
                text,
                c.execute(
                    "SELECT sha256 FROM files WHERE file_id=?", (fid,)
                ).fetchone()[0],
            ),
        )
    covered = sum(
        bool(
            c.execute(
                "SELECT 1 FROM files WHERE sha256=? AND packaged_sha256 IS NOT NULL",
                (d["sha256"],),
            ).fetchone()
        )
        for course in corpus["courses"]
        for d in course["documents"]
    )
    c.execute(
        "INSERT OR REPLACE INTO checks VALUES (?,?,?,?)",
        (
            "original-lecture-corpus",
            "PASS" if covered == 32 else "UNRESOLVED",
            "Original 32-document corpus recovered by exact recorded hashes",
            json.dumps(
                {"covered": covered, "expected": 32, "recovered_paths": recovered}
            ),
        ),
    )
    c.commit()
    c.close()
    (BUILD / "extraction-errors-final.json").write_text(json.dumps(errors, indent=2))
    print(
        "PDF/archive extraction errors:",
        len(errors),
        "Corpus originals:",
        covered,
        "/32",
    )


if __name__ == "__main__":
    main()
