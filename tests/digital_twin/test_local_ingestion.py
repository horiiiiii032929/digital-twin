from pathlib import Path

import pytest
from pydantic import ValidationError
import pymupdf

from src.digital_twin.grounding import (
    ApprovalDecision,
    EmptySourceError,
    HeadingParagraphChunker,
    LocalDocumentParser,
    LocalFigureStore,
    SourceIntegrityError,
    SourcePermissionError,
    SourcePermissions,
    SourceSensitivity,
    UnsupportedSourceError,
)
from tests.fixtures.ingestion import approved_source, write_synthetic_pdf
from src.digital_twin.grounding.ingestion import _normalized_rect


def test_markdown_parsing_and_chunking_preserve_stable_provenance(tmp_path: Path):
    path = tmp_path / "notes.md"
    path.write_text(
        "# Authentication\n\nSessions preserve login state.\n\n"
        "## CSRF\n\nCSRF abuses a trusted browser session.\n",
        encoding="utf-8",
    )
    source, approval = approved_source(path)
    parser = LocalDocumentParser()

    first = parser.parse(path, source, approval)
    second = parser.parse(path, source, approval)
    chunker = HeadingParagraphChunker(max_chars=128, overlap_chars=32)
    first_chunks = chunker.chunk(first.document)
    second_chunks = chunker.chunk(second.document)

    assert first == second
    assert [chunk.id for chunk in first_chunks] == [
        chunk.id for chunk in second_chunks
    ]
    assert first.document.source_artifact_id == source.id
    assert first.document.source_version == source.version
    assert first.document.approval_record_id == approval.id
    assert first.document.segments[2].heading_path == ["Authentication", "CSRF"]
    assert all(chunk.source_artifact_id == source.id for chunk in first_chunks)
    assert all(chunk.retrieval_allowed for chunk in first_chunks)
    assert all(chunk.metadata["source_checksum"] == source.checksum for chunk in first_chunks)
    assert all(len(chunk.text) <= 128 for chunk in first_chunks)


def test_plain_text_requires_utf8_and_rejects_empty_content(tmp_path: Path):
    invalid = tmp_path / "invalid.txt"
    invalid.write_bytes(b"\xff\xfe")
    source, approval = approved_source(invalid)

    with pytest.raises(UnsupportedSourceError, match="valid UTF-8"):
        LocalDocumentParser().parse(invalid, source, approval)

    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    source, approval = approved_source(empty)
    with pytest.raises(EmptySourceError, match="empty"):
        LocalDocumentParser().parse(empty, source, approval)


@pytest.mark.parametrize(
    ("approval_change", "source_change", "message"),
    [
        ({"decision": ApprovalDecision.REJECTED}, {}, "not been approved"),
        (
            {"permissions": SourcePermissions()},
            {},
            "processing permission",
        ),
        ({}, {"excluded": True}, "excluded"),
        (
            {},
            {"sensitivity": SourceSensitivity.SENSITIVE},
            "sensitive-by-default",
        ),
    ],
)
def test_permission_and_exclusion_failures_are_explicit(
    tmp_path: Path,
    approval_change: dict,
    source_change: dict,
    message: str,
):
    path = tmp_path / "notes.txt"
    path.write_text("Synthetic approved course material.", encoding="utf-8")
    source, approval = approved_source(path)
    source = source.model_copy(update=source_change)
    approval = approval.model_copy(update=approval_change)

    with pytest.raises(SourcePermissionError, match=message):
        LocalDocumentParser().parse(path, source, approval)


def test_permission_is_checked_before_source_bytes_are_read(tmp_path: Path):
    path = tmp_path / "removed.txt"
    path.write_text("Synthetic source.", encoding="utf-8")
    source, approval = approved_source(path)
    path.unlink()
    rejected = approval.model_copy(update={"decision": ApprovalDecision.REJECTED})

    with pytest.raises(SourcePermissionError, match="not been approved"):
        LocalDocumentParser().parse(path, source, rejected)


