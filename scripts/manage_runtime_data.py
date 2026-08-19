"""Run explicit staging retention, export, and deletion operations."""

from __future__ import annotations

import argparse
from pathlib import Path

from services.api.app.config import AppSettings, RuntimeMode
from services.operations import (
    delete_account_data,
    delete_course_data,
    export_account_data,
    prune_runtime_data,
)
from services.storage import FileSystemObjectStore


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export-account")
    export.add_argument("--account-id", required=True)
    export.add_argument("--output", type=Path, required=True)
    prune = commands.add_parser("prune")
    prune.add_argument("--terminal-job-days", type=int, default=30)
    prune.add_argument("--audit-days", type=int, default=365)
    delete_account = commands.add_parser("delete-account")
    delete_account.add_argument("--account-id", required=True)
    delete_account.add_argument("--confirm", required=True)
    delete_course = commands.add_parser("delete-course")
    delete_course.add_argument("--course-id", required=True)
    delete_course.add_argument("--confirm", required=True)
    args = parser.parse_args()

    settings = AppSettings.from_env()
    if settings.mode != RuntimeMode.STAGING:
        raise SystemExit("APP_MODE=staging is required for lifecycle operations")
    store = FileSystemObjectStore(settings.object_root)

    if args.command == "export-account":
        payload = export_account_data(
            settings.database_path, args.account_id, args.output
        )
        print(
            f"Exported account {payload['account']['account_id']} to a mode-0600 file; "
            "password and session credentials were excluded."
        )
    elif args.command == "prune":
        result = prune_runtime_data(
            settings.database_path,
            store,
            terminal_job_days=args.terminal_job_days,
            audit_days=args.audit_days,
        )
        print(result.model_dump_json())
    elif args.command == "delete-account":
        if args.confirm != args.account_id:
            raise SystemExit("--confirm must exactly match --account-id")
        result = delete_account_data(settings.database_path, args.account_id)
        print(result.model_dump_json())
    else:
        if args.confirm != args.course_id:
            raise SystemExit("--confirm must exactly match --course-id")
        result = delete_course_data(
            settings.database_path,
            store,
            args.course_id,
            source_root=settings.source_root,
            region_crop_root=settings.region_crop_root,
        )
        print(result.model_dump_json())


if __name__ == "__main__":
    main()
