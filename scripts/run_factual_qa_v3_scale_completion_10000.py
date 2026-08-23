#!/usr/bin/env python3
"""Validate, simulate, or execute the remaining-9,000 completion stage."""

from pathlib import Path
import sys

from scripts import run_factual_qa_v3_scale_checkpoint_1000 as stage
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]

CONFIGURATION = {
    "INSTRUMENT_PATH": (
        ROOT
        / "research/05_evaluation/instruments/"
        "factual_qa_v3_scale_completion_10000_001.json"
    ),
    "PREVIOUS_SUMMARY_PATH": (
        ROOT
        / "research/05_evaluation/judgments/"
        "factual-qa-v3-scale-checkpoint-1000-002-summary.json"
    ),
    "DEFAULT_OUTPUT": (
        ROOT
        / "reports/generated/factual-qa-v3-scale-completion-10000-001.sqlite3"
    ),
    "INSTRUMENT_ID": "factual-qa-v3-scale-completion-10000-001",
    "STAGE": "scale-10000",
    "NEW_CASE_COUNT": 9000,
    "CUMULATIVE_CASE_COUNT": 10000,
    "MUTATION_COUNT": 1800,
    "MUTATIONS_PER_TYPE": 300,
    "TASK_PREFIX": "fqa10k",
    "ENTRYPOINT_PATH": Path(__file__),
    "NEXT_STAGE_AUTHORIZATION_FIELD": "further_scale_authorized",
    "KEEP_DECISION": "keep-cumulative-10000-evidence",
    "EXPECTED_LIMITS": {
        "provider_canary_call_limit": 2,
        "author_call_limit": 9000,
        "independent_review_call_limit": 9000,
        "mutation_review_call_limit": 1800,
        "dispute_review_call_limit": 90,
        "total_provider_call_limit": 19894,
        "retry_attempts": 0,
        "credit_resume_continuation_limit": 2,
    },
}


def configure() -> None:
    """Apply the completion-stage configuration to the shared stage engine."""
    for name, value in CONFIGURATION.items():
        setattr(stage, name, value)


def main() -> int:
    configure()
    if "--execute" in sys.argv:
        require_bounded_pilot_operation_allowed(stage.INSTRUMENT_ID)
    return stage.main()


if __name__ == "__main__":
    raise SystemExit(main())
