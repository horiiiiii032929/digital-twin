import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_staging_entrypoint_does_not_initialize_demo_store(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime" / "digital-twin.sqlite3"
    data_root = tmp_path / "runtime"
    env = os.environ.copy()
    env.update(
        {
            "APP_MODE": "staging",
            "APP_DATABASE_PATH": str(database_path),
            "APP_DATA_ROOT": str(data_root),
            "APP_ALLOWED_ORIGINS": "https://twin.example.edu",
            "APP_SECURE_COOKIES": "true",
        }
    )
    code = """
import json
import sys
from services.api.app.main import app

print(json.dumps({
    "database_path": str(app.state.student_repository.path),
    "demo_store_imported": "services.api.app.store" in sys.modules,
}))
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result == {
        "database_path": str(database_path),
        "demo_store_imported": False,
    }
