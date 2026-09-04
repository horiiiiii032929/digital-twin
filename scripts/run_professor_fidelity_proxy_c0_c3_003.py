#!/usr/bin/env python3
"""Run the schema-corrected synthetic C0-C3 professor-profile proxy."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

from scripts import run_professor_fidelity_proxy_c0_c3_002 as predecessor
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "professor-fidelity-proxy-c0-c3-003"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/professor_fidelity_proxy_c0_c3_003.json"
)
OUTPUT_ROOT = ROOT / "reports/generated/professor-fidelity-proxy-c0-c3-003"
LEDGER_PATH = OUTPUT_ROOT / "provider-ledger.sqlite3"
RESULT_PATH = OUTPUT_ROOT / "result.json"

_PREDECESSOR_GENERATOR_SCHEMA = predecessor._generator_schema  # noqa: SLF001
_PREDECESSOR_REVIEW_SCHEMA = predecessor._review_schema  # noqa: SLF001
_PREDECESSOR_VALIDATE_OUTPUT_LISTS = predecessor._validate_output_lists  # noqa: SLF001
_PREDECESSOR_VALIDATE_REVIEW = predecessor._validate_review  # noqa: SLF001
_PROVIDER_UNSUPPORTED_CONSTRAINTS = {
    "uniqueItems",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
}


def _openai_schema_subset(value: Any) -> Any:
    """Remove provider-unsupported assertions from the transmitted schema.

    The same contracts are enforced deterministically after parsing below.
    """

    if isinstance(value, dict):
        return {
            key: _openai_schema_subset(item)
            for key, item in value.items()
            if key not in _PROVIDER_UNSUPPORTED_CONSTRAINTS
        }
    if isinstance(value, list):
        return [_openai_schema_subset(item) for item in value]
    return deepcopy(value)


def _generator_schema(case_id: str, condition: str) -> dict[str, Any]:
    return _openai_schema_subset(_PREDECESSOR_GENERATOR_SCHEMA(case_id, condition))


def _review_schema(item_id: str) -> dict[str, Any]:
    return _openai_schema_subset(_PREDECESSOR_REVIEW_SCHEMA(item_id))


def _validate_output_lists(output: dict[str, Any]) -> None:
    _PREDECESSOR_VALIDATE_OUTPUT_LISTS(output)
    response = output["response"]
    if not isinstance(response, str) or not 1 <= len(response) <= 1400:
        raise predecessor.ProfessorProxyCheckpointError(
            "generator response length drifted"
        )
    for field in ("supported_source_facts", "citations"):
        if len(output[field]) > 3:
            raise predecessor.ProfessorProxyCheckpointError(
                f"generator list limit drifted: {field}"
            )
    if len(output["applied_profile_features"]) > len(predecessor.FIDELITY_DIMENSIONS):
        raise predecessor.ProfessorProxyCheckpointError(
            "generator profile feature limit drifted"
        )
    if any(not isinstance(value, str) or not value for value in output["supported_source_facts"]):
        raise predecessor.ProfessorProxyCheckpointError(
            "generator returned an empty supported source fact"
        )
    if any(
        not citation.get("source_id") or not citation.get("locator")
        for citation in output["citations"]
    ):
        raise predecessor.ProfessorProxyCheckpointError(
            "generator returned an empty citation field"
        )


def _validate_review(content: dict[str, Any]) -> None:
    _PREDECESSOR_VALIDATE_REVIEW(content)
    rationale = content["rationale"]
    if not isinstance(rationale, str) or not 1 <= len(rationale) <= 600:
        raise predecessor.ProfessorProxyCheckpointError("review rationale length drifted")


def configure_successor() -> None:
    """Bind the immutable predecessor engine to the successor identity."""

    predecessor.RUN_ID = RUN_ID
    predecessor.INSTRUMENT_PATH = INSTRUMENT_PATH
    predecessor.OUTPUT_ROOT = OUTPUT_ROOT
    predecessor.LEDGER_PATH = LEDGER_PATH
    predecessor.RESULT_PATH = RESULT_PATH
    predecessor._generator_schema = _generator_schema  # noqa: SLF001
    predecessor._review_schema = _review_schema  # noqa: SLF001
    predecessor._validate_output_lists = _validate_output_lists  # noqa: SLF001
    predecessor._validate_review = _validate_review  # noqa: SLF001


def main() -> int:
    configure_successor()
    if "--execute" in sys.argv or "--resume" in sys.argv:
        require_bounded_pilot_operation_allowed(RUN_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(RUN_ID, "method_evaluation_execution")
    return predecessor.main()


if __name__ == "__main__":
    raise SystemExit(main())
