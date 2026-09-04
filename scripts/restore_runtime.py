from __future__ import annotations

import argparse
from pathlib import Path

from services.api.app.config import AppSettings, RuntimeMode
from services.operations import restore_runtime_backup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    # Restore verifies local archive and runtime bindings only; it does not
    # construct or call a provider client.
    settings = AppSettings.from_env(require_provider_credentials=False)
    if settings.mode != RuntimeMode.STAGING:
        raise SystemExit("APP_MODE=staging is required for runtime restore")
    manifest = restore_runtime_backup(
        args.archive,
        settings.database_path,
        settings.data_root,
    )
    print(
        f"Restored schema v{manifest.schema_version} and "
        f"{len(manifest.data_files)} verified data files."
    )


if __name__ == "__main__":
    main()
