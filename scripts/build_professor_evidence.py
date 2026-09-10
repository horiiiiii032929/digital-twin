"""Package existing research evidence without running experiments or providers.

Use --inventory first. Authoring uses the bundled Codex Python runtime.
"""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, quote

ROOT = Path(__file__).resolve().parents[1]
DECK = Path(
    "/Users/hikaru/Desktop/Course Digital Twin — Final Presentation/Course Digital Twin.pptx"
)
DEST = ROOT / "reports/generated/professor-evidence"
BUILD = ROOT / "reports/generated/professor-evidence-build"

# Explicit mappings checked against the 70-slide delivered PPTX and submitted
# report's Evidence Index. Report-only studies deliberately have no slide number.
GROUPS = [
    ("Course ingestion and page bounded chunks", "11", ["cross-course-ingestion-v1"]),
    (
        "Early evidence interface comparison",
        "16",
        ["course-digital-twin-whole-system-architecture-round-1-001"],
    ),
    (
        "Typed target evidence selection",
        "18",
        ["course-digital-twin-whole-system-architecture-round-2-001"],
    ),
    (
        "Semantic target comparison",
        "19",
        ["academic-factual-qa-semantic-target-comparison-002"],
    ),
    (
        "Semantic evidence units and ambiguity",
        "19–20",
        [
            "academic-factual-qa-source-semantic-atom-comparison-001",
            "academic-factual-qa-ambiguity-safe-comparison-002",
        ],
    ),
    ("Fresh factual comparison", "21", ["final-cross-method-factual-confirmation-001"]),
    ("Visual retrieval confirmation", "22", ["true-visual-omni-confirmation-002"]),
    (
        "IT5004 teaching example",
        "10, 12–13, 24–26, 28",
        ["it5004-presentation-teaching-002"],
    ),
    (
        "Professor fidelity and corrected reviewer scope",
        "28",
        [
            "professor-fidelity-v2-anchor-002-machine-review-summary-001-analysis-correction-001"
        ],
    ),
    (
        "Generator model comparison",
        "30",
        ["generation-model-dialogue-stability-development-001"],
    ),
    (
        "Audited teaching comparison and reviewer failures",
        "29, 31–36",
        [
            "post-report-final-selection-decision-004",
            "post-report-final-selection-004",
            "post-report-blind-review-003",
        ],
    ),
    (
        "Source grounded learner assessment",
        "46, 69",
        ["post-report-source-assessment-001", "post-report-source-assessment-002"],
    ),
    (
        "Later learner prediction and timing simulation",
        "47–52, 69",
        ["post-report-learner-policy-001"],
    ),
    (
        "Goal completion and scoped evidence",
        "53–54",
        [
            "goal-completion-scope-development-001",
            "goal-completion-scope-review-audit-001",
        ],
    ),
    (
        "Live model governance confirmation",
        "55",
        ["governed-full-autonomy-v2-1-persona-confirmation-024"],
    ),
    (
        "Longitudinal model integration",
        "56",
        ["final-profile-operational-dialogue-development-001-full-live-001"],
    ),
    (
        "Evidence recovery shadow detector",
        "57",
        ["proactive-outreach-a1-shadow-confirmation-002"],
    ),
    (
        "Local operational qualification",
        "65",
        ["local-r1-governed-v2-1-release-qualification-011"],
    ),
    (
        "Report action planning comparison",
        "",
        ["successor-architecture-confirmation-005-001"],
    ),
    (
        "Report model allocation comparison",
        "",
        ["successor-architecture-engine-comparison-006-001"],
    ),
    (
        "Report learner timing simulation",
        "",
        ["successor-learner-timing-simulation-001"],
    ),
    (
        "Report revision comparison",
        "",
        ["independent-factual-revision-controls-001-fresh-v16-live-001"],
    ),
    (
        "Report pipeline scale and correction",
        "",
        [
            "factual-qa-v3-scale-completion-10000-001",
            "factual-qa-v3-scale-completion-10000-001-analysis-correction-001",
        ],
    ),
    (
        "Report large product evaluation",
        "",
        ["course-digital-twin-evaluation-program-011"],
    ),
    (
        "Report whole corpus regression and disputed metric",
        "",
        ["academic-factual-qa-open-10000-winner-regression-001"],
    ),
    (
        "Published release corpus confirmation",
        "",
        ["governed-full-autonomy-v2-1-corpus-confirmation-028"],
    ),
    (
        "Report historical multi concept trace",
        "",
        ["governed-full-autonomy-v2-1-multi-concept-confirmation-025"],
    ),
]

