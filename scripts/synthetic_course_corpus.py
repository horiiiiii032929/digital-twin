"""Shared builders for the committed synthetic course corpus."""

import base64
from datetime import UTC, datetime
from pathlib import Path

import pymupdf

from src.digital_twin.grounding import (
    ApprovalDecision,
    ApprovalRecord,
    DocumentChunk,
    HeadingParagraphChunker,
    LocalDocumentParser,
    SourcePermissions,
    SourceArtifact,
    source_artifact_from_path,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "course_corpus"
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8A"
    "AQUBAScY42YAAAAASUVORK5CYII="
)


def synthetic_source_paths(temp_root: Path) -> list[Path]:
    paths = sorted(CORPUS.iterdir())
    pdf_path = temp_root / "figure-notes.pdf"
    write_synthetic_figure_pdf(pdf_path)
    return [*paths, pdf_path]


def synthetic_source_and_approval(
    path: Path,
) -> tuple[SourceArtifact, ApprovalRecord]:
    source_id = f"synthetic-{path.stem}"
    source = source_artifact_from_path(
        path,
        artifact_id=source_id,
        title=path.stem.replace("-", " ").title(),
        version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        provider_role="professor",
    )
    approval = ApprovalRecord(
        id=f"approval-{source_id}-v1",
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
        notes="Synthetic fixture approval only.",
    )
    return source, approval


def build_retrieval_evaluation_chunks(temp_root: Path) -> list[DocumentChunk]:
    parser = LocalDocumentParser()
    chunker = HeadingParagraphChunker(max_chars=220, overlap_chars=60)
    chunks: list[DocumentChunk] = []
    for path in synthetic_source_paths(temp_root):
        source, approval = synthetic_source_and_approval(path)
        document = parser.parse(path, source, approval).document
        chunks.extend(chunker.chunk(document))
    return chunks


def write_synthetic_figure_pdf(path: Path) -> None:
    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_text((72, 72), "Synthetic browser security figure notes")
    page.insert_text((72, 110), "The browser sends an authenticated request.")
    page.insert_image(pymupdf.Rect(72, 150, 216, 246), stream=ONE_PIXEL_PNG)
    page.insert_text((72, 270), "Figure 1: Synthetic request flow")
    pdf.save(path, no_new_id=True)
    pdf.close()
