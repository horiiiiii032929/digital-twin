#!/usr/bin/env python3
"""Validate coverage of the repository-wide pre-evaluation execution freeze."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.repository_freeze import (  # noqa: E402
    BLOCKED_OPERATIONS,
    FROZEN_ENTRYPOINT_OPERATIONS,
    freeze_status,
)


PROTECTED_FLAGS = (
    "--allow-external-provider",
    "--confirm-heldout-once",
    'add_argument("--execute"',
)
PROTECTED_NAME_PREFIXES = (
    "apply_",
    "benchmark_",
    "build_",
    "cross_review_",
    "draft_",
    "evaluate_",
    "execute_",
    "finalize_",
    "judge_",
    "prepare_",
    "qualify_",
    "record_",
    "render_",
    "review_",
    "run_",
    "sample_",
    "seal_",
    "second_review_",
)
ALLOWED_NON_EVALUATION_ENTRYPOINTS = {
    # This builder is pure and network-free. Provider execution lives in the
    # separately guarded run_academic_* reference-validation entrypoint.
    "build_academic_factual_qa_open_reference_validation.py",
    "build_factual_qa_v3_source_dispositions.py",
    "build_repository_correctness_inventory.py",
    # This analysis-only module has no provider execution mode. Provider calls
    # live in the separately guarded execute_academic_* entrypoint.
    "run_academic_factual_qa_panel_review_v2.py",
    # This prospective contract currently exposes validation/simulation and a
    # blocked preflight only. The paid executor is added after model selection.
    "run_autonomous_tutoring_r1_confirmation.py",
    # This development qualification is deterministic and network-free. It
    # cannot call a provider or open the sealed Program 011 final package.
    "run_governed_full_autonomy_product_freeze.py",
    # This build-only harness expands public/gold contracts in memory and runs
    # a deterministic reference driver. It has no provider or held-out mode.
    "run_governed_full_autonomy_v2_1_evaluation_harness.py",
    # This integration smoke drives only deterministic local services over
    # synthetic data. It has no provider, paid, execute, or held-out mode.
    "run_governed_full_autonomy_v2_1_actual_product_smoke.py",
    "run_ingestion_worker.py",
}
EXEMPT_SCRIPTS = {
    "validate_professor_fidelity_post_audit.py",
    "validate_repository_execution_freeze.py",
}
GUARD_NAMES = {
    "require_pre_evaluation_operation_allowed",
    "require_bounded_pilot_operation_allowed",
}


def has_main_guard(path: Path) -> bool:
    tree = ast.parse(path.read_text(), filename=str(path))
    main = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "main"
        ),
        None,
    )
    if main is None:
        return False

    def is_guard_statement(node: ast.stmt) -> bool:
        return (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in GUARD_NAMES
        )

    for statement in main.body:
        if is_guard_statement(statement):
            return True
        if isinstance(statement, ast.If) and not (
            isinstance(statement.test, ast.Constant) and statement.test.value is False
        ):
            if any(is_guard_statement(child) for child in statement.body):
                return True
        if isinstance(statement, (ast.Return, ast.Raise)):
            return False
    return False


def protected_scripts(root: Path = ROOT) -> list[Path]:
    discovered = {
        path
        for path in (root / "scripts").glob("*.py")
        if path.name not in EXEMPT_SCRIPTS
        and path.name not in ALLOWED_NON_EVALUATION_ENTRYPOINTS
        and (
            any(flag in path.read_text() for flag in PROTECTED_FLAGS)
            or path.name.startswith(PROTECTED_NAME_PREFIXES)
            or "heldout" in path.name
        )
    }
    if root.resolve() == ROOT.resolve():
        registered = {root / path for path in FROZEN_ENTRYPOINT_OPERATIONS}
        missing_paths = sorted(path for path in registered if not path.is_file())
        if missing_paths:
            raise ValueError(
                "registered frozen entrypoint missing: "
                + ", ".join(path.relative_to(root).as_posix() for path in missing_paths)
            )
        discovered.update(registered)
    return sorted(discovered)


def validate_freeze_coverage(root: Path = ROOT) -> dict[str, object]:
    if root.resolve() == ROOT.resolve():
        unknown_operations = sorted(
            {
                operation
                for operations in FROZEN_ENTRYPOINT_OPERATIONS.values()
                for operation in operations
                if operation not in BLOCKED_OPERATIONS
            }
        )
        if unknown_operations:
            raise ValueError(
                "frozen entrypoint registry has unknown operations: "
                + ", ".join(unknown_operations)
            )
    scripts = protected_scripts(root)
    missing = [
        path.relative_to(root).as_posix()
        for path in scripts
        if not has_main_guard(path)
    ]
    if missing:
        raise ValueError(
            "pre-evaluation freeze guard missing from: " + ", ".join(missing)
        )
    status = freeze_status()
    if not status.active:
        raise ValueError("repository correctness pre-evaluation freeze is not active")
    return {
        "freeze_id": status.freeze_id,
        "freeze_active": status.active,
        "registered_entrypoint_count": (
            len(FROZEN_ENTRYPOINT_OPERATIONS) if root.resolve() == ROOT.resolve() else 0
        ),
        "protected_script_count": len(scripts),
        "missing_guard_count": 0,
        "status": "passed",
        "model_or_provider_called": False,
        "heldout_data_read": False,
    }


def main() -> int:
    print(json.dumps(validate_freeze_coverage(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
