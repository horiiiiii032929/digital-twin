import hashlib
import re
from pathlib import Path

import pymupdf

from src.digital_twin.grounding.models import (
    ApprovalDecision,
    ApprovalRecord,
    CourseDocument,
    DocumentSegment,
    FigureAsset,
    ParsedDocumentBundle,
    SourceArtifact,
    SourceSensitivity,
)
from src.digital_twin.grounding.protocols import FigureStore
from src.digital_twin.tutor_policy import SourceLabel


class IngestionError(ValueError):
    """Base class for explicit, user-facing ingestion failures."""


class SourcePermissionError(IngestionError):
    pass


class UnsupportedSourceError(IngestionError):
    pass


class EmptySourceError(IngestionError):
    pass


class SourceIntegrityError(IngestionError):
    pass


class LocalFigureStore:
    """Keep extracted figures in a caller-selected, Git-ignored directory."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def store(self, figure_id: str, extension: str, content: bytes) -> str:
        safe_extension = re.sub(r"[^a-z0-9]", "", extension.lower()) or "bin"
        self.root.mkdir(parents=True, exist_ok=True)
        filename = f"{figure_id}.{safe_extension}"
        (self.root / filename).write_bytes(content)
        return f"figure://{filename}"


class _EphemeralFigureStore:
    def store(self, figure_id: str, extension: str, content: bytes) -> str:
        del extension, content
        return f"unpersisted://{figure_id}"


def source_artifact_from_path(
    path: Path,
    *,
    artifact_id: str,
    title: str,
    version: int,
    source_label: SourceLabel,
    provider_role: str,
    sensitivity: SourceSensitivity = SourceSensitivity.STANDARD,
    excluded: bool = False,
) -> SourceArtifact:
    """Create source metadata without copying bytes or exposing an absolute path."""

    mime_type = _mime_type_for(path)
    content = path.read_bytes()
    return SourceArtifact(
        id=artifact_id,
        title=title,
        mime_type=mime_type,
        checksum=_sha256(content),
        version=version,
        source_label=source_label,
        storage_ref=f"local-source://{artifact_id}/{path.name}",
        provider_role=provider_role,
        sensitivity=sensitivity,
        excluded=excluded,
    )


class LocalDocumentParser:
    def __init__(self, figure_store: FigureStore | None = None) -> None:
        self.figure_store = figure_store or _EphemeralFigureStore()

    def parse(
        self,
        path: Path,
        source: SourceArtifact,
        approval: ApprovalRecord,
    ) -> ParsedDocumentBundle:
        source_format = self._validate_access(path, source, approval)
        content = path.read_bytes()
        self._validate_content(content, source)
        document_id = _stable_id(
            "document",
            source.id,
            str(source.version),
            source.checksum,
        )

        if source_format == "pdf":
            segments, figures = self._parse_pdf(
                content,
                document_id=document_id,
                source=source,
                approval=approval,
            )
        else:
            try:
                decoded = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise UnsupportedSourceError("text sources must be valid UTF-8") from exc
            normalized = _normalize_text(decoded)
            segments = (
                _markdown_segments(normalized)
                if source_format == "markdown"
                else _plain_text_segments(normalized)
            )
            figures = []

        text = "\n\n".join(segment.text for segment in segments).strip()
        if not text:
            raise EmptySourceError("source contains no selectable text")

        document = CourseDocument(
            id=document_id,
            title=source.title,
            text=text,
            source_label=source.source_label,
            source_artifact_id=source.id,
            source_version=source.version,
            content_hash=_sha256(text.encode("utf-8")),
            locator=source.storage_ref,
            permissions=approval.permissions,
            approval_record_id=approval.id,
            segments=segments,
            metadata={
                "source_format": source_format,
                "source_checksum": source.checksum,
                "approval_record_id": approval.id,
            },
        )
        return ParsedDocumentBundle(document=document, figures=figures)

    def _validate_access(
        self,
        path: Path,
        source: SourceArtifact,
        approval: ApprovalRecord,
    ) -> str:
        if source.excluded:
            raise SourcePermissionError("excluded sources cannot be processed")
        if source.sensitivity == SourceSensitivity.SENSITIVE:
            raise SourcePermissionError("sensitive-by-default sources are not supported")
        if (
            approval.source_artifact_id != source.id
            or approval.source_version != source.version
        ):
            raise SourceIntegrityError("approval does not match the source version")
        if approval.decision != ApprovalDecision.APPROVED:
            raise SourcePermissionError("source has not been approved")
        if not approval.permissions.processing_allowed:
            raise SourcePermissionError("processing permission is required")
        source_format = _source_format(path)
        expected_mime_types = {
            "text": {"text/plain"},
            "markdown": {"text/markdown", "text/x-markdown"},
            "pdf": {"application/pdf"},
        }
        if source.mime_type not in expected_mime_types[source_format]:
            raise UnsupportedSourceError("source MIME type does not match its file format")
        return source_format

    def _validate_content(
        self,
        content: bytes,
        source: SourceArtifact,
    ) -> None:
        if not content:
            raise EmptySourceError("source is empty")
        if _sha256(content) != source.checksum:
            raise SourceIntegrityError("source checksum does not match the approved version")

    def _parse_pdf(
        self,
        content: bytes,
        *,
        document_id: str,
        source: SourceArtifact,
        approval: ApprovalRecord,
    ) -> tuple[list[DocumentSegment], list[FigureAsset]]:
        try:
            pdf = pymupdf.open(stream=content, filetype="pdf")
        except pymupdf.FileDataError as exc:
            raise UnsupportedSourceError("PDF could not be opened") from exc

        with pdf:
            if pdf.needs_pass:
                raise UnsupportedSourceError("encrypted PDFs are not supported")

            segments: list[DocumentSegment] = []
            page_blocks: list[tuple[pymupdf.Page, list[tuple]]] = []
            for page_index, page in enumerate(pdf):
                page_number = page_index + 1
                text_blocks = [
                    block
                    for block in page.get_text("blocks", sort=True)
                    if len(block) > 6 and block[6] == 0 and _normalize_text(block[4])
                ]
                for block_ordinal, block in enumerate(text_blocks, start=1):
                    segments.append(
                        DocumentSegment(
                            text=_normalize_text(block[4]),
                            locator=f"page {page_number}, text block {block_ordinal}",
                            page=page_number,
                            bounding_box=_normalized_rect(
                                pymupdf.Rect(block[:4]),
                                page.rect,
                            ),
                        )
                    )
                page_blocks.append((page, text_blocks))

            if not segments:
                raise EmptySourceError(
                    "PDF contains no selectable text; scanned-image OCR is not supported"
                )

            figures: list[FigureAsset] = []
            for page_index, (page, text_blocks) in enumerate(page_blocks):
                figures.extend(
                    self._extract_page_figures(
                        pdf,
                        page,
                        page_number=page_index + 1,
                        document_id=document_id,
                        source=source,
                        approval=approval,
                        text_blocks=text_blocks,
                    )
                )
            return segments, figures

    def _extract_page_figures(
        self,
        pdf: pymupdf.Document,
        page: pymupdf.Page,
        *,
        page_number: int,
        document_id: str,
        source: SourceArtifact,
        approval: ApprovalRecord,
        text_blocks: list[tuple],
    ) -> list[FigureAsset]:
        figures: list[FigureAsset] = []
        seen: set[tuple[int, float, float, float, float]] = set()
        for image in page.get_images(full=True):
            xref = image[0]
            extracted = pdf.extract_image(xref)
            image_bytes = extracted.get("image", b"")
            if not image_bytes:
                continue
            for rect in page.get_image_rects(xref):
                identity = (xref, *[round(value, 3) for value in rect])
                if identity in seen or rect.is_empty:
                    continue
                seen.add(identity)
                normalized_box = _normalized_rect(rect, page.rect)
                if not _valid_normalized_box(normalized_box):
                    continue
                figure_id = _stable_id(
                    "figure",
                    document_id,
                    str(page_number),
                    ",".join(f"{value:.6f}" for value in normalized_box),
                    _sha256(image_bytes),
                )
                image_ref = self.figure_store.store(
                    figure_id,
                    extracted.get("ext", "bin"),
                    image_bytes,
                )
                caption, surrounding_text = _figure_context(rect, text_blocks)
                figures.append(
                    FigureAsset(
                        id=figure_id,
                        document_id=document_id,
                        source_artifact_id=source.id,
                        source_version=source.version,
                        page=page_number,
                        bounding_box=normalized_box,
                        caption=caption,
                        surrounding_text=surrounding_text,
                        extraction_method="pymupdf-embedded-image",
                        checksum=_sha256(image_bytes),
                        image_ref=image_ref,
                        permissions=approval.permissions,
                    )
                )
        return figures


def _source_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return "text"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".pdf":
        return "pdf"
    raise UnsupportedSourceError(f"unsupported source format: {suffix or 'none'}")


def _mime_type_for(path: Path) -> str:
    source_format = _source_format(path)
    return {
        "text": "text/plain",
        "markdown": "text/markdown",
        "pdf": "application/pdf",
    }[source_format]


def _plain_text_segments(text: str) -> list[DocumentSegment]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text)]
    return [
        DocumentSegment(text=paragraph, locator=f"paragraph {ordinal}")
        for ordinal, paragraph in enumerate(paragraphs, start=1)
        if paragraph
    ]


def _markdown_segments(text: str) -> list[DocumentSegment]:
    segments: list[DocumentSegment] = []
    headings: list[str] = []
    paragraph_lines: list[str] = []
    paragraph_ordinal = 0
    fence: tuple[str, int] | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph_ordinal
        paragraph = "\n".join(paragraph_lines).strip()
        paragraph_lines.clear()
        if not paragraph:
            return
        paragraph_ordinal += 1
        heading_label = " > ".join(headings) if headings else "document"
        segments.append(
            DocumentSegment(
                text=paragraph,
                locator=f"{heading_label}, paragraph {paragraph_ordinal}",
                heading_path=list(headings),
            )
        )

    for line in text.splitlines():
        stripped = line.lstrip()
        fence_match = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence is not None:
            paragraph_lines.append(line.rstrip())
            if (
                fence_match
                and fence_match.group(1)[0] == fence[0]
                and len(fence_match.group(1)) >= fence[1]
            ):
                flush_paragraph()
                fence = None
            continue
        if fence_match:
            flush_paragraph()
            marker = fence_match.group(1)
            fence = (marker[0], len(marker))
            paragraph_lines.append(line.rstrip())
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            headings[:] = headings[: level - 1]
            headings.append(title)
            segments.append(
                DocumentSegment(
                    text=title,
                    locator=f"heading: {' > '.join(headings)}",
                    heading_path=list(headings),
                )
            )
        elif not line.strip():
            flush_paragraph()
        else:
            paragraph_lines.append(line.rstrip())
    flush_paragraph()
    return segments


def _normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    lines = [line.rstrip() for line in value.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _normalized_rect(
    rect: pymupdf.Rect,
    page_rect: pymupdf.Rect,
) -> tuple[float, float, float, float]:
    return (
        max(0.0, min(1.0, (rect.x0 - page_rect.x0) / page_rect.width)),
        max(0.0, min(1.0, (rect.y0 - page_rect.y0) / page_rect.height)),
        max(0.0, min(1.0, (rect.x1 - page_rect.x0) / page_rect.width)),
        max(0.0, min(1.0, (rect.y1 - page_rect.y0) / page_rect.height)),
    )


def _valid_normalized_box(box: tuple[float, float, float, float]) -> bool:
    x0, y0, x1, y1 = box
    return 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1


def _figure_context(
    figure_rect: pymupdf.Rect,
    text_blocks: list[tuple],
) -> tuple[str, str]:
    nearby: list[tuple[float, str]] = []
    captions: list[tuple[float, str]] = []
    for block in text_blocks:
        block_rect = pymupdf.Rect(block[:4])
        text = _normalize_text(block[4])
        vertical_distance = min(
            abs(block_rect.y0 - figure_rect.y1),
            abs(figure_rect.y0 - block_rect.y1),
        )
        horizontal_overlap = max(
            0.0,
            min(block_rect.x1, figure_rect.x1) - max(block_rect.x0, figure_rect.x0),
        )
        distance = vertical_distance + (0 if horizontal_overlap else 1000)
        nearby.append((distance, text))
        if block_rect.y0 >= figure_rect.y1 and vertical_distance <= 72:
            captions.append((distance, text))
    caption = min(captions, default=(0, ""))[1]
    surrounding = " ".join(text for _, text in sorted(nearby)[:2])
    return caption, surrounding


def _stable_id(prefix: str, *parts: str) -> str:
    digest = _sha256("\x1f".join(parts).encode("utf-8"))
    return f"{prefix}-{digest[:24]}"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
