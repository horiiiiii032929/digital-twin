from __future__ import annotations

import argparse
from pathlib import Path

from services.api.app.config import AppSettings, RuntimeMode
from services.operations import create_runtime_backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = AppSettings.from_env()
    if settings.mode != RuntimeMode.STAGING:
        raise SystemExit("APP_MODE=staging is required for runtime backup")
    manifest = create_runtime_backup(
        settings.database_path,
        settings.data_root,
        args.output,
    )
    print(
        f"Created verified backup with schema v{manifest.schema_version}, "
        f"{len(manifest.data_files)} data files; no file content was emitted."
    )


if __name__ == "__main__":
    main()
