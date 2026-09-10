"""Optionally provision the initial admin without exposing credentials in arguments."""
import json
import os
from pathlib import Path
import subprocess


def main() -> None:
    secret = json.loads(Path(os.environ["SECRET_FILE"]).read_text())
    password = secret.get("BOOTSTRAP_ADMIN_PASSWORD")
    email = secret.get("ADMIN_EMAIL")
    if not password or not email:
        print("Administrator bootstrap not configured; provision through Session Manager.")
        return
    probe = subprocess.run([
        "docker", "exec", "digital-twin-api", "python", "-c",
        "from services.api.app.config import AppSettings; "
        "from src.digital_twin.identity import SQLiteIdentityRepository; "
        "repo = SQLiteIdentityRepository(AppSettings.from_env(require_provider_credentials=False).database_path); "
        "exists = repo.get_credential('admin-primary') is not None; "
        "repo.close(); raise SystemExit(0 if exists else 42)",
    ], check=False)
    if probe.returncode == 0:
        print("Existing administrator preserved; no password reset performed.")
        return
    if probe.returncode != 42:
        raise SystemExit("Administrator existence check failed; refusing to provision.")
    subprocess.run([
        "docker", "exec", "-e", "BOOTSTRAP_ADMIN_PASSWORD", "digital-twin-api",
        "python", "-m", "scripts.bootstrap_admin", "--email", email,
        "--display-name", "Administrator",
    ], env={**os.environ, "BOOTSTRAP_ADMIN_PASSWORD": password}, check=True)


if __name__ == "__main__":
    main()
