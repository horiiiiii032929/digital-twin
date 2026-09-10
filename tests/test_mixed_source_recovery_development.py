import json

import pytest

from scripts import run_mixed_source_recovery_development as runner


def test_same_candidate_cross_boundary_contract_uses_credentials_and_clean_restore(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = runner.run(tmp_path / "fresh")
    assert not result["failures"], result["failures"]
    assert result["source_unchanged"]
    assert result["decision"] == "keep-integration-contract-only"
    assert result["external_calls"] == 0 and result["injected_provider_calls"] >= 7
    assert result["quality_pass"] is None and result["deployment_qualified"] is False
    assert result["cohort"] == {"active": 6, "gap_learners": 5, "review_restored": True}
    checks = {row["name"]: row["passed"] for row in result["checks"]}
    for gate in ["cross-origin-rejected-without-course", "cross-course-job-cannot-create-release",
                 "restored-active-course-uses-own-source", "restored-withdrawal-prevents-provider",
                 "restored-cohort-and-review", "unreviewed-input-writes-no-object"]:
        assert checks[gate]
    assert not (tmp_path / "fresh/runtime").exists()
    assert (tmp_path / "fresh/restored-runtime/digital-twin.sqlite3").is_file()
    assert set(result["source_formats"]) == {"application/pdf", "text/plain", "text/markdown"}
    assert json.loads((tmp_path / "fresh/summary.json").read_text())["source_unchanged"]
    with pytest.raises(FileExistsError):
        runner.run(tmp_path / "fresh")
    # Separate endpoint regression: restored PDF crops must be readable from the
    # new root only, with the same candidate composition and real session checks.
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from services.api.app.factory import create_app
    from services.api.app.config import AutonomyPlannerMode, EvidenceGateMode, StudentTutoringMode
    from scripts.verify_deployable_foundation import _settings, _login, _close_app, ORIGIN, STUDENT_PASSWORD
    settings = replace(_settings(tmp_path / "fresh/restored-runtime"),
        student_profile_path=runner.ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json",
        t1_qualification_result_path=runner.ROOT / "research/05_evaluation/records/governed-full-autonomy-v2-1-final-release-binding-001.json",
        autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE,
        evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3,
        student_tutoring_mode=StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
        learning_gap_hmac_secret=b"synthetic-mixed-source-contract-only-key-32")
    provider = runner.SourceBoundContractClient(tmp_path / "crop-provider.jsonl")
    app = create_app(settings=settings, autonomy_planner_client=provider,
        teaching_profile_context_enabled=True, question_specific_generation_enabled=True)
    citation = next(row for row in result["checks"] if row["name"] == "restored-active-course-uses-own-source")["detail"]["citations"][0]
    url = f"/api/student/messages/{citation['message_id']}/citations/{citation['id']}/crop"
    try:
        with TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN}) as client:
            assert _login(client, "mixed-6@example.test", STUDENT_PASSWORD).status_code == 200
            response = client.get(url)
            assert response.status_code == 200
            assert response.content.startswith(b"\x89PNG")
            assert response.headers["cache-control"] == "private, no-store"
            assert _login(client, "student@foundation.example", STUDENT_PASSWORD).status_code == 200
            assert client.get(url).status_code == 403
            assert provider.calls == 0
    finally:
        _close_app(app)


def test_authorization_precedes_output_creation(tmp_path, monkeypatch):
    def deny(instrument, operation):
        assert instrument == runner.INSTRUMENT_ID
        assert operation == "method_evaluation_execution"
        raise PermissionError("not authorized")
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", deny)
    with pytest.raises(PermissionError):
        runner.run(tmp_path / "denied")
    assert not (tmp_path / "denied").exists()


def test_post_report_composition_is_preserved_through_review_withdrawal_and_restore(tmp_path):
    result=runner.run(tmp_path/'post-report',post_report=True)
    assert not result['failures'],result['failures']
    assert result['source_unchanged'] and result['external_calls']==0
    assert result['quality_pass'] is None
    flags=result['manifest']['runtime_flags']
    assert flags['post_report_model_assessment_version']=='v2'
    assert flags['post_report_learning_mode']=='assessed-count'
    assert result['manifest']['candidate_id']=='question-specific-profile-grounded-v19'
    gates={r['name']:r['passed'] for r in result['checks']}
    assert gates['actual-audit-dispatched']
    assert gates['restored-withdrawal-prevents-provider']
    assert gates['restored-cohort-and-review']
    assert (tmp_path/'post-report/source-snapshot.zip').is_file()


def test_explicit_cheap_candidate_survives_full_restore(tmp_path):
    result=runner.run(tmp_path/'cheap',post_report=True,candidate='v19-luna-luna-medium')
    assert not result['failures']
    assert result['source_unchanged']
    assert result['manifest']['candidate_variant']=='v19-luna-luna-medium'
    assert any(c['name']=='actual-audit-dispatched' and c['passed'] for c in result['checks'])
