from src.digital_twin.generation.models import EvidenceBinding
from src.digital_twin.grounding.models import SourceCitation


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

        by_id = {binding.citation_id: binding for binding in evidence}
        unknown = set(citation_ids) - set(by_id)
        if unknown:
            raise CitationValidationError("citation does not map to retrieved evidence")

        citations: list[SourceCitation] = []
        for citation_id in citation_ids:
            chunk = by_id[citation_id].hit.chunk
            if not chunk.retrieval_allowed:
                raise CitationValidationError("citation maps to unapproved evidence")
            citations.append(
                SourceCitation(
                    source_id=chunk.document_id,
                    title=chunk.metadata.get("title") or chunk.document_id,
                    locator=chunk.locator or f"chunk {chunk.ordinal + 1}",
                )
            )
        return citations
