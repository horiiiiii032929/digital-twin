import base64
from datetime import UTC, datetime
from pathlib import Path

import pymupdf

from src.digital_twin.grounding import (
    ApprovalDecision,
    ApprovalRecord,
    SourceArtifact,
    SourcePermissions,
    SourceSensitivity,
    source_artifact_from_path,
)
from src.digital_twin.tutor_policy import SourceLabel


_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8A"
    "AQUBAScY42YAAAAASUVORK5CYII="
)


def write_synthetic_pdf(
    path: Path,
    *,
    with_text: bool = True,
    with_figure: bool = True,
) -> None:
    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    if with_text:
        page.insert_text((72, 72), "Synthetic network security course notes")
        page.insert_text(
            (72, 110),
            "CSRF abuses an authenticated browser session.",
        )
    if with_figure:
        page.insert_image(
            pymupdf.Rect(72, 150, 216, 246),
            stream=_ONE_PIXEL_PNG,
        )
        if with_text:
            page.insert_text((72, 270), "Figure 1: Synthetic request flow")
    pdf.save(path, no_new_id=True)
    pdf.close()


def approved_source(
    path: Path,
    *,
    version: int = 1,
    permissions: SourcePermissions | None = None,
    sensitivity: SourceSensitivity = SourceSensitivity.STANDARD,
    excluded: bool = False,
) -> tuple[SourceArtifact, ApprovalRecord]:
    source = source_artifact_from_path(
        path,
        artifact_id="synthetic-course-source",
        title="Synthetic network security notes",
        version=version,
        source_label=SourceLabel.COURSE_APPROVED,
        provider_role="professor",
        sensitivity=sensitivity,
        excluded=excluded,
    )
    approval = ApprovalRecord(
        id=f"approval-{version}",
        source_artifact_id=source.id,
        source_version=source.version,
        decision=ApprovalDecision.APPROVED,
        permissions=permissions
        or SourcePermissions(
            processing_allowed=True,
            tutoring_allowed=True,
            display_allowed=False,
        ),
        reviewer_id="synthetic-professor",
        reviewer_role="professor",
        reviewed_at=datetime(2026, 7, 14, tzinfo=UTC),
        notes="Synthetic fixture approval only.",
    )
    return source, approval
