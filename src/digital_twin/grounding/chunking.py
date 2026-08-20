import hashlib

from src.digital_twin.grounding.models import (
    CourseDocument,
    DocumentChunk,
    DocumentRegion,
    DocumentSegment,
    ParsedDocumentBundle,
)


class HeadingParagraphChunker:
    """Deterministic character-bounded chunking over parsed content units."""

    def __init__(self, *, max_chars: int = 1200, overlap_chars: int = 160) -> None:
        if max_chars < 128:
            raise ValueError("max_chars must be at least 128")
        if overlap_chars < 0 or overlap_chars >= max_chars:
            raise ValueError("overlap_chars must be non-negative and below max_chars")
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, document: CourseDocument) -> list[DocumentChunk]:
        source_segments = document.segments or [
            DocumentSegment(text=document.text, locator=document.locator)
        ]
        units = [
            unit
            for segment in source_segments
            for unit in self._bounded_segments(segment)
        ]
        groups = self._group_with_overlap(units)

        chunks: list[DocumentChunk] = []
        for ordinal, group in enumerate(groups):
            text = "\n\n".join(segment.text for segment in group)
            locator = _group_locator(group)
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            chunk_id = _chunk_id(document.id, ordinal, locator, content_hash)
            pages = [segment.page for segment in group if segment.page is not None]
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    document_id=document.id,
                    text=text,
                    ordinal=ordinal,
                    source_artifact_id=document.source_artifact_id,
                    source_version=document.source_version,
                    source_label=document.source_label,
                    content_hash=content_hash,
                    locator=locator,
                    page_start=min(pages) if pages else None,
                    page_end=max(pages) if pages else None,
                    retrieval_allowed=document.permissions.tutoring_allowed,
                    display_allowed=document.permissions.display_allowed,
                    metadata={
                        **document.metadata,
                        "title": document.title,
                        "source_label": document.source_label.value,
                        "source_artifact_id": document.source_artifact_id
                        or document.id,
                        "source_version": str(document.source_version),
                        "document_content_hash": document.content_hash or "",
                        "locator": locator,
                        "retrieval_allowed": str(
                            document.permissions.tutoring_allowed
                        ).lower(),
                        "display_allowed": str(
                            document.permissions.display_allowed
                        ).lower(),
                    },
                )
            )
        return chunks

    def _bounded_segments(self, segment: DocumentSegment) -> list[DocumentSegment]:
        if len(segment.text) <= self.max_chars:
            return [segment]

        words = segment.text.split()
        parts: list[str] = []
        current: list[str] = []
        for word in words:
            if current and len(" ".join([*current, word])) > self.max_chars:
                parts.append(" ".join(current))
                current = []
            if len(word) > self.max_chars:
                if current:
                    parts.append(" ".join(current))
                    current = []
                parts.extend(
                    word[start : start + self.max_chars]
                    for start in range(0, len(word), self.max_chars)
                )
            else:
                current.append(word)
        if current:
            parts.append(" ".join(current))

        return [
            segment.model_copy(
                update={
                    "text": part,
                    "locator": f"{segment.locator}, part {ordinal}",
                }
            )
            for ordinal, part in enumerate(parts, start=1)
        ]

    def _group_with_overlap(
        self,
        units: list[DocumentSegment],
    ) -> list[list[DocumentSegment]]:
        groups: list[list[DocumentSegment]] = []
        start = 0
        while start < len(units):
            end = start
            length = 0
            while end < len(units):
                separator = 2 if end > start else 0
                candidate_length = length + separator + len(units[end].text)
                if end > start and candidate_length > self.max_chars:
                    break
                length = candidate_length
                end += 1
            groups.append(units[start:end])
            if end == len(units):
                break

            overlap_start = end
            overlap_length = 0
            while overlap_start > start:
                candidate = units[overlap_start - 1]
                extra = len(candidate.text) + (2 if overlap_length else 0)
                if overlap_length + extra > self.overlap_chars:
                    break
                overlap_start -= 1
                overlap_length += extra
            start = max(start + 1, overlap_start)
        return groups


