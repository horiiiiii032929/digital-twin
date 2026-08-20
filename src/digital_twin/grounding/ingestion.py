import hashlib
import os
import re
import tempfile
from pathlib import Path

import pymupdf

from src.digital_twin.grounding.models import (
    ApprovalDecision,
    ApprovalRecord,
    CourseDocument,
    DocumentRegion,
    DocumentSegment,
    FigureAsset,
    ParsedDocumentBundle,
    RegionKind,
    SourceArtifact,
    SourceSensitivity,
)
from src.digital_twin.grounding.protocols import (
    FigureStore,
    OCRProvider,
    RegionCropStore,
    RegionDescriptionProvider,
)
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
        self.root = root.resolve()
        self.created_paths: list[Path] = []

    def store(self, figure_id: str, extension: str, content: bytes) -> str:
        safe_extension = re.sub(r"[^a-z0-9]", "", extension.lower()) or "bin"
        self.root.mkdir(parents=True, exist_ok=True)
        filename = f"{figure_id}.{safe_extension}"
        if _atomic_content_file(self.root / filename, content):
            self.created_paths.append(self.root / filename)
        return f"figure://{filename}"


class LocalRegionCropStore:
    """Persist original page-region crops outside the release domain model."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.created_paths: list[Path] = []

    def store(self, region_id: str, extension: str, content: bytes) -> str:
        safe_extension = re.sub(r"[^a-z0-9]", "", extension.lower()) or "png"
        self.root.mkdir(parents=True, exist_ok=True)
        filename = f"{region_id}.{safe_extension}"
        if _atomic_content_file(self.root / filename, content):
            self.created_paths.append(self.root / filename)
        return f"region://{filename}"


class _EphemeralFigureStore:
    def store(self, figure_id: str, extension: str, content: bytes) -> str:
        del extension, content
        return f"unpersisted://{figure_id}"


class _EphemeralRegionCropStore:
    def store(self, region_id: str, extension: str, content: bytes) -> str:
        del extension, content
        return f"unpersisted-region://{region_id}"


def _atomic_content_file(destination: Path, content: bytes) -> bool:
    """Create one immutable derived artifact atomically; return whether it was new."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise SourceIntegrityError("derived artifact path is a symbolic link")
    if destination.exists():
        if not destination.is_file() or _sha256(destination.read_bytes()) != _sha256(content):
            raise SourceIntegrityError("derived artifact identity has conflicting content")
        return False
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{destination.name}-", suffix=".pending", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return True


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
    def __init__(
        self,
        figure_store: FigureStore | None = None,
        *,
        region_store: RegionCropStore | None = None,
        ocr_provider: OCRProvider | None = None,
        description_provider: RegionDescriptionProvider | None = None,
        ocr_text_threshold: int = 32,
    ) -> None:
        if ocr_text_threshold < 0:
            raise ValueError("ocr_text_threshold must be non-negative")
        self.figure_store = figure_store or _EphemeralFigureStore()
        self.region_store = region_store or _EphemeralRegionCropStore()
        self.ocr_provider = ocr_provider
        self.description_provider = description_provider
        self.ocr_text_threshold = ocr_text_threshold

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
            segments, figures, regions, warnings = self._parse_pdf(
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
            regions = []
            warnings = []

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
        return ParsedDocumentBundle(
            document=document,
            figures=figures,
            regions=regions,
            processing_warnings=warnings,
        )

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
    ) -> tuple[
        list[DocumentSegment],
        list[FigureAsset],
        list[DocumentRegion],
        list[str],
    ]:
        try:
            pdf = pymupdf.open(stream=content, filetype="pdf")
        except pymupdf.FileDataError as exc:
            raise UnsupportedSourceError("PDF could not be opened") from exc

        with pdf:
            if pdf.needs_pass:
                raise UnsupportedSourceError("encrypted PDFs are not supported")

            segments: list[DocumentSegment] = []
            figures: list[FigureAsset] = []
            regions: list[DocumentRegion] = []
            warnings: list[str] = []
            page_inputs: list[tuple[pymupdf.Page, int, list[tuple]]] = []
            for page_index, page in enumerate(pdf):
                page_number = page_index + 1
                page_segment_start = len(segments)
                text_blocks = [
                    block
                    for block in page.get_text("blocks", sort=True)
                    if len(block) > 6 and block[6] == 0 and _normalize_text(block[4])
                ]
                columns = _column_assignments(text_blocks, page.rect)
                for block_ordinal, block in enumerate(text_blocks, start=1):
                    text = _normalize_text(block[4])
                    rect = pymupdf.Rect(block[:4])
                    column = columns.get(block_ordinal - 1)
                    kind = _text_region_kind(text, column=column)
                    locator = _region_locator(
                        page_number,
                        kind,
                        block_ordinal,
                        column=column,
                    )
                    segments.append(
                        DocumentSegment(
                            text=text,
                            locator=locator,
                            page=page_number,
                            bounding_box=_normalized_rect(rect, page.rect),
                        )
                    )
                    region, crop = self._make_region(
                        page,
                        rect,
                        document_id=document_id,
                        source=source,
                        approval=approval,
                        page_number=page_number,
                        kind=kind,
                        reading_order=len(regions),
                        locator=locator,
                        text=text,
                        extraction_method="pymupdf-selectable-text",
                        metadata={"column": column or "full-width"},
                    )
                    regions.append(region)
                    self._apply_description(region, crop, warnings)

                selectable_chars = sum(
                    len(_normalize_text(block[4])) for block in text_blocks
                )
                if (
                    selectable_chars < self.ocr_text_threshold
                    or _page_has_large_image(page, minimum_area_ratio=0.1)
                ):
                    ocr_segments, ocr_regions = self._extract_ocr_regions(
                        page,
                        document_id=document_id,
                        source=source,
                        approval=approval,
                        page_number=page_number,
                        reading_order_start=len(regions),
                        warnings=warnings,
                    )
                    segments.extend(ocr_segments)
                    regions.extend(ocr_regions)
                page_text = "\n\n".join(
                    segment.text for segment in segments[page_segment_start:]
                ).strip()
                if page_text:
                    page_region, _ = self._make_region(
                        page,
                        page.rect,
                        document_id=document_id,
                        source=source,
                        approval=approval,
                        page_number=page_number,
                        kind=RegionKind.PAGE,
                        reading_order=len(regions),
                        locator=f"page {page_number}",
                        text=page_text,
                        extraction_method="pymupdf-page-text-fallback",
                        metadata={"fallback": "selected-text"},
                    )
                    regions.append(page_region)
                page_inputs.append((page, page_number, text_blocks))

            if not segments:
                raise EmptySourceError(
                    "PDF contains no selectable text; OCR is not supported without "
                    "a configured provider"
                )

            for page, page_number, text_blocks in page_inputs:
                table_regions = self._extract_table_regions(
                    page,
                    document_id=document_id,
                    source=source,
                    approval=approval,
                    page_number=page_number,
                    reading_order_start=len(regions),
                    warnings=warnings,
                )
                regions.extend(table_regions)

                page_figures, figure_regions = self._extract_page_figures(
                    pdf,
                    page,
                    page_number=page_number,
                    document_id=document_id,
                    source=source,
                    approval=approval,
                    text_blocks=text_blocks,
                    reading_order_start=len(regions),
                    warnings=warnings,
                )
                figures.extend(page_figures)
                regions.extend(figure_regions)

                diagram_regions = self._extract_diagram_regions(
                    page,
                    document_id=document_id,
                    source=source,
                    approval=approval,
                    page_number=page_number,
                    reading_order_start=len(regions),
                    excluded_regions=[*table_regions, *figure_regions],
                    warnings=warnings,
                )
                regions.extend(diagram_regions)

            return segments, figures, regions, warnings

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
        reading_order_start: int,
        warnings: list[str],
    ) -> tuple[list[FigureAsset], list[DocumentRegion]]:
        figures: list[FigureAsset] = []
        regions: list[DocumentRegion] = []
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
                area = normalized_box[2] - normalized_box[0]
                area *= normalized_box[3] - normalized_box[1]
                kind = RegionKind.SCREENSHOT if area >= 0.5 else RegionKind.FIGURE
                region, crop = self._make_region(
                    page,
                    rect,
                    document_id=document_id,
                    source=source,
                    approval=approval,
                    page_number=page_number,
                    kind=kind,
                    reading_order=reading_order_start + len(regions),
                    locator=f"page {page_number}, {kind.value} {len(regions) + 1}",
                    text="\n".join(part for part in (caption, surrounding_text) if part),
                    extraction_method="pymupdf-embedded-image-region",
                    metadata={"figure_asset_id": figure_id},
                )
                regions.append(region)
                self._apply_description(region, crop, warnings)
        return figures, regions

    def _extract_ocr_regions(
        self,
        page: pymupdf.Page,
        *,
        document_id: str,
        source: SourceArtifact,
        approval: ApprovalRecord,
        page_number: int,
        reading_order_start: int,
        warnings: list[str],
    ) -> tuple[list[DocumentSegment], list[DocumentRegion]]:
        if self.ocr_provider is None:
            warnings.append(f"page {page_number}: OCR required but no provider configured")
            return [], []

        page_pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        page_image = page_pixmap.tobytes("png")
        try:
            recognized = self.ocr_provider.recognize(
                page_image,
                page_number=page_number,
                image_width=page_pixmap.width,
                image_height=page_pixmap.height,
            )
        except Exception as exc:  # provider failures become inspectable ingestion failures
            warnings.append(
                f"page {page_number}: OCR provider {self.ocr_provider.implementation_id} "
                f"failed ({type(exc).__name__})"
            )
            return [], []

        segments: list[DocumentSegment] = []
        regions: list[DocumentRegion] = []
        for ordinal, recognized_region in enumerate(
            sorted(recognized, key=lambda item: item.reading_order),
            start=1,
        ):
            text = _normalize_text(recognized_region.text)
            if not text:
                continue
            rect = _denormalized_rect(recognized_region.bounding_box, page.rect)
            locator = f"page {page_number}, OCR region {ordinal}"
            segments.append(
                DocumentSegment(
                    text=text,
                    locator=locator,
                    page=page_number,
                    bounding_box=recognized_region.bounding_box,
                )
            )
            metadata = {}
            if recognized_region.confidence is not None:
                metadata["ocr_confidence"] = f"{recognized_region.confidence:.6f}"
            region, crop = self._make_region(
                page,
                rect,
                document_id=document_id,
                source=source,
                approval=approval,
                page_number=page_number,
                kind=RegionKind.OCR,
                reading_order=reading_order_start + len(regions),
                locator=locator,
                text=text,
                extraction_method=(
                    f"ocr:{self.ocr_provider.implementation_id}:"
                    f"{self.ocr_provider.version}"
                ),
                metadata=metadata,
            )
            regions.append(region)
            self._apply_description(region, crop, warnings)
        if not regions:
            warnings.append(f"page {page_number}: OCR provider returned no text regions")
        return segments, regions

    def _extract_table_regions(
        self,
        page: pymupdf.Page,
        *,
        document_id: str,
        source: SourceArtifact,
        approval: ApprovalRecord,
        page_number: int,
        reading_order_start: int,
        warnings: list[str],
    ) -> list[DocumentRegion]:
        try:
            tables = page.find_tables().tables
        except Exception as exc:
            warnings.append(
                f"page {page_number}: table extraction failed ({type(exc).__name__})"
            )
            return []

        regions: list[DocumentRegion] = []
        for table_ordinal, table in enumerate(tables, start=1):
            rows = [
                [_normalize_text(cell or "") for cell in row]
                for row in table.extract()
            ]
            column_headers = rows[0] if rows else []
            table_text = "\n".join(
                " | ".join(cell for cell in row) for row in rows if any(row)
            ).strip()
            if not table_text:
                continue
            table_rect = pymupdf.Rect(table.bbox)
            table_region, crop = self._make_region(
                page,
                table_rect,
                document_id=document_id,
                source=source,
                approval=approval,
                page_number=page_number,
                kind=RegionKind.TABLE,
                reading_order=reading_order_start + len(regions),
                locator=f"page {page_number}, table {table_ordinal}",
                text=table_text,
                extraction_method="pymupdf-table",
                metadata={"table_ordinal": str(table_ordinal)},
            )
            regions.append(table_region)
            self._apply_description(table_region, crop, warnings)

            for row_ordinal, row in enumerate(rows, start=1):
                row_text = " | ".join(cell for cell in row).strip(" |")
                if not row_text or row_ordinal > len(table.rows):
                    continue
                row_rect = pymupdf.Rect(table.rows[row_ordinal - 1].bbox)
                row_region, _ = self._make_region(
                    page,
                    row_rect,
                    document_id=document_id,
                    source=source,
                    approval=approval,
                    page_number=page_number,
                    kind=RegionKind.TABLE_ROW,
                    reading_order=reading_order_start + len(regions),
                    locator=(
                        f"page {page_number}, table {table_ordinal}, row {row_ordinal}"
                    ),
                    text=row_text,
                    extraction_method="pymupdf-table-row",
                    parent_region_id=table_region.id,
                    metadata={
                        "table_ordinal": str(table_ordinal),
                        "row_ordinal": str(row_ordinal),
                        "row_header": row[0] if row else "",
                        "column_headers": " | ".join(column_headers),
                    },
                )
                regions.append(row_region)

                cells = table.rows[row_ordinal - 1].cells
                for column_ordinal, cell_text in enumerate(row, start=1):
                    if not cell_text or column_ordinal > len(cells):
                        continue
                    cell_box = cells[column_ordinal - 1]
                    if cell_box is None:
                        continue
                    cell_region, _ = self._make_region(
                        page,
                        pymupdf.Rect(cell_box),
                        document_id=document_id,
                        source=source,
                        approval=approval,
                        page_number=page_number,
                        kind=RegionKind.TABLE_CELL,
                        reading_order=reading_order_start + len(regions),
                        locator=(
                            f"page {page_number}, table {table_ordinal}, "
                            f"row {row_ordinal}, column {column_ordinal}"
                        ),
                        text=cell_text,
                        extraction_method="pymupdf-table-cell",
                        parent_region_id=row_region.id,
                        metadata={
                            "table_ordinal": str(table_ordinal),
                            "row_ordinal": str(row_ordinal),
                            "column_ordinal": str(column_ordinal),
                            "row_header": row[0] if row else "",
                            "column_header": (
                                column_headers[column_ordinal - 1]
                                if column_ordinal <= len(column_headers)
                                else ""
                            ),
                            "cell_value": cell_text,
                        },
                    )
                    regions.append(cell_region)
        return regions

    def _extract_diagram_regions(
        self,
        page: pymupdf.Page,
        *,
        document_id: str,
        source: SourceArtifact,
        approval: ApprovalRecord,
        page_number: int,
        reading_order_start: int,
        excluded_regions: list[DocumentRegion],
        warnings: list[str],
    ) -> list[DocumentRegion]:
        try:
            clusters = page.cluster_drawings()
        except Exception as exc:
            warnings.append(
                f"page {page_number}: drawing extraction failed ({type(exc).__name__})"
            )
            return []

        regions: list[DocumentRegion] = []
        for rect in clusters:
            normalized = _normalized_rect(rect, page.rect)
            if not _valid_normalized_box(normalized):
                continue
            if any(
                _intersection_over_union(normalized, region.bounding_box) >= 0.65
                for region in excluded_regions
            ):
                continue
            region, crop = self._make_region(
                page,
                rect,
                document_id=document_id,
                source=source,
                approval=approval,
                page_number=page_number,
                kind=RegionKind.DIAGRAM,
                reading_order=reading_order_start + len(regions),
                locator=f"page {page_number}, diagram {len(regions) + 1}",
                text=_text_near_rect(page, rect),
                extraction_method="pymupdf-vector-cluster",
            )
            regions.append(region)
            self._apply_description(region, crop, warnings)
        return regions

    def _make_region(
        self,
        page: pymupdf.Page,
        rect: pymupdf.Rect,
        *,
        document_id: str,
        source: SourceArtifact,
        approval: ApprovalRecord,
        page_number: int,
        kind: RegionKind,
        reading_order: int,
        locator: str,
        text: str,
        extraction_method: str,
        parent_region_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> tuple[DocumentRegion, bytes]:
        clipped = rect & page.rect
        normalized_box = _normalized_rect(clipped, page.rect)
        if not _valid_normalized_box(normalized_box):
            raise SourceIntegrityError("extracted region has an invalid bounding box")
        identity = ",".join(f"{value:.6f}" for value in normalized_box)
        region_id = _stable_id(
            "region",
            document_id,
            str(page_number),
            kind.value,
            identity,
            _normalize_text(text),
        )
        crop = page.get_pixmap(
            matrix=pymupdf.Matrix(2, 2),
            clip=clipped,
            alpha=False,
        ).tobytes("png")
        crop_ref = self.region_store.store(region_id, "png", crop)
        return (
            DocumentRegion(
                id=region_id,
                document_id=document_id,
                source_artifact_id=source.id,
                source_version=source.version,
                source_checksum=source.checksum,
                page=page_number,
                kind=kind,
                bounding_box=normalized_box,
                reading_order=reading_order,
                locator=locator,
                text=_normalize_text(text),
                parent_region_id=parent_region_id,
                extraction_method=extraction_method,
                checksum=_sha256(crop),
                crop_ref=crop_ref,
                permissions=approval.permissions,
                metadata=metadata or {},
            ),
            crop,
        )

    def _apply_description(
        self,
        region: DocumentRegion,
        crop: bytes,
        warnings: list[str],
    ) -> None:
        if self.description_provider is None:
            return
        try:
            description = self.description_provider.describe(region, crop)
        except Exception as exc:
            warnings.append(
                f"{region.locator}: description provider "
                f"{self.description_provider.implementation_id} failed "
                f"({type(exc).__name__})"
            )
            return
        if description is None:
            return
        if description.region_id != region.id:
            warnings.append(f"{region.locator}: description region identity mismatch")
            return
        region.description = description.text
        region.description_method = description.method
        region.description_model_version = description.model_version
        region.description_prompt_version = description.prompt_version


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


def _denormalized_rect(
    box: tuple[float, float, float, float],
    page_rect: pymupdf.Rect,
) -> pymupdf.Rect:
    x0, y0, x1, y1 = box
    return pymupdf.Rect(
        page_rect.x0 + x0 * page_rect.width,
        page_rect.y0 + y0 * page_rect.height,
        page_rect.x0 + x1 * page_rect.width,
        page_rect.y0 + y1 * page_rect.height,
    )


def _column_assignments(
    text_blocks: list[tuple],
    page_rect: pymupdf.Rect,
) -> dict[int, str]:
    candidates: dict[int, str] = {}
    sides: set[str] = set()
    for index, block in enumerate(text_blocks):
        rect = pymupdf.Rect(block[:4])
        width_ratio = rect.width / page_rect.width
        center_ratio = (rect.x0 + rect.x1 - 2 * page_rect.x0) / (
            2 * page_rect.width
        )
        if width_ratio > 0.62:
            continue
        if center_ratio < 0.46:
            side = "left"
        elif center_ratio > 0.54:
            side = "right"
        else:
            continue
        candidates[index] = side
        sides.add(side)
    return candidates if sides == {"left", "right"} else {}


def _page_has_large_image(
    page: pymupdf.Page,
    *,
    minimum_area_ratio: float,
) -> bool:
    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return False
    for image in page.get_images(full=True):
        for rect in page.get_image_rects(image[0]):
            if rect.width * rect.height / page_area >= minimum_area_ratio:
                return True
    return False


def _text_region_kind(text: str, *, column: str | None) -> RegionKind:
    compact = " ".join(text.split())
    lowered = compact.lower()
    if re.match(r"^(figure|fig\.|table)\s+\d+", lowered):
        return RegionKind.CAPTION
    math_markers = ("=", "∑", "∫", "√", "≈", "≤", "≥", "→", "λ", "α", "β")
    if len(compact) <= 240 and any(marker in compact for marker in math_markers):
        return RegionKind.EQUATION
    if column is not None:
        return RegionKind.COLUMN
    if (
        len(compact) <= 100
        and "\n" not in text
        and (compact.isupper() or compact.istitle())
        and not compact.endswith((".", ":", ";"))
    ):
        return RegionKind.HEADING
    return RegionKind.TEXT


def _region_locator(
    page_number: int,
    kind: RegionKind,
    ordinal: int,
    *,
    column: str | None,
) -> str:
    if column:
        return f"page {page_number}, {column} column, text block {ordinal}"
    return f"page {page_number}, {kind.value} block {ordinal}"


def _intersection_over_union(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    if intersection == 0:
        return 0.0
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    return intersection / (first_area + second_area - intersection)


def _text_near_rect(page: pymupdf.Page, rect: pymupdf.Rect) -> str:
    expanded = pymupdf.Rect(
        max(page.rect.x0, rect.x0 - 36),
        max(page.rect.y0, rect.y0 - 36),
        min(page.rect.x1, rect.x1 + 36),
        min(page.rect.y1, rect.y1 + 72),
    )
    return _normalize_text(page.get_text("text", clip=expanded, sort=True))


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
