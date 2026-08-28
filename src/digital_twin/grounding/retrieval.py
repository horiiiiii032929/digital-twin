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


class _ZeroMagnitudeEmbeddingError(ValueError):
    pass


def lexical_tokens(value: str) -> list[str]:
    """Return deterministic, provider-independent lowercase lexical tokens."""

    return _TOKEN_PATTERN.findall(value.lower())


def retrieval_text(chunk: DocumentChunk) -> str:
    """Combine citable text with explicitly non-authoritative search metadata."""

    description = chunk.metadata.get("search_description", "").strip()
    return f"{chunk.text}\n\n{description}" if description else chunk.text


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
            chunk.id: set(lexical_tokens(retrieval_text(chunk)))
            for chunk in self.chunks
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
        if not math.isfinite(k1) or k1 <= 0:
            raise ValueError("k1 must be positive")
        if not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")
        if not math.isfinite(minimum_score) or minimum_score < 0:
            raise ValueError("minimum_score cannot be negative")

        self.k1 = k1
        self.b = b
        self.minimum_score = minimum_score
        self.chunks = _eligible_chunks(chunks, active_source_versions)
        self._term_frequencies = {
            chunk.id: Counter(lexical_tokens(retrieval_text(chunk)))
            for chunk in self.chunks
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

    @classmethod
    def from_index(
        cls,
        chunks: Sequence[DocumentChunk],
        *,
        term_frequencies: Mapping[str, Mapping[str, int]],
        document_lengths: Mapping[str, int],
        document_frequencies: Mapping[str, int],
        average_document_length: float,
        k1: float = 1.2,
        b: float = 0.75,
        minimum_score: float = 0.0,
    ) -> "BM25Retriever":
        """Load a validated lexical index without tokenizing the corpus again."""

        instance = cls([], k1=k1, b=b, minimum_score=minimum_score)
        eligible = _eligible_chunks(chunks, None)
        identifiers = [chunk.id for chunk in eligible]
        if len(identifiers) != len(chunks) or len(identifiers) != len(set(identifiers)):
            raise ValueError("indexed chunks must be unique and retrieval-eligible")
        expected = set(identifiers)
        if (
            set(term_frequencies) != expected
            or set(document_lengths) != expected
        ):
            raise ValueError("lexical index chunk identifiers do not match the corpus")

        normalized_frequencies: dict[str, Counter[str]] = {}
        normalized_lengths: dict[str, int] = {}
        recomputed_document_frequencies: Counter[str] = Counter()
        for identifier in identifiers:
            frequencies = term_frequencies[identifier]
            if any(
                not isinstance(term, str)
                or not term
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 1
                for term, count in frequencies.items()
            ):
                raise ValueError("lexical index contains an invalid term frequency")
            counter = Counter(frequencies)
            length = document_lengths[identifier]
            if (
                isinstance(length, bool)
                or not isinstance(length, int)
                or length != sum(counter.values())
            ):
                raise ValueError("lexical index document length is inconsistent")
            normalized_frequencies[identifier] = counter
            normalized_lengths[identifier] = length
            recomputed_document_frequencies.update(counter.keys())

        if any(
            not isinstance(term, str)
            or not term
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 1
            for term, count in document_frequencies.items()
        ):
            raise ValueError("lexical index contains an invalid document frequency")
        if Counter(document_frequencies) != recomputed_document_frequencies:
            raise ValueError("lexical index document frequencies are inconsistent")
        recomputed_average = (
            sum(normalized_lengths.values()) / len(normalized_lengths)
            if normalized_lengths
            else 0.0
        )
        if (
            not math.isfinite(average_document_length)
            or not math.isclose(
                average_document_length,
                recomputed_average,
                rel_tol=0,
                abs_tol=1e-12,
            )
        ):
            raise ValueError("lexical index average document length is inconsistent")

        instance.chunks = eligible
        instance._term_frequencies = normalized_frequencies
        instance._document_lengths = normalized_lengths
        instance._average_document_length = recomputed_average
        instance._document_frequencies = recomputed_document_frequencies
        return instance

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
        if not math.isfinite(minimum_similarity) or not -1 <= minimum_similarity <= 1:
            raise ValueError("minimum_similarity must be between -1 and 1")
        self.chunks = _eligible_chunks(chunks, active_source_versions)
        self.embedder = embedder
        self.minimum_similarity = minimum_similarity
        vectors = (
            embedder.embed_documents([retrieval_text(chunk) for chunk in self.chunks])
            if self.chunks
            else []
        )
        if len(vectors) != len(self.chunks):
            raise ValueError("embedder returned the wrong number of document vectors")
        normalized_vectors = [_normalized_vector(vector) for vector in vectors]
        dimensions = {len(vector) for vector in normalized_vectors}
        if len(dimensions) > 1:
            raise ValueError("embedder returned inconsistent document dimensions")
        self._dimension = next(iter(dimensions), None)
        self._vectors = dict(
            zip(
                (chunk.id for chunk in self.chunks),
                normalized_vectors,
                strict=True,
            )
        )

    @classmethod
    def from_index(
        cls,
        chunks: Sequence[DocumentChunk],
        embedder: TextEmbedder,
        *,
        vectors: Mapping[str, Sequence[float]],
        minimum_similarity: float = -1.0,
    ) -> "DenseRetriever":
        """Load document vectors while retaining the embedder only for queries."""

        instance = cls([], embedder, minimum_similarity=minimum_similarity)
        eligible = _eligible_chunks(chunks, None)
        identifiers = [chunk.id for chunk in eligible]
        if len(identifiers) != len(chunks) or len(identifiers) != len(set(identifiers)):
            raise ValueError("indexed chunks must be unique and retrieval-eligible")
        if set(vectors) != set(identifiers):
            raise ValueError("dense index chunk identifiers do not match the corpus")
        normalized_vectors = {
            identifier: _normalized_vector(vectors[identifier])
            for identifier in identifiers
        }
        dimensions = {len(vector) for vector in normalized_vectors.values()}
        if len(dimensions) > 1:
            raise ValueError("dense index contains inconsistent vector dimensions")

        instance.chunks = eligible
        instance._dimension = next(iter(dimensions), None)
        instance._vectors = normalized_vectors
        return instance

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        _validate_limit(limit)
        if not lexical_tokens(query):
            raise EmptyQueryError("query must contain at least one lexical token")
        if not self.chunks:
            return []
        raw_query_vector = self.embedder.embed_query(query)
        try:
            query_vector = _normalized_vector(raw_query_vector)
        except _ZeroMagnitudeEmbeddingError:
            return []
        if self._dimension is not None and len(query_vector) != self._dimension:
            raise ValueError("query embedding dimension does not match the index")
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
        if isinstance(rank_constant, bool) or rank_constant < 1:
            raise ValueError("rank_constant must be at least 1")
        if isinstance(candidate_limit, bool) or candidate_limit < 1:
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
            identifiers = [hit.chunk.id for hit in hits]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(
                    "a fused retriever returned duplicate chunk identifiers"
                )
            for rank, hit in enumerate(hits, start=1):
                identifier = hit.chunk.id
                existing = chunks.get(identifier)
                if existing is not None and existing != hit.chunk:
                    raise ValueError(
                        "fused retrievers disagreed on authoritative chunk content"
                    )
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
        if (
            not math.isfinite(minimum_relevance_score)
            or not 0 <= minimum_relevance_score <= 1
        ):
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
            hit for hit in hits if hit.relevance_score >= self.minimum_relevance_score
        ][:limit]


def _normalized_vector(vector: Sequence[float]) -> list[float]:
    try:
        values = [float(value) for value in vector]
    except (TypeError, ValueError) as error:
        raise ValueError("embedding vectors must be numeric") from error
    if not values:
        raise ValueError("embedding vectors cannot be empty")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("embedding vectors must contain only finite values")
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude == 0:
        raise _ZeroMagnitudeEmbeddingError(
            "embedding vectors cannot have zero magnitude"
        )
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
    if isinstance(limit, bool) or limit < 1:
        raise InvalidRetrievalLimitError("retrieval limit must be at least 1")


def _ranked_hits(
    normalized_scores: list[tuple[float, DocumentChunk]],
    *,
    limit: int,
    raw_scores: list[tuple[float, DocumentChunk]] | None = None,
) -> list[RetrievalHit]:
    if any(
        not math.isfinite(score) or not 0 <= score <= 1
        for score, _ in normalized_scores
    ):
        raise ValueError(
            "normalized retrieval scores must be finite and between 0 and 1"
        )
    if raw_scores is not None and any(
        not math.isfinite(score) or score < 0 for score, _ in raw_scores
    ):
        raise ValueError("raw retrieval scores must be finite and non-negative")
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
