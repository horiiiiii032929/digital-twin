"""Provision or rotate the first staging administrator credential."""

from __future__ import annotations

import argparse
import os

from services.api.app.config import AppSettings, RuntimeMode
from src.digital_twin.identity import IdentityService, SQLiteIdentityRepository
from src.digital_twin.student import AccountRole, SQLiteStudentRepository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--account-id", default="admin-primary")
    args = parser.parse_args()
    # Bootstrap never constructs a provider client. Validate the complete
    # runtime binding without coupling this offline administrative command to
    # inference credentials.
    settings = AppSettings.from_env(require_provider_credentials=False)
    if settings.mode != RuntimeMode.STAGING:
        raise SystemExit("APP_MODE=staging is required for administrator bootstrap")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not password:
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD is required and is never printed")

    students = SQLiteStudentRepository(settings.database_path)
    identities = SQLiteIdentityRepository(settings.database_path)
    try:
        profile = IdentityService(identities, students).provision_account(
            account_id=args.account_id,
            email=args.email,
            display_name=args.display_name,
            role=AccountRole.ADMIN,
            password=password,
        )
        print(
            f"Provisioned administrator {profile.account_id} ({profile.email}); "
            "credential value was not emitted."
        )
    finally:
        identities.close()
        students.close()


if __name__ == "__main__":
    main()
