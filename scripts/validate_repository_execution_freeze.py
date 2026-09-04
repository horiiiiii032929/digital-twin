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
    # These two successors only derive and validate immutable in-memory
    # contracts. Provider and paid execution live in separately guarded run_*
    # entrypoints.
    "build_academic_factual_qa_grounding_selection_002.py",
    "build_governed_full_autonomy_v2_1_actual_product_evaluation_002.py",
    "build_governed_full_autonomy_v2_1_actual_product_evaluation_003.py",
    "build_governed_full_autonomy_v2_1_actual_product_evaluation_004.py",
    "build_governed_full_autonomy_v2_1_actual_product_evaluation_005.py",
    "build_governed_full_autonomy_v2_1_actual_product_evaluation_006.py",
    "build_governed_full_autonomy_v2_1_actual_product_evaluation_007.py",
    "build_governed_full_autonomy_v2_1_actual_product_evaluation_008.py",
    "build_governed_full_autonomy_v2_1_actual_product_evaluation_009.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_012.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_013.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_014.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_015.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_016.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_018.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_019.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_020.py",
    "build_governed_full_autonomy_v2_1_actual_product_confirmation_021.py",
    "build_governed_full_autonomy_v2_1_persona_confirmation_023.py",
    "build_governed_full_autonomy_v2_1_persona_confirmation_024.py",
    "build_governed_full_autonomy_v2_1_corpus_confirmation_025.py",
    "build_governed_full_autonomy_v2_1_corpus_confirmation_026.py",
    "build_governed_full_autonomy_v2_1_corpus_confirmation_027.py",
    "build_governed_full_autonomy_v2_1_corpus_confirmation_028.py",
    "build_governed_full_autonomy_v2_1_persona_wording_requirements_022.py",
    "build_governed_full_autonomy_v2_1_cross_engine_evaluation_010.py",
    "build_factual_qa_v3_source_dispositions.py",
    "build_repository_correctness_inventory.py",
    # This builder writes a deterministic synthetic public/gold package. The
    # guarded run_* successor owns every provider-backed operation.
    "build_successor_architecture_development_fold_001.py",
    "build_successor_architecture_policy_value_fold_004.py",
    "build_successor_architecture_confirmation_005.py",
    "build_successor_architecture_engine_comparison_006.py",
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
    # Fresh synthetic multi-concept confirmation. It exposes validation and a
    # deterministic product simulation only; no provider or held-out path is
    # implemented.
    "run_governed_full_autonomy_v2_1_multi_concept_confirmation_025.py",
    # This fresh mixed-initiative confirmation drives only synthetic product
    # services and SQLite state. It contains no provider, held-out, private-
    # source, or paid execution path.
    "run_stateful_clarification_confirmation.py",
    # The professor-fidelity proxy exposes only contract validation and a
    # deterministic two-reviewer simulation; it has no provider execution.
    "run_professor_fidelity_proxy_harness.py",
    # This release-local utility copies already-qualified vectors into a
    # release-bound index. It makes no provider call and opens no held-out set.
    "materialize_visual_retrieval_index.py",
    "run_ingestion_worker.py",
    # This successor-study simulation drives only synthetic hidden-state
    # learners through pure-Python estimators and timing policies. It has no
    # provider, paid, execute, held-out, or product-data mode.
    "run_successor_learner_timing_simulation_001.py",
    # The A/B/C/C+V tournament entrypoint exposes validation and network-free
    # synthetic conformance only. A separate frozen successor must own any
    # provider-backed or confirmation execution.
    "run_successor_architecture_paired_comparison_001.py",
    # This report builder only reads the committed result registry and its
    # linked records, and shells out to git for read-only revision facts. It
    # is network-free and has no provider, paid, execute, or held-out mode.
    "build_final_report_evidence_inventory.py",
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
