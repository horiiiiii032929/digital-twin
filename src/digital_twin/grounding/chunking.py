import hashlib

from src.digital_twin.grounding.models import (
    CourseDocument,
    DocumentChunk,
    DocumentSegment,
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
                    metadata={
                        **document.metadata,
                        "title": document.title,
                        "source_label": document.source_label.value,
                        "source_artifact_id": document.source_artifact_id or document.id,
                        "source_version": str(document.source_version),
                        "document_content_hash": document.content_hash or "",
                        "locator": locator,
                        "retrieval_allowed": str(
                            document.permissions.tutoring_allowed
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
