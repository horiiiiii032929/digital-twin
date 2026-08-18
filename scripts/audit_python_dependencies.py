#!/usr/bin/env python3
"""Audit every locked Python dependency group without installing ML extras."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="digital-twin-python-audit-") as temp:
        requirements = Path(temp) / "requirements.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--locked",
                "--all-extras",
                "--all-groups",
                "--no-emit-project",
                "--no-hashes",
                "--quiet",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [
                "pip-audit",
                "--requirement",
                str(requirements),
                "--no-deps",
                "--disable-pip",
                "--progress-spinner",
                "off",
            ],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