class PageBoundedHeadingParagraphChunker:
    """Apply heading/paragraph chunking without combining separate PDF pages."""

    def __init__(self, *, max_chars: int = 1200, overlap_chars: int = 160) -> None:
        self._chunker = HeadingParagraphChunker(
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )

    def chunk(self, document: CourseDocument) -> list[DocumentChunk]:
        paged_segments = [
            segment for segment in document.segments if segment.page is not None
        ]
        if not paged_segments:
            return self._chunker.chunk(document)
        if len(paged_segments) != len(document.segments):
            raise ValueError(
                "page-bounded chunking requires every document segment to have "
                "a page or none of them to have a page"
            )

        segments_by_page: dict[int, list[DocumentSegment]] = {}
        for segment in paged_segments:
            if segment.page is None:
                raise AssertionError("paged segment unexpectedly has no page")
            segments_by_page.setdefault(segment.page, []).append(segment)

        chunks: list[DocumentChunk] = []
        ordinal = 0
        for page, segments in sorted(segments_by_page.items()):
            page_document = document.model_copy(
                update={
                    "text": "\n\n".join(segment.text for segment in segments),
                    "segments": segments,
                    "locator": f"page {page}",
                }
            )
            for provisional in self._chunker.chunk(page_document):
                content_hash = (
                    provisional.content_hash
                    or hashlib.sha256(provisional.text.encode("utf-8")).hexdigest()
                )
                chunks.append(
                    provisional.model_copy(
                        update={
                            "id": _chunk_id(
                                document.id,
                                ordinal,
                                provisional.locator or f"page {page}",
                                content_hash,
                            ),
                            "ordinal": ordinal,
                        }
                    )
                )
                ordinal += 1
        return chunks


class RegionAwareChunker:
    """Create one lineage-preserving retrieval unit per extracted page region."""

    def chunk(self, bundle: ParsedDocumentBundle) -> list[DocumentChunk]:
        if not bundle.regions:
            return PageBoundedHeadingParagraphChunker().chunk(bundle.document)

        chunks: list[DocumentChunk] = []
        for region in sorted(
            bundle.regions,
            key=lambda item: (item.page, item.reading_order, item.id),
        ):
            authoritative_text = _structured_region_text(region)
            search_description = region.description.strip()
            if not authoritative_text and not search_description:
                continue
            text = authoritative_text or (
                "This visual-only region requires direct inspection of its cited crop."
            )
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            search_content_hash = hashlib.sha256(
                f"{text}\x1f{search_description}".encode("utf-8")
            ).hexdigest()
            ordinal = len(chunks)
            chunks.append(
                DocumentChunk(
                    id=_chunk_id(
                        bundle.document.id,
                        ordinal,
                        region.locator,
                        search_content_hash,
                    ),
                    document_id=bundle.document.id,
                    text=text,
                    ordinal=ordinal,
                    source_artifact_id=region.source_artifact_id,
                    source_version=region.source_version,
                    source_label=bundle.document.source_label,
                    content_hash=content_hash,
                    locator=region.locator,
                    page_start=region.page,
                    page_end=region.page,
                    region_id=region.id,
                    region_kind=region.kind,
                    bounding_box=region.bounding_box,
                    crop_ref=region.crop_ref,
                    source_checksum=region.source_checksum,
                    region_checksum=region.checksum,
                    description_method=region.description_method,
                    retrieval_allowed=region.permissions.tutoring_allowed,
                    display_allowed=region.permissions.display_allowed,
                    metadata={
                        **bundle.document.metadata,
                        **region.metadata,
                        "title": bundle.document.title,
                        "source_label": bundle.document.source_label.value,
                        "source_artifact_id": region.source_artifact_id,
                        "source_version": str(region.source_version),
                        "source_checksum": region.source_checksum,
                        "document_content_hash": (bundle.document.content_hash or ""),
                        "locator": region.locator,
                        "region_id": region.id,
                        "region_kind": region.kind.value,
                        "region_checksum": region.checksum,
                        "crop_ref": region.crop_ref,
                        "parent_region_id": region.parent_region_id or "",
                        "description_is_authoritative": "false",
                        "search_description": search_description,
                        "search_content_hash": search_content_hash,
                        "retrieval_allowed": str(
                            region.permissions.tutoring_allowed
                        ).lower(),
                        "display_allowed": str(
                            region.permissions.display_allowed
                        ).lower(),
                    },
                )
            )
        return chunks


def _structured_region_text(region: DocumentRegion) -> str:
    if region.kind.value == "table-cell":
        row_header = region.metadata.get("row_header", "").strip()
        column_header = region.metadata.get("column_header", "").strip()
        labels = []
        if row_header and row_header != region.text:
            labels.append(f"Row: {row_header}")
        if column_header and column_header != region.text:
            labels.append(f"Column: {column_header}")
        labels.append(f"Value: {region.text}")
        return ". ".join(labels)
    if region.kind.value == "table-row":
        headers = region.metadata.get("column_headers", "").strip()
        return f"Columns: {headers}. Row: {region.text}" if headers else region.text
    if region.kind.value == "equation":
        return f"Defined equation formula: {region.text}"
    return region.text.strip()


def _group_locator(group: list[DocumentSegment]) -> str:
    first = group[0].locator
    last = group[-1].locator
    return first if first == last else f"{first} - {last}"


def _chunk_id(
    document_id: str,
    ordinal: int,
    locator: str,
    content_hash: str,
) -> str:
    identity = f"{document_id}\x1f{ordinal}\x1f{locator}\x1f{content_hash}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"chunk-{digest[:24]}"
