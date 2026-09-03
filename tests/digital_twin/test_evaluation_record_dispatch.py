import json

import pytest
from pydantic import ValidationError

from src.digital_twin.evaluation import load_evaluation_record


def test_loads_non_component_research_run_record(tmp_path) -> None:
    path = tmp_path / "run.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "whole-system-run-001",
                "code_revision": "1234567",
                "status": "complete",
                "decision": "go-deeper",
                "domain_specific_metrics": {"score": 0.9},
            }
        ),
        encoding="utf-8",
    )

    record = load_evaluation_record(path)

    assert record.run_id == "whole-system-run-001"
    assert record.model_extra == {"domain_specific_metrics": {"score": 0.9}}


def test_rejects_non_component_record_with_invalid_provenance(tmp_path) -> None:
    path = tmp_path / "run.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "NOT VALID",
                "code_revision": "working-tree",
                "status": "complete",
                "decision": "go-deeper",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_evaluation_record(path)
