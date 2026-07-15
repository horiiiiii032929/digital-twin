import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence

from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.protocols import Retriever, TextEmbedder


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


class RetrievalError(ValueError):
    """Base class for explicit retrieval input failures."""


class EmptyQueryError(RetrievalError):
    pass


class InvalidRetrievalLimitError(RetrievalError):
    pass


def lexical_tokens(value: str) -> list[str]:
    """Return deterministic, provider-independent lowercase lexical tokens."""

    return _TOKEN_PATTERN.findall(value.lower())


class TermOverlapRetriever:
    """Rank approved chunks by the fraction of unique query terms matched."""

    def __init__(
        self,
        chunks: Sequence[DocumentChunk],
        *,
        active_source_versions: Mapping[str, int] | None = None,
    ) -> None:
        self.chunks = _eligible_chunks(chunks, active_source_versions)
        self._terms = {
            chunk.id: set(lexical_tokens(chunk.text)) for chunk in self.chunks
        }

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        _validate_limit(limit)
        query_terms = set(lexical_tokens(query))
        if not query_terms:
            raise EmptyQueryError("query must contain at least one lexical token")

        scored = []
        for chunk in self.chunks:
            overlap = query_terms & self._terms[chunk.id]
            if overlap:
                scored.append((len(overlap) / len(query_terms), chunk))
        return _ranked_hits(scored, limit=limit)


