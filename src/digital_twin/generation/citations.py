from src.digital_twin.generation.models import EvidenceBinding
from src.digital_twin.grounding.models import DocumentChunk, SourceCitation


class CitationValidationError(ValueError):
    pass


class DeterministicCitationValidator:
    implementation_id = "deterministic-citation-validator"
    version = "v1"

    def validate(
        self,
        citation_ids: list[str],
        evidence: list[EvidenceBinding],
        *,
        require_citation: bool = True,
    ) -> list[SourceCitation]:
        if len(citation_ids) != len(set(citation_ids)):
            raise CitationValidationError("duplicate citation identifier")
        if require_citation and not citation_ids:
            raise CitationValidationError("grounded answer requires a citation")

        evidence_ids = [binding.citation_id for binding in evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise CitationValidationError("duplicate evidence citation identifier")
        by_id = {binding.citation_id: binding for binding in evidence}
        unknown = set(citation_ids) - set(by_id)
        if unknown:
            raise CitationValidationError("citation does not map to retrieved evidence")

        citations: list[SourceCitation] = []
        for citation_id in citation_ids:
            chunk = by_id[citation_id].hit.chunk
            if not chunk.retrieval_allowed:
                raise CitationValidationError("citation maps to unapproved evidence")
            citations.append(authoritative_citation_for_chunk(chunk))
        return citations


def authoritative_citation_for_chunk(chunk: DocumentChunk) -> SourceCitation:
    """Build the only citation representation accepted for a retrieved chunk."""

    if not chunk.retrieval_allowed:
        raise CitationValidationError("citation maps to unapproved evidence")
    return SourceCitation(
        source_id=chunk.document_id,
        title=chunk.metadata.get("title") or chunk.document_id,
        locator=chunk.locator or f"chunk {chunk.ordinal + 1}",
        source_artifact_id=chunk.source_artifact_id,
        source_version=chunk.source_version,
        source_checksum=chunk.source_checksum,
        page=chunk.page_start,
        region_id=chunk.region_id,
        region_kind=chunk.region_kind,
        bounding_box=chunk.bounding_box,
        crop_ref=chunk.crop_ref if chunk.display_allowed else None,
    )


def citation_matches_chunk(citation: SourceCitation, chunk: DocumentChunk) -> bool:
    """Require exact authoritative lineage, not only a display locator match."""

    if not chunk.retrieval_allowed:
        return False
    expected = authoritative_citation_for_chunk(chunk)
    return (
        citation.source_id == expected.source_id
        and citation.locator == expected.locator
        and citation.source_artifact_id == expected.source_artifact_id
        and citation.source_version == expected.source_version
        and citation.source_checksum == expected.source_checksum
        and citation.page == expected.page
        and citation.region_id == expected.region_id
        and citation.region_kind == expected.region_kind
        and citation.bounding_box == expected.bounding_box
        and citation.crop_ref == expected.crop_ref
    )
