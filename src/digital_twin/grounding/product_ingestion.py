"""Release-ready local ingestion orchestration for approved course PDFs."""

from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from src.digital_twin.grounding.chunking import RegionAwareChunker
from src.digital_twin.grounding.ingestion import (
    LocalDocumentParser,
    LocalFigureStore,
    LocalRegionCropStore,
)
from src.digital_twin.grounding.models import (
    ApprovalDecision,
    ApprovalRecord,
    DocumentChunk,
    ParsedDocumentBundle,
    SourceArtifact,
    SourcePermissions,
    SourceSensitivity,
)
from src.digital_twin.grounding.protocols import (
    OCRProvider,
    RegionDescriptionProvider,
)
from src.digital_twin.tutor_policy import SourceLabel, infer_sensitive_source_name


class CourseSourceIngestionResult(BaseModel):
    source: SourceArtifact
    approval: ApprovalRecord
    bundle: ParsedDocumentBundle
    chunks: list[DocumentChunk] = Field(default_factory=list)
    stored_source_ref: str = Field(min_length=1)


class LocalCourseSourceIngestionService:
    """Synchronously ingest one bounded PDF for the local product foundation.

    Production deployment will move this operation to the job and object-storage
    boundary tracked separately. The domain result is already portable.
    """

    def __init__(
        self,
        source_root: Path,
        region_crop_root: Path,
        *,
        ocr_provider: OCRProvider | None = None,
        description_provider: RegionDescriptionProvider | None = None,
        max_source_bytes: int = 50 * 1024 * 1024,
    ) -> None:
        if (
            isinstance(max_source_bytes, bool)
            or not isinstance(max_source_bytes, int)
            or max_source_bytes <= 0
        ):
            raise ValueError("max_source_bytes must be positive")
        self.source_root = source_root
        self.region_crop_root = region_crop_root
        self.ocr_provider = ocr_provider
        self.description_provider = description_provider
        self.max_source_bytes = max_source_bytes

    def ingest_pdf(
        self,
        content: bytes,
        *,
        course_id: str,
        artifact_id: str,
        title: str,
        version: int,
        professor_id: str,
        permissions: SourcePermissions,
        source_label: SourceLabel = SourceLabel.COURSE_APPROVED,
    ) -> CourseSourceIngestionResult:
        if not content:
            raise ValueError("uploaded PDF is empty")
        if len(content) > self.max_source_bytes:
            raise ValueError("uploaded PDF exceeds the configured size limit")
        if version < 1:
            raise ValueError("source version must be at least 1")
        if not all(
            value.strip() for value in (course_id, artifact_id, title, professor_id)
        ):
            raise ValueError(
                "course, source, title, and professor identifiers are required"
            )
        if source_label == SourceLabel.UNAPPROVED_EXTERNAL:
            raise ValueError(
                "unapproved external sources cannot be ingested for tutoring"
            )
        if infer_sensitive_source_name(title) or infer_sensitive_source_name(
            artifact_id
        ):
            raise ValueError(
                "potentially sensitive student or private sources require a separate "
                "consent-reviewed ingestion path"
            )

        checksum = hashlib.sha256(content).hexdigest()
        source_identity = f"{course_id}:{artifact_id}"
        source = SourceArtifact(
            id=source_identity,
            title=title.strip(),
            mime_type="application/pdf",
            checksum=checksum,
            version=version,
            source_label=source_label,
            storage_ref=f"local-source://{course_id}/{artifact_id}/v{version}",
            provider_role="professor",
            sensitivity=SourceSensitivity.STANDARD,
        )
        approval = ApprovalRecord(
            id=_stable_id("approval", source_identity, str(version), checksum),
            source_artifact_id=source.id,
            source_version=version,
            decision=ApprovalDecision.APPROVED,
            permissions=permissions,
            reviewer_id=professor_id,
            reviewer_role="professor",
            reviewed_at=datetime.now(UTC),
            notes="Explicit professor approval captured by course ingestion.",
        )

        self.source_root.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="course-source-",
            suffix=".pdf",
            dir=self.source_root,
        )
        temporary_path = Path(temporary_name)
        figure_store = LocalFigureStore(self.region_crop_root / "figures")
        region_store = LocalRegionCropStore(self.region_crop_root)
        created_derived_paths: list[Path] = []
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
            parser = LocalDocumentParser(
                figure_store,
                region_store=region_store,
                ocr_provider=self.ocr_provider,
                description_provider=self.description_provider,
            )
            bundle = parser.parse(temporary_path, source, approval)
            chunks = [
                chunk.model_copy(
                    update={
                        "metadata": {
                            **chunk.metadata,
                            "course_id": course_id,
                            "ingestion_mode": "region-aware-offline",
                        }
                    },
                    deep=True,
                )
                for chunk in RegionAwareChunker().chunk(bundle)
            ]
            final_name = _stable_id(
                "source",
                course_id,
                artifact_id,
                str(version),
                checksum,
            )
            final_path = self.source_root / f"{final_name}.pdf"
            if final_path.is_symlink():
                raise ValueError("stored source path is a symbolic link")
            if final_path.exists():
                if hashlib.sha256(final_path.read_bytes()).hexdigest() != checksum:
                    raise ValueError("stored source identity has conflicting content")
                temporary_path.unlink()
            else:
                os.chmod(temporary_path, 0o600)
                temporary_path.replace(final_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            created_derived_paths.extend(figure_store.created_paths)
            created_derived_paths.extend(region_store.created_paths)
            for path in reversed(created_derived_paths):
                path.unlink(missing_ok=True)
            raise

        return CourseSourceIngestionResult(
            source=source,
            approval=approval,
            bundle=bundle,
            chunks=chunks,
            stored_source_ref=f"source://{final_path.name}",
        )


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:24]}"
