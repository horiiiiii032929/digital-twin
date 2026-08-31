from __future__ import annotations

from datetime import UTC, datetime
import json

import scripts.run_academic_factual_qa_source_aligned_wording as runner
from src.digital_twin.evaluation.factual_qa_reference_questions import (
    ReferenceQuestionAuthorResponseV1,
)


def test_validate_binds_one_finite_nonhuman_stage() -> None:
    result = runner.validate()

    assert result["status"] == "passed-build-only"
    assert result["case_count"] == 500
    assert result["required_reference_count"] == 450
    assert result["maximum_calls"] == 50
    assert result["maximum_cost_usd"] == 4.0
    assert result["private_data_used"] is False
    assert result["human_participants"] == 0


def test_attempt_002_uses_a_fresh_binding_and_exclusive_paths() -> None:
    try:
        runner._select_attempt("002")  # noqa: SLF001
        result = runner.validate()
        assert result["stage_id"].endswith("-002")
        assert runner.BINDING_ID.endswith("-002")
        assert runner.LEDGER_PATH.name.endswith("-002.sqlite3")
        assert runner.RESULT_PATH.name.endswith("-002.json")
    finally:
        runner._select_attempt("001")  # noqa: SLF001


def test_parser_accepts_reordered_complete_id_set() -> None:
    content = {
        "items": [
            {"case_id": "b", "question": "What does source B establish?"},
            {"case_id": "a", "question": "What does source A establish?"},
        ]
    }

    rows, error = runner._parse_by_id(  # noqa: SLF001
        content=content,
        expected_ids=["a", "b"],
        model=ReferenceQuestionAuthorResponseV1,
    )

    assert error is None
    assert [row.case_id for row in rows] == ["a", "b"]


def test_parser_quarantines_duplicate_or_unknown_ids() -> None:
    duplicate = {
        "items": [
            {"case_id": "a", "question": "What does source A establish?"},
            {"case_id": "a", "question": "What else does source A establish?"},
        ]
    }
    unknown = {
        "items": [
            {"case_id": "a", "question": "What does source A establish?"},
            {"case_id": "c", "question": "What does source C establish?"},
        ]
    }

    assert runner._parse_by_id(  # noqa: SLF001
        content=duplicate,
        expected_ids=["a", "b"],
        model=ReferenceQuestionAuthorResponseV1,
    )[1] == "semantic-duplicate-case-id"
    assert runner._parse_by_id(  # noqa: SLF001
        content=unknown,
        expected_ids=["a", "b"],
        model=ReferenceQuestionAuthorResponseV1,
    )[1] == "semantic-case-id-set-mismatch"


def test_preflight_is_ready_only_for_clean_exclusive_paths(
    monkeypatch, tmp_path
) -> None:
    load_hashed = runner._load_hashed  # noqa: SLF001

    def load_with_fresh_binding(path):
        payload = load_hashed(path)
        if path == runner.BINDING_PATH:
            payload = {**payload, "verified_at": datetime.now(UTC).isoformat()}
        return payload

    monkeypatch.setattr(runner, "_load_hashed", load_with_fresh_binding)
    monkeypatch.setattr(runner, "_repo_dirty", lambda: False)
    monkeypatch.setattr(runner, "LEDGER_PATH", tmp_path / "calls.sqlite3")
    monkeypatch.setattr(runner, "OUTPUT_CASES_PATH", tmp_path / "cases.json")
    monkeypatch.setattr(runner, "RESULT_PATH", tmp_path / "result.json")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-redacted")

    result = runner.preflight(resume=False)

    assert result["status"] == "ready"
    assert result["blockers"] == []
    assert result["credential_value_emitted"] is False


def test_reviewer_prompt_contains_no_authoritative_truth() -> None:
    _, _, _, cases, _, clusters = runner._loaded_domain()  # noqa: SLF001
    selected = cases[:2]
    selected_clusters = [
        row for row in clusters if row.cluster_id in {case.cluster_id for case in selected}
    ]
    _, prompt = runner._review_prompt(  # noqa: SLF001
        clusters=selected_clusters,
        items=[
            {
                "case_id": row.case_id,
                "cluster_id": row.cluster_id,
                "course_id": row.course_id,
                "candidate_question": row.question,
            }
            for row in selected
        ],
    )
    payload = json.loads(prompt)

    serialized = json.dumps(payload["blind_review_items"], sort_keys=True)
    assert "expected_action" not in serialized
    assert "canonical_answer" not in serialized
    assert "required_answer_spans" not in serialized