TEXT_EXT = {
    ".md",
    ".txt",
    ".tex",
    ".py",
    ".mjs",
    ".js",
    ".ts",
    ".tsx",
    ".json",
    ".jsonl",
    ".csv",
    ".tsv",
    ".html",
    ".sql",
    ".yaml",
    ".yml",
    ".toml",
    ".bib",
}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", ".cache"}
SECRET = re.compile(
    r"(?:(?<![A-Za-z0-9_-])sk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}|(?<![A-Za-z0-9])AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
FORBIDDEN_TABLE = re.compile(
    r"(?:identity_credentials|identity_sessions|password|credential|auth_token|api_key)",
    re.I,
)


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def key(p):
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        s = str(p.resolve())
        if s == "/Users/hikaru/Documents/academia_vault":
            return "academia_vault"
        if "/academia_vault/" in s:
            return "academia_vault/" + s.split("/academia_vault/", 1)[1]
        if "/Desktop/Course Digital Twin" in s:
            return "presentation-final/" + p.name
        return s


def aid(k):
    return "F" + hashlib.sha256(k.encode()).hexdigest()[:16]


def category(k):
    if k.startswith("academia_vault/") or "/external/" in k or "/raw/" in k:
        return "materials"
    if "/datasets/" in k or "/interim/" in k or "/processed/" in k:
        return "datasets"
    if k.startswith("reports/generated/") or k.startswith("output/"):
        return "outputs"
    return "records"


def strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)
    elif isinstance(obj, str):
        yield obj


def refs(p):
    """Only explicit path references; never infer a missing run's output."""
    if p.suffix not in {".md", ".json"} or p.stat().st_size > 40_000_000:
        return []
    if key(p).startswith(("data/external/", "src/", "services/", "tests/")):
        return []
    s = p.read_text(errors="replace")
    candidates = []
    if p.suffix == ".json":
        try:
            candidates.extend(strings(json.loads(s)))
        except ValueError:
            pass
    candidates += re.findall(r"`([^`\n]+)`", s)
    candidates += re.findall(r"\]\(([^)\s]+)\)", s)
    candidates += re.findall(
        r"(?:research|reports/generated|data|scripts|src|services|tests|docs)/[\w./+\-]+",
        s,
    )
    found = set()
    for c in candidates:
        c = unquote(c).split("#")[0].rstrip(".,;:")
        c = re.sub(r":\d+(?:-\d+)?$", "", c)
        if (
            "\n" in c
            or len(c) > 450
            or any(x in c for x in ["<", ">", "*", " --", "${"])
        ):
            continue
        if c.startswith("https://github.com/horiiiiii032929/digital-twin/blob/"):
            c = "/".join(c.split("/")[7:])
        if c.startswith(("http:", "https:")):
            continue
        if c.startswith("/Users/"):
            q = Path(c)
            if "/academia_vault/" not in c and not c.startswith(str(ROOT) + "/"):
                continue
        elif c.startswith("academia_vault/"):
            q = Path("/Users/hikaru/Documents") / c
        elif c.startswith(
            (
                "research/",
                "reports/",
                "data/",
                "scripts/",
                "src/",
                "services/",
                "tests/",
                "docs/",
                "output/",
            )
        ):
            q = ROOT / c
        elif c.startswith(("../", "./")):
            q = p.parent / c
        elif "/" not in c and Path(c).suffix in TEXT_EXT | {
            ".pdf",
            ".zip",
            ".sqlite3",
            ".png",
        }:
            q = p.parent / c
            if not q.exists():
                continue
        else:
            continue
        q = q.resolve()
        if key(q) in {"research/05_evaluation/result-registry.md", "README.md"}:
            continue
        if q.is_dir() and (
            key(q).startswith(("academia_vault", "reports/presentation/"))
            or len(key(q).split("/")) < 3
        ):
            continue
        if not q.exists() and (
            Path(c).suffix not in TEXT_EXT | {".pdf", ".zip", ".sqlite3", ".png"}
            and not re.search(r"\d{3}/?$", c)
        ):
            continue
        found.add(q)
    return sorted(found)