class BM25Retriever:
    """Inspectable Okapi BM25 ranking over approved, active source chunks."""

    def __init__(
        self,
        chunks: Sequence[DocumentChunk],
        *,
        k1: float = 1.2,
        b: float = 0.75,
        minimum_score: float = 0.0,
        active_source_versions: Mapping[str, int] | None = None,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")
        if minimum_score < 0:
            raise ValueError("minimum_score cannot be negative")

        self.k1 = k1
        self.b = b
        self.minimum_score = minimum_score
        self.chunks = _eligible_chunks(chunks, active_source_versions)
        self._term_frequencies = {
            chunk.id: Counter(lexical_tokens(chunk.text)) for chunk in self.chunks
        }
        self._document_lengths = {
            chunk.id: sum(self._term_frequencies[chunk.id].values())
            for chunk in self.chunks
        }
        self._average_document_length = (
            sum(self._document_lengths.values()) / len(self.chunks)
            if self.chunks
            else 0.0
        )
        self._document_frequencies = self._build_document_frequencies()

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        _validate_limit(limit)
        query_terms = sorted(set(lexical_tokens(query)))
        if not query_terms:
            raise EmptyQueryError("query must contain at least one lexical token")
        if not self.chunks:
            return []

        raw_scores = []
        for chunk in self.chunks:
            score = self._score(chunk, query_terms)
            if score > 0 and score >= self.minimum_score:
                raw_scores.append((score, chunk))
        if not raw_scores:
            return []

        maximum = max(score for score, _ in raw_scores)
        normalized = [(score / maximum, chunk) for score, chunk in raw_scores]
        return _ranked_hits(normalized, limit=limit, raw_scores=raw_scores)

    def _build_document_frequencies(self) -> Counter[str]:
        frequencies: Counter[str] = Counter()
        for term_frequency in self._term_frequencies.values():
            frequencies.update(term_frequency.keys())
        return frequencies

    def _score(self, chunk: DocumentChunk, query_terms: list[str]) -> float:
        term_frequency = self._term_frequencies[chunk.id]
        document_length = self._document_lengths[chunk.id]
        score = 0.0
        for term in query_terms:
            frequency = term_frequency[term]
            if frequency == 0:
                continue
            document_frequency = self._document_frequencies[term]
            inverse_document_frequency = math.log(
                1
                + (len(self.chunks) - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            length_ratio = (
                document_length / self._average_document_length
                if self._average_document_length
                else 0.0
            )
            denominator = frequency + self.k1 * (1 - self.b + self.b * length_ratio)
            score += inverse_document_frequency * (
                frequency * (self.k1 + 1) / denominator
            )
        return score


class DenseRetriever:
    """Rank approved chunks by cosine similarity from an injected embedder."""

    def __init__(
        self,
        chunks: Sequence[DocumentChunk],
        embedder: TextEmbedder,
        *,
        minimum_similarity: float = -1.0,
        active_source_versions: Mapping[str, int] | None = None,
    ) -> None:
        if not -1 <= minimum_similarity <= 1:
            raise ValueError("minimum_similarity must be between -1 and 1")
        self.chunks = _eligible_chunks(chunks, active_source_versions)
        self.embedder = embedder
        self.minimum_similarity = minimum_similarity
        vectors = embedder.embed_documents([chunk.text for chunk in self.chunks])
        if len(vectors) != len(self.chunks):
            raise ValueError("embedder returned the wrong number of document vectors")
        self._vectors = {
            chunk.id: _normalized_vector(vector)
            for chunk, vector in zip(self.chunks, vectors, strict=True)
        }

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        _validate_limit(limit)
        if not lexical_tokens(query):
            raise EmptyQueryError("query must contain at least one lexical token")
        if not self.chunks:
            return []
        raw_query_vector = self.embedder.embed_query(query)
        if not raw_query_vector or not any(float(value) for value in raw_query_vector):
            return []
        query_vector = _normalized_vector(raw_query_vector)
        scored: list[tuple[float, DocumentChunk]] = []
        for chunk in self.chunks:
            similarity = sum(
                left * right
                for left, right in zip(
                    query_vector,
                    self._vectors[chunk.id],
                    strict=True,
                )
            )
            if similarity >= self.minimum_similarity:
                normalized_similarity = min(1.0, max(0.0, (similarity + 1) / 2))
                scored.append((normalized_similarity, chunk))
        return _ranked_hits(scored, limit=limit)


class ReciprocalRankFusionRetriever:
    """Fuse candidate ranks without assuming comparable relevance scores."""

    def __init__(
        self,
        retrievers: Sequence[Retriever],
        *,
        rank_constant: int = 60,
        candidate_limit: int = 20,
    ) -> None:
        if len(retrievers) < 2:
            raise ValueError("reciprocal rank fusion requires at least two retrievers")
        if rank_constant < 1:
            raise ValueError("rank_constant must be at least 1")
        if candidate_limit < 1:
            raise ValueError("candidate_limit must be at least 1")
        self.retrievers = list(retrievers)
        self.rank_constant = rank_constant
        self.candidate_limit = candidate_limit

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        _validate_limit(limit)
        fused_scores: dict[str, float] = {}
        chunks: dict[str, DocumentChunk] = {}
        for retriever in self.retrievers:
            hits = retriever.retrieve(query, limit=max(limit, self.candidate_limit))
            for rank, hit in enumerate(hits, start=1):
                identifier = hit.chunk.id
                chunks[identifier] = hit.chunk
                fused_scores[identifier] = fused_scores.get(identifier, 0.0) + 1 / (
                    self.rank_constant + rank
                )
        if not fused_scores:
            return []
        maximum = max(fused_scores.values())
        normalized = [
            (score / maximum, chunks[identifier])
            for identifier, score in fused_scores.items()
        ]
        raw = [
            (score, chunks[identifier]) for identifier, score in fused_scores.items()
        ]
        return _ranked_hits(normalized, limit=limit, raw_scores=raw)


class RelevanceThresholdRetriever:
    """Suppress low-confidence hits without coupling calibration to a ranker."""

    def __init__(
        self,
        retriever: Retriever,
        *,
        minimum_relevance_score: float,
        candidate_limit: int = 100,
    ) -> None:
        if not 0 <= minimum_relevance_score <= 1:
            raise ValueError("minimum_relevance_score must be between 0 and 1")
        if candidate_limit < 1:
            raise ValueError("candidate_limit must be at least 1")
        self.retriever = retriever
        self.minimum_relevance_score = minimum_relevance_score
        self.candidate_limit = candidate_limit

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        _validate_limit(limit)
        hits = self.retriever.retrieve(
            query,
            limit=max(limit, self.candidate_limit),
        )
        return [
            hit
            for hit in hits
            if hit.relevance_score >= self.minimum_relevance_score
        ][:limit]


def _normalized_vector(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    if not values:
        raise ValueError("embedding vectors cannot be empty")
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude == 0:
        raise ValueError("embedding vectors cannot have zero magnitude")
    return [value / magnitude for value in values]


def _eligible_chunks(
    chunks: Sequence[DocumentChunk],
    active_source_versions: Mapping[str, int] | None,
) -> list[DocumentChunk]:
    allowed = [chunk for chunk in chunks if chunk.retrieval_allowed]
    if active_source_versions is None:
        active_source_versions = {}
        for chunk in allowed:
            source_id = chunk.source_artifact_id or chunk.document_id
            active_source_versions[source_id] = max(
                chunk.source_version,
                active_source_versions.get(source_id, 0),
            )

    eligible = [
        chunk
        for chunk in allowed
        if active_source_versions.get(chunk.source_artifact_id or chunk.document_id)
        == chunk.source_version
    ]
    identifiers = [chunk.id for chunk in eligible]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("retrieval chunk identifiers must be unique")
    return sorted(eligible, key=_chunk_tie_breaker)


def _validate_limit(limit: int) -> None:
    if limit < 1:
        raise InvalidRetrievalLimitError("retrieval limit must be at least 1")


def _ranked_hits(
    normalized_scores: list[tuple[float, DocumentChunk]],
    *,
    limit: int,
    raw_scores: list[tuple[float, DocumentChunk]] | None = None,
) -> list[RetrievalHit]:
    raw_by_chunk = (
        {chunk.id: score for score, chunk in raw_scores}
        if raw_scores is not None
        else {chunk.id: score for score, chunk in normalized_scores}
    )
    ranked = sorted(
        normalized_scores,
        key=lambda item: (-raw_by_chunk[item[1].id], *_chunk_tie_breaker(item[1])),
    )
    return [
        RetrievalHit(
            chunk=chunk,
            relevance_score=score,
            raw_score=raw_by_chunk[chunk.id],
        )
        for score, chunk in ranked[:limit]
    ]


def _chunk_tie_breaker(chunk: DocumentChunk) -> tuple[str, str, int, str]:
    return (
        chunk.source_artifact_id or chunk.document_id,
        chunk.document_id,
        chunk.ordinal,
        chunk.id,
    )
