"""Deterministic query routing over offline region-text indexes."""

from __future__ import annotations

from enum import StrEnum

from src.digital_twin.grounding.models import (
    DocumentChunk,
    RegionKind,
    RetrievalHit,
)
from src.digital_twin.grounding.retrieval import BM25Retriever, lexical_tokens


class RegionRoute(StrEnum):
    GENERAL = "general"
    TABLE = "table"
    DIAGRAM = "diagram"
    EQUATION = "equation"
    VISUAL_TEXT = "visual-text"


class ModalityAwareRegionRetriever:
    """Route textual queries to small modality indexes with a general fallback."""

    implementation_id = "modality-aware-region-bm25"
    version = "v1"

    _ROUTE_KINDS = {
        RegionRoute.DIAGRAM: {RegionKind.DIAGRAM},
        RegionRoute.EQUATION: {RegionKind.EQUATION},
        RegionRoute.VISUAL_TEXT: {
            RegionKind.OCR,
            RegionKind.SCREENSHOT,
            RegionKind.FIGURE,
            RegionKind.DIAGRAM,
        },
    }

    def __init__(self, chunks: list[DocumentChunk]) -> None:
        general_kinds = {
            None,
            RegionKind.PAGE,
            RegionKind.TEXT,
            RegionKind.COLUMN,
            RegionKind.HEADING,
            RegionKind.CAPTION,
            RegionKind.OCR,
        }
        general_chunks = [
            chunk for chunk in chunks if chunk.region_kind in general_kinds
        ]
        table_chunks = [chunk for chunk in chunks if _is_answer_bearing_table(chunk)]
        self._general = BM25Retriever(general_chunks)
        self._routed = {
            route: BM25Retriever(
                [chunk for chunk in chunks if chunk.region_kind in kinds]
            )
            for route, kinds in self._ROUTE_KINDS.items()
        }
        self._routed[RegionRoute.TABLE] = BM25Retriever(table_chunks)
        self.index_sizes = {
            RegionRoute.GENERAL.value: len(general_chunks),
            RegionRoute.TABLE.value: len(table_chunks),
            **{
                route.value: len(retriever.chunks)
                for route, retriever in self._routed.items()
                if route != RegionRoute.TABLE
            },
        }
        self.last_route = RegionRoute.GENERAL

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        route = classify_region_query(query)
        self.last_route = route
        if route != RegionRoute.GENERAL:
            routed_hits = self._routed[route].retrieve(query, limit=limit)
            if routed_hits:
                return routed_hits
        return self._general.retrieve(query, limit=limit)


def classify_region_query(query: str) -> RegionRoute:
    terms = set(lexical_tokens(query))
    if terms & {"table", "row", "column", "score", "value", "recall"} or any(
        marker in query.casefold() for marker in ("complete@", "recall@")
    ):
        return RegionRoute.TABLE
    if terms & {"diagram", "flow", "stage", "arrow", "follows"} or {
        "order",
        "index",
    } <= terms:
        return RegionRoute.DIAGRAM
    if terms & {"equation", "throughput", "formula", "defined"} or (
        "total" in terms and "latency" in terms
    ):
        return RegionRoute.EQUATION
    if terms & {
        "screenshot",
        "dashboard",
        "visual",
        "scan",
        "scanned",
        "ocr",
    } or ({"online", "vision"} <= terms) or ({"query", "time"} <= terms):
        return RegionRoute.VISUAL_TEXT
    return RegionRoute.GENERAL


def _is_answer_bearing_table(chunk: DocumentChunk) -> bool:
    if chunk.region_kind == RegionKind.TABLE:
        return True
    if chunk.region_kind != RegionKind.TABLE_CELL:
        return False
    try:
        row = int(chunk.metadata.get("row_ordinal", "0"))
        column = int(chunk.metadata.get("column_ordinal", "0"))
    except ValueError:
        return False
    return row > 1 and column > 1