def inventory():
    BUILD.mkdir(parents=True, exist_ok=True)
    selected = {}
    group_files = defaultdict(set)
    links = set()
    missing = {}

    def add(p, g, depth=0, origin=None):
        p = p.resolve()
        k = key(p)
        if origin:
            links.add((origin, k, "explicit reference"))
        if any(
            x in SKIP_DIRS or x.startswith(".") for x in p.parts if x not in {".", ".."}
        ) or p.suffix in {".pyc", ".lock"}:
            return
        if any(
            x in k for x in ["data/external/huggingface/", "data/external/model_cache/"]
        ):
            return
        if p.suffix in {".pptx", ".ppsx", ".webm", ".mp4"}:
            return
        if k.startswith("reports/presentation/deck/") and p.suffix in {
            ".pdf",
            ".png",
            ".zip",
        }:
            return
        if not p.exists():
            missing[k] = "Referenced path not found"
            group_files[g].add(k)
            return
        if p.is_dir():
            for q in sorted(p.rglob("*")):
                if q.is_file():
                    add(q, g, depth + 1, k)
            return
        group_files[g].add(k)
        already = k in selected
        selected[k] = p
        # Recursion is capped at result->record->dataset/config/source. The traversal
        # boundary is recorded explicitly rather than claiming arbitrary transitive closure.
        if not already and depth < 4:
            for q in refs(p):
                add(q, g, depth + 1, k)

    for i, (_, _, runs) in enumerate(GROUPS, 1):
        g = f"E{i:02}"
        for run in runs:
            add(ROOT / f"research/05_evaluation/{run}-results.md", g)
            for parent in ["research/05_evaluation/records", "reports/generated"]:
                for p in sorted((ROOT / parent).glob(run + "*")):
                    add(p, g, 1)
            for p in (ROOT / "research/05_evaluation").glob(run + "*-results.md"):
                add(p, g, 1)
            for parent in [
                "research/05_evaluation/instruments",
                "research/05_evaluation/datasets",
            ]:
                for stem in [run, run.replace("-", "_")]:
                    for p in (ROOT / parent).glob(stem + "*"):
                        add(p, g, 1)
    # Additional original data IDs explicitly named in records.
    for g, ks in list(group_files.items()):
        for k in list(ks):
            p = selected.get(k)
            if p and p.suffix == ".json" and "/records/" in k:
                try:
                    obj = json.loads(p.read_text())
                except ValueError:
                    continue
                ds = obj.get("dataset", {})
                if isinstance(ds, dict):
                    for field in ["dataset_id", "id"]:
                        value = ds.get(field)
                        if isinstance(value, str):
                            for q in (ROOT / "research/05_evaluation/datasets").glob(
                                value + "*"
                            ):
                                add(q, g, 2, k)
    # Corpus source provenance. The user requested this private professor research
    # handoff; retain the collection's explicit exclusions, and never sweep the vault.
    portfolio = ROOT / "research/05_evaluation/cross_course_portfolio_v2.manifest.json"
    add(portfolio, "E01")
    corpus = json.loads(portfolio.read_text())
    vault = Path("/Users/hikaru/Documents/academia_vault")
    for course in corpus["courses"]:
        for d in course["documents"]:
            q = vault / course["relative_root"] / d["filename"]
            if not q.exists():
                matches = [
                    x
                    for x in vault.rglob(Path(d["filename"]).name)
                    if x.is_file() and digest(x) == d["sha256"]
                ]
                if matches:
                    # Identical hashes resolve duplicate copies without changing source identity.
                    suffix = (
                        course["relative_root"].split("/", 1)[-1] + "/" + d["filename"]
                    )
                    q = next(
                        (p for p in matches if str(p).endswith(suffix)),
                        sorted(matches)[0],
                    )
            add(q, "E01", 4, key(portfolio))
    for p in (ROOT / "data/interim/it5004-presentation-001").glob("*"):
        add(p, "E08", 2)
    # Explicit implementation and demo evidence, separate from experiments.
    for dirname in [
        "reports/presentation/recording/it5004-context",
        "reports/presentation/recording/it5004-final",
    ]:
        for p in (ROOT / dirname).glob("*.md"):
            add(p, "D01", 1)
    for p in (ROOT / "src/digital_twin").rglob("*.py"):
        add(p, "D02", 4)
    for p in (ROOT / "services").rglob("*.py"):
        add(p, "D02", 4)
    for p in (ROOT / "tests").rglob("*.py"):
        add(p, "D02", 4)
    for p in (ROOT / "reports/submitted/2026-09-06").iterdir():
        add(p, "R01", 4)
    for p in [
        ROOT / "docs/post-report-historical-metric-discrepancy-2026-09-08.md",
        ROOT / "research/03_data/academics-source-permission.md",
        ROOT / "research/05_evaluation/result-registry.md",
    ]:
        add(p, "R01", 4)
    # Freeze slide text and report source without adding a new slide deliverable.
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(DECK) as z:
        slides = []
        for n in range(1, 71):
            root = ET.fromstring(z.read(f"ppt/slides/slide{n}.xml"))
            slides.append(
                {
                    "slide": n,
                    "text": "\n".join(
                        e.text or "" for e in root.iter() if e.tag.endswith("}t")
                    ),
                }
            )
    (BUILD / "slides.json").write_text(json.dumps(slides, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(ROOT / "reports/submitted/2026-09-06/report-source.zip") as z:
        for n in z.namelist():
            if n.endswith((".tex", ".bib")):
                out = BUILD / "submitted-source" / n
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(z.read(n))
    # No files from later source builds are substituted for submitted sources.
    result = {
        "deck": str(DECK),
        "deck_sha256": digest(DECK),
        "groups": GROUPS,
        "files": {k: str(p) for k, p in sorted(selected.items())},
        "group_files": {g: sorted(v) for g, v in group_files.items()},
        "references": sorted(links),
        "missing": missing,
        "bytes": sum(p.stat().st_size for p in selected.values()),
        "traversal": "explicit references through four levels; group roots and referenced directories enumerated in full",
    }
    (BUILD / "inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    print(
        json.dumps(
            {
                "files": len(selected),
                "bytes": result["bytes"],
                "missing_paths": len(missing),
                "groups": len(group_files),
            }
        )
    )
    return result


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE archive_info(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE evidence_groups(evidence_id TEXT PRIMARY KEY,title TEXT,slides TEXT,report_locations TEXT);
CREATE TABLE files(file_id TEXT PRIMARY KEY,original_path TEXT UNIQUE,package_path TEXT,category TEXT,status TEXT,sha256 TEXT,packaged_sha256 TEXT,bytes INTEGER,note TEXT);
CREATE TABLE group_files(evidence_id TEXT REFERENCES evidence_groups,file_id TEXT REFERENCES files,PRIMARY KEY(evidence_id,file_id));
CREATE TABLE file_links(source_file_id TEXT REFERENCES files,target_file_id TEXT REFERENCES files,relation TEXT,PRIMARY KEY(source_file_id,target_file_id,relation));
CREATE TABLE texts(file_id TEXT PRIMARY KEY REFERENCES files,text TEXT,extraction TEXT);
CREATE TABLE payloads(payload_hash TEXT PRIMARY KEY,payload_json TEXT NOT NULL CHECK(json_valid(payload_json)));
CREATE TABLE records(record_id INTEGER PRIMARY KEY,file_id TEXT REFERENCES files,locator TEXT,payload_hash TEXT REFERENCES payloads,UNIQUE(file_id,locator));
CREATE INDEX records_file ON records(file_id);
CREATE INDEX records_payload ON records(payload_hash);
CREATE TABLE runs(file_id TEXT PRIMARY KEY REFERENCES files,run_id TEXT,status TEXT,decision TEXT,code_revision TEXT,dataset_id TEXT);
CREATE INDEX runs_id ON runs(run_id);
CREATE TABLE exclusions(file_id TEXT REFERENCES files,locator TEXT,reason TEXT,row_count INTEGER);
CREATE TABLE checks(check_id TEXT PRIMARY KEY,status TEXT,description TEXT,actual_json TEXT);
CREATE TABLE document_locations(document TEXT,location TEXT,text TEXT,sha256 TEXT,PRIMARY KEY(document,location));
CREATE VIEW json_records AS SELECT r.record_id,r.file_id,f.original_path,r.locator,p.payload_json FROM records r JOIN payloads p USING(payload_hash) JOIN files f USING(file_id);
CREATE VIEW group_inventory AS SELECT g.evidence_id,g.title,f.* FROM evidence_groups g JOIN group_files gf USING(evidence_id) JOIN files f USING(file_id);
CREATE VIEW case_records AS SELECT j.record_id,j.file_id,j.original_path,j.locator,json_extract(j.payload_json,'$.case_id') case_id,j.payload_json FROM json_records j WHERE json_type(j.payload_json,'$.case_id') IS NOT NULL;
CREATE VIEW response_records AS SELECT * FROM case_records WHERE json_type(payload_json,'$.answer') IS NOT NULL OR json_type(payload_json,'$.response') IS NOT NULL;
CREATE VIEW unresolved_files AS SELECT * FROM files WHERE status NOT IN ('included','sanitized_sqlite');
"""


def jdump(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"), default=str)


def report_locations():
    paths = list((BUILD / "submitted-source").rglob("*.tex"))
    study = {}
    for p in paths:
        if p.name == "study-index.tex":
            for line in p.read_text().splitlines():
                a = re.search(r"\\label\{(study-[^}]+)\}", line)
                b = re.search(r"/([^/{}]+)-results\.md", line)
                if a and b:
                    study[b[1]] = a[1]
    locations = defaultdict(set)
    for p in paths:
        section = p.stem
        table = ""
        for line in p.read_text().splitlines():
            m = re.search(r"\\(?:subsection|section)\{([^}]+)\}", line)
            if m:
                section = m[1]
            m = re.search(r"\\label\{(tab:[^}]+)\}", line)
            if m:
                table = m[1]
            if "\\end{table}" in line:
                table = ""
            for run, label in study.items():
                if f"[{label}]" in line:
                    locations[run].add(section + (" / " + table if table else ""))
    for run in study:
        locations[run].add("Appendix Evidence Index / " + study[run])
    return locations


def add_record(c, fid, locator, obj):
    raw = jdump(obj)
    h = hashlib.sha256(raw.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO payloads VALUES (?,?)", (h, raw))
    c.execute(
        "INSERT OR IGNORE INTO records(file_id,locator,payload_hash) VALUES (?,?,?)",
        (fid, locator, h),
    )


def ingest_json(c, fid, obj, locator="$"):
    add_record(c, fid, locator, obj)
    # Index top-level collections without changing or conflating their grain.
    if isinstance(obj, dict):
        for name, v in obj.items():
            if isinstance(v, list):
                for i, row in enumerate(v):
                    if isinstance(row, dict):
                        add_record(c, fid, f"{locator}.{name}[{i}]", row)
    elif isinstance(obj, list):
        for i, row in enumerate(obj):
            if isinstance(row, dict):
                add_record(c, fid, f"{locator}[{i}]", row)


def sqlite_export(c, fid, p, out):
    """Exclude authentication rows, retain all remaining rows and a compact DB copy."""
    source = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    names = [
        r[0]
        for r in source.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    temp = BUILD / "sanitized-runtime.sqlite"
    if temp.exists():
        temp.unlink()
    clean = sqlite3.connect(temp)
    # Preserve schemas/data without replaying triggers or executing stored SQL.
    for name in names:
        quoted = '"' + name.replace('"', '""') + '"'
        info = list(source.execute(f"PRAGMA table_info({quoted})"))
        if not info:
            continue
        count = source.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0]
        if FORBIDDEN_TABLE.search(name):
            c.execute(
                "INSERT INTO exclusions VALUES (?,?,?,?)",
                (fid, name, "Authentication or credential table excluded", count),
            )
            continue
        cols = [r[1] for r in info]

        def q(n):
            return '"' + n.replace('"', '""') + '"'

        clean.execute(
            "CREATE TABLE "
            + quoted
            + " ("
            + ",".join(q(r[1]) + " " + (r[2] or "BLOB") for r in info)
            + ")"
        )
        insert = (
            "INSERT INTO " + quoted + " VALUES (" + ",".join("?" for _ in cols) + ")"
        )
        for i, row in enumerate(source.execute(f"SELECT * FROM {quoted}")):
            values = tuple(row)
            obj = {}
            for col, v in zip(cols, values):
                if isinstance(v, bytes):
                    # Binary checkpoints are retained losslessly in the companion DB; metadata
                    # makes their existence queryable without duplicating opaque blobs in JSON.
                    v = {
                        "binary_sha256": hashlib.sha256(v).hexdigest(),
                        "bytes": len(v),
                        "storage": "companion SQLite column",
                    }
                elif isinstance(v, str) and (
                    col.endswith("_json") or col in {"payload", "value"}
                ):
                    try:
                        v = json.loads(v)
                    except ValueError:
                        pass
                obj[col] = v
            text = jdump(obj)
            if SECRET.search(text):
                c.execute(
                    "INSERT INTO exclusions VALUES (?,?,?,?)",
                    (fid, f"{name}[{i}]", "Secret pattern detected; row excluded", 1),
                )
                continue
            clean.execute(insert, values)
            add_record(c, fid, f"table:{name}/row:{i}", obj)
            if name == "responses" and isinstance(obj.get("payload_json"), dict):
                add_record(c, fid, f"table:{name}/payload:{i}", obj["payload_json"])
        clean.commit()
    clean.close()
    source.close()
    with temp.open("rb") as src, gzip.open(out, "wb", compresslevel=6) as target:
        shutil.copyfileobj(src, target)
    temp.unlink()


def build():
    inv = json.loads((BUILD / "inventory.json").read_text())
    if DEST.exists():
        raise RuntimeError(
            "Output exists: preserve it or choose a fresh output directory before building"
        )
    DEST.mkdir(parents=True)
    for n in ["database", "materials", "datasets", "records", "outputs", "snapshots"]:
        (DEST / n).mkdir()
    c = sqlite3.connect(DEST / "database/evidence.sqlite")
    c.executescript(SCHEMA)
    c.execute("PRAGMA journal_mode=MEMORY")
    c.execute("PRAGMA synchronous=OFF")
    report = report_locations()
    for i, (title, slides, runs) in enumerate(GROUPS, 1):
        loc = sorted(set(x for run in runs for x in report.get(run, [])))
        c.execute(
            "INSERT INTO evidence_groups VALUES (?,?,?,?)",
            (
                f"E{i:02}",
                title,
                slides,
                "; ".join(loc) or "Not explicitly cited in submitted report",
            ),
        )
    for g, title, slides, loc in [
        (
            "D01",
            "Final demonstration and recording evidence",
            "4, 39–44, 60–64",
            "Post submission demonstration",
        ),
        (
            "D02",
            "Implementation and regression test sources",
            "3, 6–10, 14–15, 17, 23–25, 27, 29, 31–32, 38–45, 47–50, 53, 58, 61–64, 67–70",
            "Implementation context; current snapshot, not historical run source",
        ),
        (
            "R01",
            "Submitted documents and provenance",
            "",
            "Submitted report and abstract",
        ),
    ]:
        c.execute(
            "INSERT INTO evidence_groups VALUES (?,?,?,?)", (g, title, slides, loc)
        )
    c.executemany(
        "INSERT INTO archive_info VALUES (?,?)",
        [
            ("archive_version", "1"),
            ("presentation_path", inv["deck"]),
            ("presentation_sha256", inv["deck_sha256"]),
            ("presentation_slide_count", "70"),
            (
                "report_sha256",
                digest(
                    ROOT / "reports/submitted/2026-09-06/report-with-appendices.pdf"
                ),
            ),
            (
                "build_code_revision",
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
            ),
            ("build_working_tree_dirty", "true"),
            ("scope", inv["traversal"]),
            (
                "permission",
                "Private professor research handoff requested by source holder; approved lecture corpus only; mandatory exclusions retained",
            ),
            (
                "metric_policy",
                "Historical values preserved. Packaging and explicit saved-data checks do not requalify experiments.",
            ),
        ],
    )
    for slide in json.loads((BUILD / "slides.json").read_text()):
        c.execute(
            "INSERT INTO document_locations VALUES (?,?,?,?)",
            (
                "Final presentation",
                str(slide["slide"]),
                slide["text"],
                inv["deck_sha256"],
            ),
        )
    all_files = {**inv["files"]}
    # Archive the submitted source members as separate searchable files.
    for p in (BUILD / "submitted-source").rglob("*"):
        if p.is_file():
            all_files[
                "submitted-source/" + str(p.relative_to(BUILD / "submitted-source"))
            ] = str(p)
    file_rows = []
    errors = []
    for pos, (k, path) in enumerate(sorted(all_files.items())):
        p = Path(path)
        fid = aid(k)
        cat = category(k)
        status = "included"
        note = "Original file; byte preserving"
        size = p.stat().st_size
        ext = p.suffix.lower()
        outrel = str(Path(cat) / k)
        out = DEST / outrel
        original_hash = digest(p)
        if p.name.endswith(("-wal", "-shm")):
            status = "excluded_sidecar"
            note = (
                "SQLite sidecar; main database read using SQLite consistent connection"
            )
        if (
            p.name.lower() in {"credentials.json", "storage-state.json", "auth.json"}
            or ".env" in p.name
        ):
            status = "excluded_sensitive"
            note = "Credential/session artifact excluded"
        txt = None
        if status == "included" and ext in TEXT_EXT | {".rst"}:
            txt = p.read_text(errors="replace")
            if SECRET.search(txt):
                status = "excluded_sensitive"
                note = "Secret-like value detected; original retained locally only"
        if status == "included":
            out.parent.mkdir(parents=True, exist_ok=True)
            if ext in {".sqlite", ".sqlite3", ".db"}:
                outrel += ".gz"
                out = DEST / outrel
                status = "sanitized_sqlite"
                note = "Companion SQLite export: authentication excluded, blobs preserved; gzip decompress before opening. Original schema constraints are not replayed."
            c.execute(
                "INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?)",
                (fid, k, outrel, cat, status, original_hash, None, size, note),
            )
            try:
                if status == "sanitized_sqlite":
                    sqlite_export(c, fid, p, out)
                else:
                    shutil.copy2(p, out)
                if txt is not None:
                    if ext == ".json":
                        obj = json.loads(txt)
                        ingest_json(c, fid, obj)
                        if isinstance(obj, dict) and "run_id" in obj:
                            ds = obj.get("dataset", {})
                            dsid = (
                                ds.get("dataset_id", ds.get("id"))
                                if isinstance(ds, dict)
                                else ds
                            )
                            c.execute(
                                "INSERT INTO runs VALUES (?,?,?,?,?,?)",
                                (
                                    fid,
                                    str(obj["run_id"]),
                                    str(obj.get("status", "")),
                                    str(obj.get("decision", "")),
                                    str(obj.get("code_revision", "")),
                                    str(dsid or ""),
                                ),
                            )
                    elif ext == ".jsonl":
                        for n, line in enumerate(txt.splitlines(), 1):
                            if line.strip():
                                add_record(c, fid, f"line:{n}", json.loads(line))
                    elif ext in {".csv", ".tsv"}:
                        for n, row in enumerate(
                            csv.DictReader(
                                txt.splitlines(),
                                delimiter="\t" if ext == ".tsv" else ",",
                            ),
                            2,
                        ):
                            add_record(c, fid, f"row:{n}", row)
                    else:
                        c.execute(
                            "INSERT INTO texts VALUES (?,?,?)",
                            (
                                fid,
                                txt,
                                "Original UTF-8 text; replacement decoding if needed",
                            ),
                        )
                elif ext == ".pdf":
                    from pypdf import PdfReader

                    for n, page in enumerate(PdfReader(p).pages, 1):
                        add_record(
                            c,
                            fid,
                            f"page:{n}",
                            {
                                "page": n,
                                "text": page.extract_text() or "",
                                "extraction": "pypdf plain text; images retained in original PDF",
                            },
                        )
                elif ext == ".zip":
                    with zipfile.ZipFile(p) as z:
                        for info in z.infolist():
                            if info.is_dir():
                                continue
                            add_record(
                                c,
                                fid,
                                "member:" + info.filename,
                                {
                                    "member": info.filename,
                                    "bytes": info.file_size,
                                    "crc": info.CRC,
                                },
                            )
                c.execute(
                    "UPDATE files SET packaged_sha256=? WHERE file_id=?",
                    (digest(out), fid),
                )
            except Exception as e:
                errors.append({"file": k, "error": str(e)})
                c.execute(
                    "UPDATE files SET note=note||? WHERE file_id=?",
                    ("; extraction gap: " + str(e), fid),
                )
        else:
            c.execute(
                "INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?)",
                (fid, k, None, cat, status, original_hash, None, size, note),
            )
        if pos % 150 == 0:
            c.commit()
            print(f"Imported {pos}/{len(all_files)} files", flush=True)
    for k, reason in inv["missing"].items():
        c.execute(
            "INSERT OR IGNORE INTO files VALUES (?,?,?,?,?,?,?,?,?)",
            (
                aid(k),
                k,
                None,
                category(k),
                "unresolved_reference",
                None,
                None,
                None,
                reason
                + "; may be historical, moved or illustrative; not treated as a proven lost result",
            ),
        )
    for g, ks in inv["group_files"].items():
        for k in ks:
            if c.execute("SELECT 1 FROM files WHERE file_id=?", (aid(k),)).fetchone():
                c.execute("INSERT OR IGNORE INTO group_files VALUES (?,?)", (g, aid(k)))
    for a, b, rel in inv["references"]:
        if (
            c.execute("SELECT 1 FROM files WHERE file_id=?", (aid(a),)).fetchone()
            and c.execute("SELECT 1 FROM files WHERE file_id=?", (aid(b),)).fetchone()
        ):
            c.execute(
                "INSERT OR IGNORE INTO file_links VALUES (?,?,?)", (aid(a), aid(b), rel)
            )
    (BUILD / "extraction-errors.json").write_text(json.dumps(errors, indent=2))
    c.commit()
    c.close()
    print("Database imported; extraction errors:", len(errors), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    if args.build:
        build()
    else:
        inventory()
