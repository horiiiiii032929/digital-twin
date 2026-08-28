from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.digital_twin.repository_freeze import FREEZE_ID


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("module", "arguments"),
    [
        ("scripts.analyze_it5002_rapid_result", []),
        ("scripts.build_course_tutor_splits", []),
        ("scripts.build_academic_factual_qa_open_mixed_wording_005", ["--write"]),
        ("scripts.build_generator_qualification_dataset", []),
        ("scripts.build_it5002_rapid_dataset", []),
        ("scripts.finalize_factual_qa_v3_conversion", []),
        ("scripts.seal_course_tutor_anchor", []),
        ("scripts.evaluate_retrieval", []),
        ("scripts.benchmark_retrieval", []),
        ("scripts.build_multimodal_development_artifacts", []),
        ("scripts.draft_cross_course_benchmark_v2", []),
        ("scripts.run_cross_course_retrieval_pilot", []),
        ("scripts.run_it5002_retrieval_rapid", ["--phase", "development"]),
        ("scripts.run_multimodal_retrieval_development", []),
        (
            "scripts.run_factual_qa_quality_pilot",
            ["--execute", "--allow-external-provider"],
        ),
        ("scripts.run_local_reviewer_sensitivity", ["--execute"]),
        (
            "scripts.run_cross_course_retrieval_heldout",
            ["--confirm-heldout-once"],
        ),
    ],
)
def test_high_risk_entrypoints_fail_before_execution(
    module: str, arguments: list[str]
) -> None:
    result = subprocess.run(
        [sys.executable, "-m", module, *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert FREEZE_ID in result.stdout + result.stderr
