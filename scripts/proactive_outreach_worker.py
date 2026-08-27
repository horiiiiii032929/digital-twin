"""Materialize due, consented proactive messages without external delivery."""

from __future__ import annotations

import argparse
import time

from services.api.app.config import AppSettings, RuntimeMode
from src.digital_twin.student import ProactiveOutreachService, SQLiteStudentRepository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds must be positive")
    if not 1 <= args.batch_size <= 500:
        raise SystemExit("--batch-size must be between 1 and 500")

    settings = AppSettings.from_env()
    if settings.mode != RuntimeMode.STAGING:
        raise SystemExit("APP_MODE=staging is required for the outreach worker")
    if not settings.proactive_outreach_worker_enabled:
        raise SystemExit(
            "APP_PROACTIVE_OUTREACH_WORKER_ENABLED=true is required for the outreach worker"
        )

    repository = SQLiteStudentRepository(settings.database_path)
    service = ProactiveOutreachService(repository)
    try:
        while True:
            service.process_due(limit=args.batch_size)
            if args.once:
                return
            time.sleep(args.poll_seconds)
    finally:
        repository.close()


if __name__ == "__main__":
    main()
