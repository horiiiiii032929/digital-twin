"""Isolated, network-free product runtime for recording rehearsals.

Uses the ordinary API and UI in their explicit synthetic demo mode. This is
not the qualified R1 deployment. A new process starts with empty courses.
"""
from pathlib import Path
import tempfile
from datetime import UTC, datetime
from src.digital_twin.clock import VirtualUtcClock
from scripts.recording_controls import install_controls
from src.digital_twin.student import SQLiteStudentRepository

from services.api.app.config import AppSettings, EvidenceGateMode, StudentTutoringMode
from services.api.app.factory import create_app
from src.digital_twin.student.models import Account, AccountRole

ACTORS = (
    ("Professor A", "professor-synthetic", 5178, "professor"),
    ("Professor B", "professor-b-recording", 5179, "professor"),
    ("Student A1", "student-a-synthetic", 5180, "student"),
    ("Student A2", "student-a2-recording", 5181, "student"),
    ("Student B1", "student-b-synthetic", 5182, "student"),
    ("Student B2", "student-b2-recording", 5183, "student"),
)


def make_recording_app(root: Path):
    settings = AppSettings(
        data_root=root,
        learning_gap_hmac_secret=b"synthetic-recording-only-not-a-private-key",
        database_path=root / "recording.sqlite3",
        allowed_origins=tuple(f"http://127.0.0.1:{actor[2]}" for actor in ACTORS),
        evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3,
        student_tutoring_mode=StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
    )
    clock = VirtualUtcClock(datetime(2026, 9, 7, 12, tzinfo=UTC))
    app = create_app(settings=settings, clock=clock, student_repository=SQLiteStudentRepository(settings.database_path), source_root=root / "sources",
                     region_crop_root=root / "regions")
    for _, account_id, _, role in ACTORS:
        app.state.student_repository.save_account(Account(id=account_id, role=AccountRole(role)))
    install_controls(app, clock)
    return app


def create_recording_app():
    temporary = tempfile.TemporaryDirectory(prefix="digital-twin-recording-ui-")
    app = make_recording_app(Path(temporary.name))
    # Keep the directory alive for the process; restarting resets this sandbox.
    app.state.recording_temporary = temporary
    return app
