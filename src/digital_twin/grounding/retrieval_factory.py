from collections.abc import Mapping, Sequence

from src.digital_twin.evaluation import (
    ComponentKind,
    ComponentProfileEntry,
    ComponentStatus,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.protocols import Retriever
from src.digital_twin.grounding.retrieval import BM25Retriever, TermOverlapRetriever


class UnsupportedRetrieverSelectionError(ValueError):
    pass


def build_selected_retriever(
    selection: ComponentProfileEntry,
    chunks: Sequence[DocumentChunk],
    *,
    active_source_versions: Mapping[str, int] | None = None,
) -> Retriever:
    """Resolve one validated retriever profile entry outside orchestration code."""

    if selection.component != ComponentKind.RETRIEVER:
        raise UnsupportedRetrieverSelectionError("profile entry is not a retriever")
    if selection.status != ComponentStatus.SELECTED or selection.implementation is None:
        raise UnsupportedRetrieverSelectionError("retriever is not selected")

    implementation = selection.implementation
    if implementation.version != "v1":
        raise UnsupportedRetrieverSelectionError("unsupported retriever version")

    if implementation.implementation_id == "term-overlap":
        _validate_configuration(
            implementation.configuration,
            allowed={"tokenizer"},
        )
        return TermOverlapRetriever(
            chunks,
            active_source_versions=active_source_versions,
        )
    if implementation.implementation_id == "bm25":
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
    return float(value)
