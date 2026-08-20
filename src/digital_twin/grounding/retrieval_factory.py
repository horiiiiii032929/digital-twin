import math
from collections.abc import Mapping, Sequence

from src.digital_twin.evaluation import (
    ComponentKind,
    ComponentProfileEntry,
    ComponentStatus,
    ImplementationRef,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.protocols import Retriever, TextEmbedder
from src.digital_twin.grounding.retrieval import (
    BM25Retriever,
    DenseRetriever,
    ReciprocalRankFusionRetriever,
    TermOverlapRetriever,
)
from src.digital_twin.grounding.retrieval_runtime import FallbackRetriever


class UnsupportedRetrieverSelectionError(ValueError):
    pass


def build_selected_retriever(
    selection: ComponentProfileEntry,
    chunks: Sequence[DocumentChunk],
    *,
    active_source_versions: Mapping[str, int] | None = None,
    embedder: TextEmbedder | None = None,
    allow_control_fallback: bool = True,
) -> Retriever:
    """Resolve one profile entry behind an explicit provider boundary.

    A selected provider-backed method requires an injected embedder. When it is
    unavailable or fails during indexing/querying, the selected profile's
    control is returned through ``FallbackRetriever`` when fallback is enabled.
    """

    if selection.component != ComponentKind.RETRIEVER:
        raise UnsupportedRetrieverSelectionError("profile entry is not a retriever")
    if selection.status != ComponentStatus.SELECTED or selection.implementation is None:
        raise UnsupportedRetrieverSelectionError("retriever is not selected")

    implementation = selection.implementation
    if implementation.version not in {"v1", "cross-course-retrieval-v1"}:
        raise UnsupportedRetrieverSelectionError("unsupported retriever version")

    if implementation.implementation_id in {
        "term-overlap",
        "term-overlap-v1",
        "bm25",
        "bm25-v1",
    }:
        return _build_implementation(
            implementation,
            chunks,
            active_source_versions=active_source_versions,
        )

    if implementation.implementation_id != "qwen3-hybrid-v1":
        raise UnsupportedRetrieverSelectionError(
            f"unsupported retriever: {implementation.implementation_id}"
        )

    if not allow_control_fallback:
        if embedder is None:
            raise UnsupportedRetrieverSelectionError(
                "qwen3 hybrid retrieval requires an injected embedder"
            )
        return _build_implementation(
            implementation,
            chunks,
            active_source_versions=active_source_versions,
            embedder=embedder,
        )

    if selection.control is None:
        raise UnsupportedRetrieverSelectionError(
            "provider-backed retrieval requires an explicit control"
        )
    fallback = _build_implementation(
        selection.control,
        chunks,
        active_source_versions=active_source_versions,
    )
    if embedder is None:
        return FallbackRetriever(
            None,
            fallback,
            primary_implementation_id=implementation.implementation_id,
            fallback_implementation_id=selection.control.implementation_id,
            initialization_failure_type="embedder-not-configured",
        )

    try:
        primary = _build_implementation(
            implementation,
            chunks,
            active_source_versions=active_source_versions,
            embedder=embedder,
        )
    except UnsupportedRetrieverSelectionError:
        raise
    except (RuntimeError, ValueError) as error:
        return FallbackRetriever(
            None,
            fallback,
            primary_implementation_id=implementation.implementation_id,
            fallback_implementation_id=selection.control.implementation_id,
            initialization_failure_type=type(error).__name__,
        )
    return FallbackRetriever(
        primary,
        fallback,
        primary_implementation_id=implementation.implementation_id,
        fallback_implementation_id=selection.control.implementation_id,
    )


def _build_implementation(
    implementation: ImplementationRef,
    chunks: Sequence[DocumentChunk],
    *,
    active_source_versions: Mapping[str, int] | None,
    embedder: TextEmbedder | None = None,
) -> Retriever:
    if implementation.version not in {"v1", "cross-course-retrieval-v1"}:
        raise UnsupportedRetrieverSelectionError("unsupported retriever version")

    if implementation.implementation_id in {"term-overlap", "term-overlap-v1"}:
        _validate_configuration(
            implementation.configuration,
            allowed={"tokenizer"},
        )
        return TermOverlapRetriever(
            chunks,
            active_source_versions=active_source_versions,
        )
    if implementation.implementation_id in {"bm25", "bm25-v1"}:
        _validate_configuration(
            implementation.configuration,
            allowed={"tokenizer", "k1", "b", "minimum_score"},
        )
        return BM25Retriever(
            chunks,
            k1=_numeric_configuration(implementation.configuration, "k1", 1.2),
            b=_numeric_configuration(implementation.configuration, "b", 0.75),
            minimum_score=_numeric_configuration(
                implementation.configuration, "minimum_score", 0.0
            ),
            active_source_versions=active_source_versions,
        )
    if implementation.implementation_id == "qwen3-hybrid-v1":
        _validate_configuration(
            implementation.configuration,
            allowed={
                "method",
                "provider_pair",
                "embedding_provider",
                "embedding_model",
                "embedding_revision",
                "embedding_execution",
                "query_instruction",
                "device",
                "dtype",
                "embedding_max_length",
                "embedding_batch_size",
                "bm25_k1",
                "bm25_b",
                "tokenizer",
                "fusion_rank_constant",
                "fusion_candidate_limit",
                "result_limit",
                "reranker",
            },
        )
        if implementation.configuration.get("method") != "M2":
            raise UnsupportedRetrieverSelectionError(
                "qwen3 hybrid selection must declare method M2"
            )
        _require_configuration_value(
            implementation.configuration,
            "provider_pair",
            "local-qwen3-0-6b",
        )
        _require_configuration_value(
            implementation.configuration,
            "embedding_provider",
            "local-huggingface",
        )
        _require_configuration_value(
            implementation.configuration,
            "embedding_model",
            "Qwen/Qwen3-Embedding-0.6B",
        )
        _require_configuration_value(
            implementation.configuration,
            "embedding_revision",
            "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
        )
        _require_configuration_value(
            implementation.configuration,
            "embedding_execution",
            "local",
        )
        _require_configuration_value(
            implementation.configuration,
            "query_instruction",
            (
                "Given a student question within one authorized university course, "
                "retrieve passages that directly support a grounded answer."
            ),
        )
        _require_configuration_value(
            implementation.configuration,
            "device",
            "mps",
        )
        _require_configuration_value(
            implementation.configuration,
            "dtype",
            "float16",
        )
        _require_configuration_value(
            implementation.configuration,
            "embedding_max_length",
            2048,
        )
        _require_configuration_value(
            implementation.configuration,
            "embedding_batch_size",
            16,
        )
        _require_configuration_value(
            implementation.configuration,
            "result_limit",
            10,
        )
        _require_configuration_value(
            implementation.configuration,
            "reranker",
            "none",
        )
        if embedder is None:
            raise UnsupportedRetrieverSelectionError(
                "qwen3 hybrid retrieval requires an injected embedder"
            )
        _validate_embedder_binding(embedder, implementation.configuration)
        bm25 = BM25Retriever(
            chunks,
            k1=_numeric_configuration(implementation.configuration, "bm25_k1", 1.2),
            b=_numeric_configuration(implementation.configuration, "bm25_b", 0.75),
            active_source_versions=active_source_versions,
        )
        dense = DenseRetriever(
            chunks,
            embedder,
            minimum_similarity=-1.0,
            active_source_versions=active_source_versions,
        )
        return ReciprocalRankFusionRetriever(
            [bm25, dense],
            rank_constant=_integer_configuration(
                implementation.configuration,
                "fusion_rank_constant",
                60,
            ),
            candidate_limit=_integer_configuration(
                implementation.configuration,
                "fusion_candidate_limit",
                20,
            ),
        )
    raise UnsupportedRetrieverSelectionError(
        f"unsupported retriever: {implementation.implementation_id}"
    )


def _validate_configuration(
    configuration: dict[str, str | int | float | bool],
    *,
    allowed: set[str],
) -> None:
    unknown = set(configuration) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise UnsupportedRetrieverSelectionError(
            f"unsupported retriever configuration: {names}"
        )
    tokenizer = configuration.get("tokenizer", "lowercase-alphanumeric")
    if tokenizer != "lowercase-alphanumeric":
        raise UnsupportedRetrieverSelectionError("unsupported retriever tokenizer")


def _numeric_configuration(
    configuration: dict[str, str | int | float | bool],
    name: str,
    default: float,
) -> float:
    value = configuration.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UnsupportedRetrieverSelectionError(
            f"retriever configuration {name} must be numeric"
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise UnsupportedRetrieverSelectionError(
            f"retriever configuration {name} must be finite"
        )
    return numeric


def _require_configuration_value(
    configuration: dict[str, str | int | float | bool],
    name: str,
    expected: str | int | float | bool,
) -> None:
    if configuration.get(name) != expected:
        raise UnsupportedRetrieverSelectionError(
            f"retriever configuration {name} must be {expected}"
        )


def _integer_configuration(
    configuration: dict[str, str | int | float | bool],
    name: str,
    default: int,
) -> int:
    value = configuration.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise UnsupportedRetrieverSelectionError(
            f"retriever configuration {name} must be an integer"
        )
    if value < 1:
        raise UnsupportedRetrieverSelectionError(
            f"retriever configuration {name} must be at least 1"
        )
    return value


def _validate_embedder_binding(
    embedder: TextEmbedder,
    configuration: dict[str, str | int | float | bool],
) -> None:
    expected = {
        "provider_id": configuration["embedding_provider"],
        "model_name": configuration["embedding_model"],
        "model_revision": configuration["embedding_revision"],
        "execution": configuration["embedding_execution"],
        "instruction": configuration["query_instruction"],
        "device": configuration["device"],
        "dtype": configuration["dtype"],
        "max_length": configuration["embedding_max_length"],
        "batch_size": configuration["embedding_batch_size"],
    }
    mismatched = [
        name
        for name, expected_value in expected.items()
        if getattr(embedder, name, None) != expected_value
    ]
    if mismatched:
        names = ", ".join(mismatched)
        raise UnsupportedRetrieverSelectionError(
            f"injected embedder does not match selected profile: {names}"
        )
