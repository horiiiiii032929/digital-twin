"""Deterministic, lineage-preserving source representations for retrieval.

The citable source text remains authoritative.  These helpers add only
non-authoritative search metadata so lexical and embedding retrievers can use
the same section, course, modality, and identifier context that a student sees.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import hashlib
import re

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.tutor_policy import SourceLabel


_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*|[A-Za-z_][A-Za-z0-9_]*\([^\n)]{0,80}\)")
_GENERIC = frozenset(
    {
        "about",
        "adds",
        "also",
        "another",
        "answer",
        "course",
        "detail",
        "does",
        "example",
        "explains",
        "fact",
        "from",
        "gives",
        "material",
        "point",
        "returns",
        "section",
        "selected",
        "source",
        "state",
        "states",
        "statement",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "uses",
        "using",
        "what",
        "when",
        "where",
        "which",
        "with",
    }
)


def semantic_anchors(values: Iterable[str], *, limit: int = 12) -> list[str]:
    """Return stable, context-bearing anchors without inventing semantics."""

    if limit < 1:
        raise ValueError("semantic anchor limit must be positive")
    candidates: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    ordinal = 0
    for value in values:
        for match in _TOKEN.finditer(value):
            token = match.group(0).strip()
            normalized = token.casefold()
            if (
                normalized in seen
                or normalized in _GENERIC
                or len(normalized) < 2
                or normalized.isdigit()
            ):
                continue
            seen.add(normalized)
            identifier_like = bool(
                "_" in token
                or "-" in token
                or "(" in token
                or any(character.isdigit() for character in token)
                or any(character.isupper() for character in token[1:])
            )
            specificity = 3 if identifier_like else 2 if len(normalized) >= 7 else 1
            candidates.append((-specificity, ordinal, token))
            ordinal += 1
    return [row[2] for row in sorted(candidates)[:limit]]


def registered_search_description(
    *,
    course_id: str,
    section_heading: str,
    source_path: str,
    modality: str,
    text: str,
) -> str:
    """Build a compact, deterministic search-only representation."""

    required = {
        "course_id": course_id,
        "section_heading": section_heading,
        "source_path": source_path,
        "modality": modality,
        "text": text,
    }
    if any(not value.strip() for value in required.values()):
        missing = sorted(name for name, value in required.items() if not value.strip())
        raise ValueError(f"source registration fields cannot be blank: {missing}")
    anchors = semantic_anchors((section_heading, text), limit=12)
    source_name = Path(source_path).stem.replace("_", " ").replace("-", " ")
    rows = [
        f"Course: {course_id}",
        f"Section: {section_heading}",
        f"Source: {source_name}",
        f"Modality: {modality}",
    ]
    if anchors:
        rows.append("Semantic anchors: " + ", ".join(anchors))
    return "\n".join(rows)


def canonical_region_id(
    *,
    source_artifact_id: str,
    source_version: int,
    source_sha256: str,
    char_start: int,
    char_end: int,
    modality: str,
) -> str:
    """Return a source-derived region identity independent of cases/questions."""

    if source_version < 1 or char_start < 0 or char_end <= char_start:
        raise ValueError("canonical region lineage is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("canonical region source hash must be SHA-256")
    payload = "\x1f".join(
        (
            source_artifact_id,
            str(source_version),
            source_sha256,
            str(char_start),
            str(char_end),
            modality,
        )
    )
    return "source-region-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def registered_source_chunks(clusters: Iterable[object]) -> list[DocumentChunk]:
    """Materialize exact citable regions with contextual search metadata.

    ``clusters`` may contain Pydantic source-cluster objects or their JSON
    mappings.  Every emitted chunk is an exact reference span, never a
    question-derived window.
    """

    rows: list[dict[str, object]] = []
    for cluster in clusters:
        value = cluster.model_dump(mode="json") if hasattr(cluster, "model_dump") else cluster
        if not isinstance(value, dict):
            raise TypeError("registered source clusters must be mappings or Pydantic models")
        rows.append(value)
    output: list[DocumentChunk] = []
    seen: set[str] = set()
    ordinals: dict[str, int] = {}
    for cluster in sorted(rows, key=lambda row: str(row["cluster_id"])):
        course_id = str(cluster["course_id"])
        cluster_start = int(cluster["char_start"])
        cluster_text = str(cluster["text"])
        for target in cluster["reference_targets"]:  # type: ignore[index]
            if not isinstance(target, dict):
                raise TypeError("reference target must be a mapping")
            modality = str(target["modality"])
            for span in target["evidence_spans"]:  # type: ignore[index]
                if not isinstance(span, dict):
                    raise TypeError("reference evidence span must be a mapping")
                start = cluster_start + int(span["relative_char_start"])
                end = cluster_start + int(span["relative_char_end"])
                quote = str(span["quote"])
                relative_start = int(span["relative_char_start"])
                relative_end = int(span["relative_char_end"])
                if cluster_text[relative_start:relative_end] != quote:
                    raise ValueError("registered region quote does not match source text")
                region_id = canonical_region_id(
                    source_artifact_id=str(cluster["source_artifact_id"]),
                    source_version=int(cluster["source_version"]),
                    source_sha256=str(cluster["source_sha256"]),
                    char_start=start,
                    char_end=end,
                    modality=modality,
                )
                if region_id in seen:
                    continue
                seen.add(region_id)
                ordinal = ordinals.get(course_id, 0)
                ordinals[course_id] = ordinal + 1
                output.append(
                    DocumentChunk(
                        id=region_id,
                        document_id=str(cluster["source_artifact_id"]),
                        text=quote,
                        ordinal=ordinal,
                        source_artifact_id=str(cluster["source_artifact_id"]),
                        source_version=int(cluster["source_version"]),
                        source_label=SourceLabel.COURSE_APPROVED,
                        locator=(
                            f"{cluster['source_path']} characters {start}–{end}"
                        ),
                        region_id=region_id,
                        source_checksum=str(cluster["source_sha256"]),
                        retrieval_allowed=True,
                        display_allowed=True,
                        metadata={
                            "title": str(cluster["section_heading"]),
                            "course_id": course_id,
                            "char_start": str(start),
                            "char_end": str(end),
                            "source_path": str(cluster["source_path"]),
                            "source_family_id": str(cluster["source_family_id"]),
                            "parent_cluster_id": str(cluster["cluster_id"]),
                            "modality": modality,
                            "search_description": registered_search_description(
                                course_id=course_id,
                                section_heading=str(cluster["section_heading"]),
                                source_path=str(cluster["source_path"]),
                                modality=modality,
                                text=cluster_text,
                            ),
                        },
                    )
                )
    return sorted(output, key=lambda chunk: (chunk.metadata["course_id"], chunk.ordinal))


__all__ = [
    "canonical_region_id",
    "registered_search_description",
    "registered_source_chunks",
    "semantic_anchors",
]
