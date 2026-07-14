"""Run a deterministic, synthetic verification of local ingestion and chunking."""

import base64
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pymupdf

from src.digital_twin.grounding import (
    ApprovalDecision,
    ApprovalRecord,
    HeadingParagraphChunker,
    LocalDocumentParser,
    LocalFigureStore,
    SourcePermissions,
    source_artifact_from_path,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "course_corpus"
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8A"
    "AQUBAScY42YAAAAASUVORK5CYII="
)


def main() -> None:
    paths = sorted(CORPUS.iterdir())
    with tempfile.TemporaryDirectory(prefix="digital-twin-ingestion-") as temp:
        temp_root = Path(temp)
        pdf_path = temp_root / "synthetic-figure-notes.pdf"
        _write_pdf(pdf_path)
        paths.append(pdf_path)

        parser = LocalDocumentParser(LocalFigureStore(temp_root / "figures"))
        chunker = HeadingParagraphChunker(max_chars=480, overlap_chars=80)
        summaries = []
        for ordinal, path in enumerate(paths, start=1):
            source = source_artifact_from_path(
                path,
                artifact_id=f"synthetic-source-{ordinal}",
                title=path.stem.replace("-", " ").title(),
                version=1,
                source_label=SourceLabel.COURSE_APPROVED,
                provider_role="professor",
            )
            approval = ApprovalRecord(
                id=f"synthetic-approval-{ordinal}",
                source_artifact_id=source.id,
                source_version=source.version,
                decision=ApprovalDecision.APPROVED,
                permissions=SourcePermissions(
                    processing_allowed=True,
                    tutoring_allowed=True,
                    display_allowed=False,
                ),
                reviewer_id="synthetic-professor",
                reviewer_role="professor",
                reviewed_at=datetime(2026, 7, 14, tzinfo=UTC),
            )
            first = parser.parse(path, source, approval)
            second = parser.parse(path, source, approval)
            first_chunks = chunker.chunk(first.document)
            second_chunks = chunker.chunk(second.document)
            if first.document != second.document:
                raise RuntimeError(f"non-deterministic parsing: {path.name}")
            if [figure.id for figure in first.figures] != [
                figure.id for figure in second.figures
            ]:
                raise RuntimeError(f"non-deterministic figures: {path.name}")
            if [chunk.id for chunk in first_chunks] != [
                chunk.id for chunk in second_chunks
            ]:
                raise RuntimeError(f"non-deterministic chunking: {path.name}")
            provenance_preserved = all(
                chunk.source_artifact_id == source.id
                and chunk.source_version == source.version
                and chunk.retrieval_allowed
                for chunk in first_chunks
            )
            if not provenance_preserved:
                raise RuntimeError(f"provenance was not preserved: {path.name}")
            summaries.append(
                {
                    "source": path.name,
                    "document_id": first.document.id,
                    "segments": len(first.document.segments),
                    "chunks": len(first_chunks),
                    "figures": len(first.figures),
                    "provenance_preserved": provenance_preserved,
                }
            )

        print(
            json.dumps(
                {
                    "status": "passed",
                    "documents": len(summaries),
                    "chunks": sum(item["chunks"] for item in summaries),
                    "figures": sum(item["figures"] for item in summaries),
                    "results": summaries,
                },
                indent=2,
            )
        )


def _write_pdf(path: Path) -> None:
    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_text((72, 72), "Synthetic browser security figure notes")
    page.insert_text((72, 110), "The browser sends an authenticated request.")
    page.insert_image(pymupdf.Rect(72, 150, 216, 246), stream=ONE_PIXEL_PNG)
    page.insert_text((72, 270), "Figure 1: Synthetic request flow")
    pdf.save(path, no_new_id=True)
    pdf.close()


if __name__ == "__main__":
    main()
