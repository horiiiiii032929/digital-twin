"""Run due governed-autonomy jobs and professor-scheduled A0 outreach."""

from __future__ import annotations

import argparse
import asyncio
import socket
import time

from services.api.app.config import AppSettings, RuntimeMode
from services.api.app.factory import create_app


async def _process_once(app, *, worker_id: str, batch_size: int) -> None:
    await app.state.governed_autonomy_service.process_due(
        worker_id=worker_id,
        limit=batch_size,
    )
    app.state.proactive_outreach_service.process_due(limit=batch_size)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--worker-id", default=f"autonomy-worker:{socket.gethostname()}")
    args = parser.parse_args()
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds must be positive")
    if not 1 <= args.batch_size <= 500:
        raise SystemExit("--batch-size must be between 1 and 500")
    if not args.worker_id.strip() or len(args.worker_id) > 128:
        raise SystemExit("--worker-id must be 1-128 characters")

    settings = AppSettings.from_env()
    if settings.mode != RuntimeMode.STAGING:
        raise SystemExit("APP_MODE=staging is required for the autonomy worker")
    if not settings.proactive_outreach_worker_enabled:
        raise SystemExit(
            "APP_PROACTIVE_OUTREACH_WORKER_ENABLED=true is required for the autonomy worker"
        )
    app = create_app(settings=settings)
    repository = app.state.student_repository
    try:
        while True:
            asyncio.run(
                _process_once(
                    app,
                    worker_id=args.worker_id.strip(),
                    batch_size=args.batch_size,
                )
            )
            if args.once:
                return
            time.sleep(args.poll_seconds)
    finally:
        close = getattr(repository, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":
    main()
