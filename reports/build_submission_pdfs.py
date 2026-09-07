"""Package the standalone abstract and report with curated appendices.

Compile abstract.tex and report.tex into reports/generated/final-report/components
first. The historical full archive is retained separately, not concatenated into
submission PDFs. No evaluation or application execution occurs here.
"""
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime, timezone
import pymupdf as fitz

out = Path("reports/generated/final-report")
components = out / "components"
outputs = {"abstract.pdf": "abstract.pdf", "report-with-appendices.pdf": "report.pdf"}
checks = {}
for target, source in outputs.items():
    shutil.copyfile(components / source, out / target)
    with fitz.open(out / target) as doc:
        text = "\n".join(page.get_text() for page in doc)
        assert "Hikaru (Rawin) Horinouchi" in text and "A0330350X" in text
        assert "OpenAI Codex" in text
        if target == "abstract.pdf":
            assert len(doc) == 1
        link_count = 0
        for page in doc:
            for link in page.get_links():
                link_count += 1
                assert link["kind"] not in (fitz.LINK_GOTOR, fitz.LINK_LAUNCH), link
                if link["kind"] == fitz.LINK_GOTO:
                    assert 0 <= link["page"] < len(doc), link
                if link["kind"] == fitz.LINK_NAMED:
                    assert link["nameddest"] in doc.resolve_names(), link
        if target != "abstract.pdf":
            names = doc.resolve_names()
            for label in ["study-A", "study-B", "study-C", "study-D", "study-E", "study-F", "study-G", "study-H", "study-L1", "study-L1c", "study-L2", "study-L3"]:
                # LaTeX resolves labels to section/table destinations, checked via AUX.
                aux = (components / "report.aux").read_text() if (components / "report.aux").exists() else ""
                if aux:
                    assert "newlabel{" + label + "}" in aux, label
            assert "Detailed Design and Trial Appendix" not in text
        checks[target] = {"pages": len(doc), "links_verified": link_count,
                          "bytes": (out / target).stat().st_size,
                          "sha256": hashlib.sha256((out / target).read_bytes()).hexdigest()}
manifest = {"created_utc": datetime.now(timezone.utc).isoformat(),
            "author": "Hikaru (Rawin) Horinouchi", "student_id": "A0330350X",
            "submission_scope": "standalone abstract; report with curated explanatory appendices",
            "historical_trial_archive_included": False, "files": checks}
(out / "submission-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
