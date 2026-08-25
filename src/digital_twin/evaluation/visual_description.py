"""Provider-neutral visual-description contracts for grounded retrieval.

Visual descriptions are advisory retrieval metadata.  They never replace the
original asset, become authoritative truth, or receive a citation identity of
their own.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol, Sequence


class VisualDescriptionError(ValueError):
    """Raised when a visual description violates its source binding."""


@dataclass(frozen=True)
class VisualRegionLineage:
    source_id: str
    asset_id: str
    region_id: str
    image_sha256: str
    bbox: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        if len(self.image_sha256) != 64:
            raise VisualDescriptionError("image SHA-256 must contain 64 characters")
        if len(self.bbox) != 4 or any(value < 0 or value > 1 for value in self.bbox):
            raise VisualDescriptionError("region bounding box must be normalized")
        x, y, width, height = self.bbox
        if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise VisualDescriptionError("region bounding box is invalid")


@dataclass(frozen=True)
class VisualDescription:
    transcription: str
    entities: tuple[str, ...]
    relationships: tuple[str, ...]
    uncertainty: tuple[str, ...]
    provider_model: str
    provider_revision: str | None
    provider_name: str
    source_image_sha256: str
    region_lineage: tuple[VisualRegionLineage, ...]

    def __post_init__(self) -> None:
        if not self.provider_model or not self.provider_name:
            raise VisualDescriptionError("provider identity is required")
        if len(self.source_image_sha256) != 64:
            raise VisualDescriptionError("source image SHA-256 is invalid")
        if not self.region_lineage:
            raise VisualDescriptionError("at least one original region is required")
        if any(
            region.image_sha256 != self.source_image_sha256
            for region in self.region_lineage
        ):
            raise VisualDescriptionError("description and region image hashes differ")
        if len(self.entities) != len(set(self.entities)):
            raise VisualDescriptionError("visual entities must be unique")
        if len(self.relationships) != len(set(self.relationships)):
            raise VisualDescriptionError("visual relationships must be unique")

    def retrieval_text(self) -> str:
        """Return advisory text without changing citation authority."""

        parts = [self.transcription.strip()]
        parts.extend(value.strip() for value in self.entities)
        parts.extend(value.strip() for value in self.relationships)
        return "\n".join(value for value in parts if value)

    def to_record(self) -> dict[str, object]:
        return asdict(self)


class VisualDescriptionProvider(Protocol):
    """Question-independent visual description interface."""

    implementation_id: str

    async def describe(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        regions: Sequence[VisualRegionLineage],
    ) -> VisualDescription: ...
