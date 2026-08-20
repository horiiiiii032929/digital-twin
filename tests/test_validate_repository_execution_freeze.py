from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_repository_execution_freeze import validate_freeze_coverage
from src.digital_twin.repository_freeze import FROZEN_ENTRYPOINT_OPERATIONS


def test_validator_rejects_unprotected_execution_script(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_eval.py").write_text(
        'parser.add_argument("--execute", action="store_true")\n'
    )

    with pytest.raises(ValueError, match="freeze guard missing"):
        validate_freeze_coverage(tmp_path)


def test_validator_rejects_unprotected_no_flag_dataset_builder(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "build_eval_dataset.py").write_text("def main():\n    pass\n")

    with pytest.raises(ValueError, match="freeze guard missing"):
        validate_freeze_coverage(tmp_path)


def test_validator_accepts_guarded_execution_script(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_eval.py").write_text(
        'parser.add_argument("--execute", action="store_true")\n'
        "def main():\n"
        "    require_pre_evaluation_operation_allowed("
        "'method_evaluation_execution')\n"
    )

    result = validate_freeze_coverage(tmp_path)

    assert result["protected_script_count"] == 1
    assert result["missing_guard_count"] == 0


def test_validator_rejects_guard_token_outside_main(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_eval.py").write_text(
        "require_pre_evaluation_operation_allowed = lambda operation: None\n"
        "def main():\n"
        "    pass\n"
    )

    with pytest.raises(ValueError, match="freeze guard missing"):
        validate_freeze_coverage(tmp_path)


def test_validator_rejects_nested_or_unreachable_guard(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_eval.py").write_text(
        "def main():\n"
        "    def never_called():\n"
        "        require_pre_evaluation_operation_allowed('method_evaluation_execution')\n"
        "    return 0\n"
    )

    with pytest.raises(ValueError, match="freeze guard missing"):
        validate_freeze_coverage(tmp_path)


def test_repository_registry_is_the_authoritative_coverage_set() -> None:
    result = validate_freeze_coverage()

    assert result["registered_entrypoint_count"] == len(
        FROZEN_ENTRYPOINT_OPERATIONS
    )
    assert result["protected_script_count"] == len(FROZEN_ENTRYPOINT_OPERATIONS)


def test_validator_supports_direct_script_execution() -> None:
    root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "scripts/validate_repository_execution_freeze.py"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout)["status"] == "passed"
