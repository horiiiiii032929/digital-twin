"""Persistent, bounded clarification for genuinely ambiguous evidence."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.digital_twin.grounding.models import DocumentChunk


class ClarificationStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ClarificationOptionV1(BaseModel):
    """One source-derived interpretation; it never contains hidden gold."""

    model_config = ConfigDict(extra="forbid")

    option_id: str = Field(pattern=r"^option-[1-5]$")
    label: str = Field(min_length=1, max_length=240)
    source_chunk_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_version: int = Field(ge=1)
    source_checksum: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    region_id: str | None = None
    locator: str = Field(min_length=1)
    claim_class_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ClarificationRequestV1(BaseModel):
    """A single pending mixed-initiative turn bound to immutable course scope."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    original_student_message_id: str = Field(min_length=1)
    original_question_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    options: list[ClarificationOptionV1] = Field(min_length=2, max_length=5)
    status: ClarificationStatus = ClarificationStatus.PENDING
    selected_option_id: str | None = None
    resolved_by_message_id: str | None = None
    created_at: str
    expires_at: str
    resolved_at: str | None = None

    @field_validator("created_at", "expires_at", "resolved_at")
    @classmethod
    def timestamps_are_utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("clarification timestamps must include a timezone")
        return parsed.astimezone(UTC).isoformat()

    @model_validator(mode="after")
    def lifecycle_is_consistent(self) -> "ClarificationRequestV1":
        option_ids = [option.option_id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("clarification option IDs must be unique")
        if datetime.fromisoformat(self.expires_at) <= datetime.fromisoformat(
            self.created_at
        ):
            raise ValueError("clarification expiry must follow creation")
        resolution = (
            self.selected_option_id,
            self.resolved_by_message_id,
            self.resolved_at,
        )
        if self.status == ClarificationStatus.RESOLVED:
            if any(value is None for value in resolution):
                raise ValueError("resolved clarification requires complete lineage")
            if self.selected_option_id not in option_ids:
                raise ValueError("resolved option is not part of the request")
        elif any(value is not None for value in resolution):
            raise ValueError("only a resolved clarification may carry a selection")
        return self


def build_clarification_request(
    *,
    conversation_id: str,
    student_id: str,
    course_id: str,
    release_id: str,
    original_student_message_id: str,
    original_question: str,
    chunks: Sequence[DocumentChunk],
    created_at: str,
    ttl: timedelta = timedelta(hours=24),
) -> ClarificationRequestV1:
    """Build two-to-five stable options from authorized source metadata only."""

    created = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(UTC)
    if ttl <= timedelta(0):
        raise ValueError("clarification TTL must be positive")
    unique: list[DocumentChunk] = []
    seen_claims: set[str] = set()
    for chunk in chunks:
        if not (chunk.retrieval_allowed and chunk.source_artifact_id and chunk.locator):
            continue
        claim = str(chunk.metadata.get("semantic_atom_claim", chunk.text)).strip()
        claim_hash = hashlib.sha256(claim.casefold().encode("utf-8")).hexdigest()
        if claim_hash in seen_claims:
            continue
        seen_claims.add(claim_hash)
        unique.append(chunk)
        if len(unique) == 5:
            break
    if len(unique) < 2:
        raise ValueError("a targeted clarification requires two source interpretations")
    labels = _unique_source_labels(unique)
    options = [
        ClarificationOptionV1(
            option_id=f"option-{index}",
            label=labels[index - 1],
            source_chunk_id=chunk.id,
            source_artifact_id=chunk.source_artifact_id or chunk.document_id,
            source_version=chunk.source_version,
            source_checksum=chunk.source_checksum,
            region_id=chunk.region_id,
            locator=chunk.locator or f"chunk {chunk.ordinal + 1}",
            claim_class_sha256=hashlib.sha256(
                str(chunk.metadata.get("semantic_atom_claim", chunk.text))
                .strip()
                .casefold()
                .encode("utf-8")
            ).hexdigest(),
        )
        for index, chunk in enumerate(unique, start=1)
    ]
    request_key = "\x1f".join(
        [
            conversation_id,
            original_student_message_id,
            *(row.source_chunk_id for row in options),
        ]
    )
    return ClarificationRequestV1(
        request_id="clarification-"
        + hashlib.sha256(request_key.encode()).hexdigest()[:24],
        conversation_id=conversation_id,
        student_id=student_id,
        course_id=course_id,
        release_id=release_id,
        original_student_message_id=original_student_message_id,
        original_question_sha256=hashlib.sha256(
            original_question.strip().encode("utf-8")
        ).hexdigest(),
        options=options,
        created_at=created.isoformat(),
        expires_at=(created + ttl).isoformat(),
    )


def render_clarification_prompt(request: ClarificationRequestV1) -> str:
    lines = ["I found more than one supported interpretation. Which one do you mean?"]
    lines.extend(
        f"{index}. {option.label}"
        for index, option in enumerate(request.options, start=1)
    )
    lines.append("Reply with the number or option label. I will clarify only once.")
    return "\n".join(lines)


def resolve_clarification_option(
    request: ClarificationRequestV1,
    reply: str,
) -> ClarificationOptionV1 | None:
    """Resolve only an explicit number, option ID, or unambiguous full label."""

    normalized = " ".join(reply.casefold().strip().split())
    number = re.fullmatch(r"(?:option[ -]?)?([1-5])(?:[.)])?", normalized)
    if number:
        index = int(number.group(1)) - 1
        return request.options[index] if index < len(request.options) else None
    exact = [
        option
        for option in request.options
        if normalized
        in {
            option.option_id.casefold(),
            " ".join(option.label.casefold().split()),
        }
    ]
    return exact[0] if len(exact) == 1 else None


def _unique_source_labels(chunks: Sequence[DocumentChunk]) -> list[str]:
    bases: list[str] = []
    for chunk in chunks:
        title = str(chunk.metadata.get("title", "")).strip()
        section = str(chunk.metadata.get("section", "")).strip()
        # Never expose a filesystem or ingestion path in a student-facing
        # clarification label.  Titles, section names, and approved locators
        # are already part of the product's citation surface.
        parts = [value for value in (title, section) if value]
        bases.append(" · ".join(parts) or (chunk.locator or "Approved source passage"))
    counts = {value: bases.count(value) for value in bases}
    return [
        value
        if counts[value] == 1
        else f"{value} · {chunk.locator or f'passage {chunk.ordinal + 1}'}"
        for value, chunk in zip(bases, chunks, strict=True)
    ]


__all__ = [
    "ClarificationOptionV1",
    "ClarificationRequestV1",
    "ClarificationStatus",
    "build_clarification_request",
    "render_clarification_prompt",
    "resolve_clarification_option",
]