def test_system_cannot_approve_its_own_proposal(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("Synthetic course material.", encoding="utf-8")
    _, approval = approved_source(path)

    with pytest.raises(ValidationError, match="only a professor"):
        approval.model_copy(update={"reviewer_role": "system"}).model_validate(
            approval.model_copy(update={"reviewer_role": "system"}).model_dump()
        )


def test_checksum_and_approval_version_must_match(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("Version one.", encoding="utf-8")
    source, approval = approved_source(path)

    path.write_text("Version two.", encoding="utf-8")
    with pytest.raises(SourceIntegrityError, match="checksum"):
        LocalDocumentParser().parse(path, source, approval)

    current_source, _ = approved_source(path, version=2)
    with pytest.raises(SourceIntegrityError, match="approval"):
        LocalDocumentParser().parse(path, current_source, approval)


def test_changed_source_version_produces_new_document_identity(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("Version one.", encoding="utf-8")
    source_v1, approval_v1 = approved_source(path, version=1)
    document_v1 = LocalDocumentParser().parse(path, source_v1, approval_v1).document

    path.write_text("Version two.", encoding="utf-8")
    source_v2, approval_v2 = approved_source(path, version=2)
    document_v2 = LocalDocumentParser().parse(path, source_v2, approval_v2).document

    assert document_v1.id != document_v2.id
    assert document_v1.content_hash != document_v2.content_hash


def test_pdf_text_figures_and_page_locators_are_preserved(tmp_path: Path):
    path = tmp_path / "notes.pdf"
    figure_dir = tmp_path / "figures"
    write_synthetic_pdf(path)
    source, approval = approved_source(path)

    bundle = LocalDocumentParser(LocalFigureStore(figure_dir)).parse(
        path,
        source,
        approval,
    )
    chunks = HeadingParagraphChunker(max_chars=180, overlap_chars=32).chunk(
        bundle.document
    )

    assert "CSRF abuses an authenticated browser session" in bundle.document.text
    assert bundle.document.segments[0].page == 1
    assert bundle.document.segments[0].bounding_box is not None
    assert len(bundle.figures) == 1
    figure = bundle.figures[0]
    assert figure.page == 1
    assert figure.caption == "Figure 1: Synthetic request flow"
    assert figure.image_ref.startswith("figure://")
    assert list(figure_dir.iterdir())
    assert figure.permissions == approval.permissions
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert "page 1" in chunks[0].locator

    repeated = LocalDocumentParser(LocalFigureStore(figure_dir)).parse(
        path,
        source,
        approval,
    )
    assert [item.id for item in repeated.figures] == [figure.id]


def test_pdf_coordinates_account_for_nonzero_page_origin():
    page = pymupdf.Rect(10, 20, 110, 220)
    content = pymupdf.Rect(20, 40, 60, 120)

    assert _normalized_rect(content, page) == (0.1, 0.1, 0.5, 0.5)


def test_chunker_uses_whole_segment_overlap(tmp_path: Path):
    path = tmp_path / "overlap.md"
    path.write_text(
        "# Topic\n\n"
        + "A" * 70
        + "\n\n"
        + "B" * 70
        + "\n\n"
        + "C" * 70,
        encoding="utf-8",
    )
    source, approval = approved_source(path)
    document = LocalDocumentParser().parse(path, source, approval).document

    chunks = HeadingParagraphChunker(max_chars=150, overlap_chars=75).chunk(document)

    assert len(chunks) == 2
    assert "A" * 70 in chunks[0].text
    assert "B" * 70 in chunks[0].text
    assert "B" * 70 in chunks[1].text
    assert "C" * 70 in chunks[1].text


def test_image_only_pdf_is_rejected_before_figures_are_persisted(tmp_path: Path):
    path = tmp_path / "scan.pdf"
    figure_dir = tmp_path / "figures"
    write_synthetic_pdf(path, with_text=False, with_figure=True)
    source, approval = approved_source(path)

    with pytest.raises(EmptySourceError, match="OCR is not supported"):
        LocalDocumentParser(LocalFigureStore(figure_dir)).parse(
            path,
            source,
            approval,
        )

    assert not figure_dir.exists()


def test_unsupported_format_and_mime_mismatch_are_rejected(tmp_path: Path):
    unsupported = tmp_path / "notes.docx"
    unsupported.write_bytes(b"synthetic")
    with pytest.raises(UnsupportedSourceError, match="unsupported source format"):
        approved_source(unsupported)

    path = tmp_path / "notes.txt"
    path.write_text("Synthetic notes.", encoding="utf-8")
    source, approval = approved_source(path)
    wrong_mime = source.model_copy(update={"mime_type": "application/pdf"})
    with pytest.raises(UnsupportedSourceError, match="MIME type"):
        LocalDocumentParser().parse(path, wrong_mime, approval)


def test_malformed_and_encrypted_pdfs_are_rejected(tmp_path: Path):
    malformed = tmp_path / "malformed.pdf"
    malformed.write_bytes(b"not a PDF")
    source, approval = approved_source(malformed)
    with pytest.raises(UnsupportedSourceError, match="could not be opened"):
        LocalDocumentParser().parse(malformed, source, approval)

    encrypted = tmp_path / "encrypted.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Synthetic encrypted notes")
    pdf.save(
        encrypted,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="synthetic-owner",
        user_pw="synthetic-user",
        no_new_id=True,
    )
    pdf.close()
    source, approval = approved_source(encrypted)
    with pytest.raises(UnsupportedSourceError, match="encrypted PDFs"):
        LocalDocumentParser().parse(encrypted, source, approval)


def test_markdown_fenced_code_does_not_create_false_headings(tmp_path: Path):
    path = tmp_path / "code.md"
    path.write_text(
        "# Real heading\n\n```markdown\n# Not a heading\n```\n",
        encoding="utf-8",
    )
    source, approval = approved_source(path)

    document = LocalDocumentParser().parse(path, source, approval).document

    assert [segment.heading_path for segment in document.segments] == [
        ["Real heading"],
        ["Real heading"],
    ]
    assert "# Not a heading" in document.segments[1].text


def test_chunker_rejects_invalid_size_and_preserves_non_tutoring_state(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("One paragraph for processing only.", encoding="utf-8")
    permissions = SourcePermissions(
        processing_allowed=True,
        tutoring_allowed=False,
        display_allowed=False,
    )
    source, approval = approved_source(path, permissions=permissions)
    document = LocalDocumentParser().parse(path, source, approval).document

    chunks = HeadingParagraphChunker().chunk(document)

    assert chunks[0].retrieval_allowed is False
    with pytest.raises(ValueError, match="at least 128"):
        HeadingParagraphChunker(max_chars=127)
    with pytest.raises(ValueError, match="below max_chars"):
        HeadingParagraphChunker(max_chars=128, overlap_chars=128)
