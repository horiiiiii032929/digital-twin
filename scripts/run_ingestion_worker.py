"""Run the durable single-host ingestion worker."""

from __future__ import annotations

import argparse
import socket
import time
from uuid import uuid4

from services.api.app.config import AppSettings, RuntimeMode
from services.ingestion import IngestionJobService
from services.persistence import SQLiteIngestionJobRepository
from services.storage import FileSystemObjectStore
from src.digital_twin.grounding import LocalCourseSourceIngestionService
from src.digital_twin.student import SQLiteStudentRepository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    args = parser.parse_args()
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds must be positive")
    settings = AppSettings.from_env()
    if settings.mode != RuntimeMode.STAGING:
        raise SystemExit("APP_MODE=staging is required for the ingestion worker")

    students = SQLiteStudentRepository(settings.database_path)
    jobs = SQLiteIngestionJobRepository(settings.database_path)
    service = IngestionJobService(
        jobs,
        FileSystemObjectStore(
            settings.object_root, max_bytes=settings.max_object_store_bytes
        ),
        LocalCourseSourceIngestionService(
            settings.source_root,
            settings.region_crop_root,
            max_source_bytes=settings.max_upload_bytes,
        ),
        max_upload_bytes=settings.max_upload_bytes,
    )
    worker_id = f"{socket.gethostname()}-{uuid4()}"
    try:
        while True:
            processed = service.process_one(worker_id)
            if args.once:
                return
            if processed is None:
                time.sleep(args.poll_seconds)
    finally:
        jobs.close()
        students.close()


if __name__ == "__main__":
    main()
