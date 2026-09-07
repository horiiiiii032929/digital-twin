from dataclasses import replace

import pytest

from services.api.app.config import AppSettings, AutonomyPlannerMode, EvidenceGateMode, StudentTutoringMode
from services.api.app import experimental
from services.llm import OpenAiResponsesClient
from scripts.verify_deployable_foundation import _settings


def configured_settings(path):
    return replace(_settings(path), student_tutoring_mode=StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
        autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE,
        evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3)


def test_experimental_factory_requires_explicit_version_and_real_authentication(monkeypatch):
    monkeypatch.delenv("APP_EXPERIMENTAL_TUTORING_CANDIDATE", raising=False)
    monkeypatch.setattr(experimental, "load_dotenv", lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="explicit experimental version"):
        experimental.create_experimental_app()
    with pytest.raises(ValueError, match="unknown experimental"):
        experimental.build_experimental_app(AppSettings(), "latest")
    with pytest.raises(ValueError, match="credential-authenticated"):
        experimental.build_experimental_app(AppSettings(), "v9")


def test_real_transport_cap_mismatch_fails_before_application_creation(tmp_path):
    settings = configured_settings(tmp_path)
    with pytest.raises(ValueError, match="model or output cap"):
        experimental.build_experimental_app(settings, "v9", transport=OpenAiResponsesClient("gpt-5.6-luna", max_output_tokens=500))


def test_experimental_factory_keeps_existing_qualification_requirement(tmp_path):
    from tests.test_paired_pedagogy_development import InstructionalContractClient
    settings = replace(configured_settings(tmp_path), t1_qualification_result_path=None)
    with pytest.raises(ValueError, match="APP_T1_QUALIFICATION_RESULT_PATH"):
        experimental.build_experimental_app(settings, "v9", transport=InstructionalContractClient("v9"))


def test_local_application_serves_built_ui_without_bypassing_api_auth(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from scripts.verify_deployable_foundation import _close_app
    from tests.test_paired_pedagogy_development import InstructionalContractClient
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<html>Existing application login UI</html>")
    (web / "build-configuration.json").write_text('{"schema_version":1,"auth_mode":"session"}')
    (web / "app.js").write_text("window.syntheticAsset = true;")
    (web / "api").mkdir()
    (web / "api/nonexistent-route").write_text("MUST_NOT_SHADOW_API")
    (tmp_path / "private.txt").write_text("PRIVATE_PARENT_FILE")
    monkeypatch.setattr(experimental, "WEB_DIST", web)
    root = experimental.WEB_DIST.parents[0]
    settings = replace(configured_settings(root / "runtime"), learning_gap_hmac_secret=b"synthetic-local-application-test-secret-32",
        student_profile_path=experimental.Path(__file__).resolve().parents[2] / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json",
        t1_qualification_result_path=experimental.Path(__file__).resolve().parents[2] / "research/05_evaluation/records/governed-full-autonomy-v2-1-final-release-binding-001.json")
    app = experimental.build_experimental_app(settings, "v9", transport=InstructionalContractClient("v9"), serve_web=True)
    try:
        with TestClient(app, base_url="https://testserver") as client:
            assert "Existing application login UI" in client.get("/").text
            assert "syntheticAsset" in client.get("/app.js").text
            for route in ("/student", "/professor", "/professor/setup", "/professor/delivery"):
                assert "Existing application login UI" in client.get(route).text
            assert client.get("/unknown-page").status_code == 404
            missing = client.get("/api/nonexistent-route")
            assert missing.status_code == 404 and "application/json" in missing.headers["content-type"]
            traversal = client.get("/%2e%2e/private.txt")
            assert traversal.status_code == 404 and "PRIVATE_PARENT_FILE" not in traversal.text
            assert client.get("/api/student/courses", headers={"X-Account-ID": "pretend-student"}).status_code == 401
            assert app.state.experimental_tutoring_configuration["observed_implementation_id"] == "question-specific-profile-grounded-v9"
    finally:
        _close_app(app)


def test_wrapped_provider_cap_and_independent_generator_are_rejected(tmp_path):
    from types import SimpleNamespace
    from services.api.app.config import GeneratorMode
    settings = configured_settings(tmp_path)
    wrapper = SimpleNamespace(serializer=OpenAiResponsesClient("gpt-5.6-luna", max_output_tokens=3000),
        client=SimpleNamespace(transport=OpenAiResponsesClient("gpt-5.6-luna", max_output_tokens=500)))
    with pytest.raises(ValueError, match="model or output cap"):
        experimental.build_experimental_app(settings, "v9", transport=wrapper)
    with pytest.raises(ValueError, match="independently configured external"):
        experimental.build_experimental_app(replace(settings, generator_mode=GeneratorMode.OPENAI_PROFILE_SELECTED), "v9")


def test_mismatched_modes_and_unknown_transport_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="matching governed tutoring"):
        experimental.build_experimental_app(_settings(tmp_path), "v9", transport=object())
    with pytest.raises(ValueError, match="unknown transport capability"):
        experimental.build_experimental_app(configured_settings(tmp_path), "v9", transport=object())


def test_session_build_marker_is_required_before_serving_ui(tmp_path, monkeypatch):
    monkeypatch.setattr(experimental, "WEB_DIST", tmp_path)
    with pytest.raises(ValueError, match="VITE_AUTH_MODE=session"):
        experimental.validate_web_build()
    (tmp_path / "index.html").write_text("demo")
    (tmp_path / "build-configuration.json").write_text('{"schema_version":1,"auth_mode":"demo"}')
    with pytest.raises(ValueError, match="session-auth build"):
        experimental.validate_web_build()
