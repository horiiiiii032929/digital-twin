import json
import sqlite3
from dataclasses import replace

import pytest

from services.api.app.config import (
    AppSettings,
    AutonomyPlannerMode,
    EvidenceGateMode,
    StudentTutoringMode,
)
from services.api.app.factory import create_app
from src.digital_twin.evaluation.experimental_tutoring_candidate import (
    experimental_tutoring_configuration,
)
from src.digital_twin.generation.typed_instruction import TASK
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse
from src.digital_twin.student import (
    SQLiteStudentRepository,
    seed_synthetic_student_workflow,
)
from src.digital_twin.student.generated_preview import (
    GeneratedProfilePreviewService,
    GeneratedPreviewRequest,
    GeneratedPreviewApproval,
    canonical_sha,
)
from src.digital_twin.student.models import StudentReleaseStatus
from src.digital_twin.student.teaching_profile import (
    TeachingProfileService,
    TeachingProfileError,
)
from src.digital_twin.student.teaching_profile_context import (
    approved_teaching_profile_context,
)
from tests.api.test_publication_api import _teaching_profile_payload


class Client:
    def __init__(self):
        self.calls = []

    async def chat(self, messages, task):
        payload = json.loads(messages[-1].content)
        self.calls.append((task, payload))
        if task == "question_specific_conditional_revision":
            from tests.test_conditional_revision_generation import decision

            return LlmResponse(
                content=json.dumps(decision()),
                provider_model="gpt-5.6-sol",
                usage=GenerationUsage(
                    input_tokens=10,
                    output_tokens=10,
                    total_tokens=20,
                    approximate_cost_usd=0.001,
                ),
            )
        if task != TASK:
            raise LlmMalformedResponseError(
                usage=GenerationUsage(approximate_cost_usd=0)
            )
        return LlmResponse(
            provider_model="gpt-5.6-luna",
            usage=GenerationUsage(
                input_tokens=10,
                output_tokens=10,
                total_tokens=20,
                approximate_cost_usd=0.001,
            ),
            content=json.dumps(
                {
                    "action": "instruction",
                    "units": [
                        {
                            "kind": "explanation",
                            "text": payload["evidence"][0]["text"],
                            "source_ids": [payload["evidence"][0]["citation_id"]],
                        }
                    ],
                    "missing_details": [],
                }
            ),
        )


@pytest.fixture(params=["v10-luna-low", "v14-luna-sol", "v14-luna-sol-medium"])
def environment(tmp_path, request):
    repo = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(repo)
    profiles = TeachingProfileService(repo)
    first = profiles.create_draft(
        fixture.professor_id, fixture.course_a_id, _teaching_profile_payload()
    )
    first = profiles.approve(
        fixture.professor_id,
        fixture.course_a_id,
        first.profile_id,
        preview_sha256=profiles.preview(
            fixture.professor_id, fixture.course_a_id, first.profile_id
        ).preview_sha256,
    )
    release = repo.get_release(fixture.release_a_id)
    # Save a separate current release already bound to the first real approval.
    release = release.model_copy(
        update={
            "id": "profile-bound-current",
            "status": StudentReleaseStatus.DRAFT,
            "teaching_profile_id": first.profile_id,
            "teaching_profile_sha256": first.content_sha256,
        }
    )
    repo.save_release(release)
    repo.publish_release(release.id)
    release = repo.get_release(release.id)
    client = Client()
    settings = replace(
        AppSettings(),
        data_root=tmp_path,
        database_path=tmp_path / "api.sqlite3",
        student_tutoring_mode=StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
        evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3,
        autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE,
        learning_gap_hmac_secret=b"synthetic-preview-secret-at-least-32-characters",
    )
    selection = experimental_tutoring_configuration(request.param)
    app = create_app(
        student_repository=repo,
        settings=settings,
        autonomy_planner_client=client,
        **selection["runtime_flags"],
    )
    app.state.experimental_tutoring_configuration = selection
    yield app, repo, fixture, profiles, first, release, client
    for name in (
        "student_repository",
        "identity_repository",
        "ingestion_job_repository",
    ):
        getattr(app.state, name).close()


def new_profile(env):
    _, _, f, p, *_ = env
    return p.create_draft(f.professor_id, f.course_a_id, _teaching_profile_payload())


def request():
    return GeneratedPreviewRequest(
        session_id="owned-session",
        ingestion_job_ids=["owned-job"],
        concept_label="cache",
        concept_description="Cache behavior in the selected approved material.",
        objective="Explain the cache.",
        cases=[
            {"case_id": "case1", "student_messages": ["Explain cache invalidation."]}
        ],
    )


def snapshot(env):
    release = env[5]
    return {
        "policy": release.policy.model_dump(mode="json"),
        "policy_version": release.policy_version,
        "chunks": [c.model_dump(mode="json") for c in release.chunks],
    }


def test_new_approval_preserves_current_published_authority_and_retry(environment):
    _, repo, f, p, old, release, _ = environment
    new = new_profile(environment)
    digest = p.preview(f.professor_id, f.course_a_id, new.profile_id).preview_sha256
    p.approve(f.professor_id, f.course_a_id, new.profile_id, preview_sha256=digest)
    assert repo.get_teaching_profile(old.profile_id).status == "superseded"
    assert (
        approved_teaching_profile_context(repo, release)["content_sha256"]
        == old.content_sha256
    )
    assert (
        p.approve(
            f.professor_id, f.course_a_id, new.profile_id, preview_sha256=digest
        ).profile_id
        == new.profile_id
    )
    with pytest.raises(TeachingProfileError):
        p.require_approved(f.professor_id, f.course_a_id, old.profile_id)
    p.withdraw(f.professor_id, f.course_a_id, old.profile_id)
    with pytest.raises(ValueError):
        approved_teaching_profile_context(repo, release)


def test_approval_rolls_back_predecessor_on_successor_write_failure(environment):
    _, repo, f, p, old, _, _ = environment
    new = new_profile(environment)
    repo._connection.execute(
        f"CREATE TRIGGER fail_profile BEFORE UPDATE ON teaching_profiles WHEN NEW.profile_id='{new.profile_id}' BEGIN SELECT RAISE(ABORT,'injected-failure'); END"
    )
    with pytest.raises(sqlite3.IntegrityError):
        p.approve(
            f.professor_id,
            f.course_a_id,
            new.profile_id,
            preview_sha256=p.preview(
                f.professor_id, f.course_a_id, new.profile_id
            ).preview_sha256,
        )
    assert repo.get_teaching_profile(old.profile_id).status == "approved"
    assert repo.get_teaching_profile(new.profile_id).status == "draft"


def test_profile_approval_serializes_concurrent_withdrawal_before_status_read(
    environment, tmp_path, monkeypatch
):
    _, repo, f, profiles, *_ = environment
    draft = new_profile(environment)
    digest = profiles.preview(
        f.professor_id, f.course_a_id, draft.profile_id
    ).preview_sha256
    other = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    other._connection.execute("PRAGMA busy_timeout=0")
    get_profile = repo.get_teaching_profile
    checked = []

    def competing_withdrawal(profile_id):
        if not checked:
            checked.append(True)
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                TeachingProfileService(other).withdraw(
                    f.professor_id, f.course_a_id, draft.profile_id
                )
        return get_profile(profile_id)

    monkeypatch.setattr(repo, "get_teaching_profile", competing_withdrawal)
    try:
        repo.approve_teaching_profile_atomic(
            draft.profile_id, preview_sha256=digest, changed_at="2026-09-06T09:00:00Z"
        )
        assert checked
        TeachingProfileService(other).withdraw(
            f.professor_id, f.course_a_id, draft.profile_id
        )
        assert get_profile(draft.profile_id).status == "withdrawn"
        with pytest.raises(ValueError, match="draft"):
            repo.approve_teaching_profile_atomic(
                draft.profile_id,
                preview_sha256=digest,
                changed_at="2026-09-06T09:01:00Z",
            )
        assert get_profile(draft.profile_id).status == "withdrawn"
    finally:
        other.close()


@pytest.mark.asyncio
async def test_actual_isolated_generation_saved_approval_no_get_calls(environment):
    app, repo, f, p, old, release, client = environment
    draft = new_profile(environment)
    service = app.state.generated_preview_service
    before = repo._connection.execute("SELECT count(*) FROM messages").fetchone()[0]
    artifact = await service.create(
        f.professor_id,
        f.course_a_id,
        draft.profile_id,
        request(),
        resolve_snapshot=lambda _: snapshot(environment),
    )
    assert artifact["status"] == "complete", artifact
    assert artifact["cases"][0]["turns"][0]["tutor"]
    assert client.calls
    calls = len(client.calls)
    assert (
        service.get(
            f.professor_id, f.course_a_id, draft.profile_id, artifact["artifact_id"]
        )
        == artifact
    )
    assert len(service.list(f.professor_id, f.course_a_id, draft.profile_id)) == 1
    approval = GeneratedPreviewApproval(
        artifact_sha256=artifact["artifact_sha256"],
        decisions=[{"case_id": "case1", "decision": "accept"}],
    )
    accepted = service.approve(
        f.professor_id,
        f.course_a_id,
        draft.profile_id,
        artifact["artifact_id"],
        approval,
        resolve_snapshot=lambda _: snapshot(environment),
    )
    assert accepted["review_status"] == "accepted"
    assert (
        service.approve(
            f.professor_id,
            f.course_a_id,
            draft.profile_id,
            artifact["artifact_id"],
            approval,
            resolve_snapshot=lambda _: snapshot(environment),
        )
        == accepted
    )
    assert len(client.calls) == calls
    assert (
        repo._connection.execute("SELECT count(*) FROM messages").fetchone()[0]
        == before
    )
    assert (
        approved_teaching_profile_context(repo, release)["content_sha256"]
        == old.content_sha256
    )
    assert (
        repo.get_teaching_profile(draft.profile_id).preview_sha256
        == artifact["artifact_sha256"]
    )
    with pytest.raises(TeachingProfileError):
        service.get(
            f.student_a_id, f.course_a_id, draft.profile_id, artifact["artifact_id"]
        )


@pytest.mark.asyncio
async def test_changed_sources_tampered_bytes_and_failed_artifacts_reject(environment):
    app, repo, f, _, _, _, _ = environment
    draft = new_profile(environment)
    service = app.state.generated_preview_service
    artifact = await service.create(
        f.professor_id,
        f.course_a_id,
        draft.profile_id,
        request(),
        resolve_snapshot=lambda _: snapshot(environment),
    )
    approve = GeneratedPreviewApproval(
        artifact_sha256=artifact["artifact_sha256"],
        decisions=[{"case_id": "case1", "decision": "accept"}],
    )
    with pytest.raises(TeachingProfileError, match="changed"):
        service.approve(
            f.professor_id,
            f.course_a_id,
            draft.profile_id,
            artifact["artifact_id"],
            approve,
            resolve_snapshot=lambda _: {**snapshot(environment), "changed": True},
        )
    changed = {**artifact, "error_code": "tampered"}
    repo._connection.execute(
        "UPDATE generated_profile_previews SET artifact_json=? WHERE artifact_id=?",
        (json.dumps(changed), artifact["artifact_id"]),
    )
    repo._connection.commit()
    with pytest.raises(TeachingProfileError, match="hash"):
        service.get(
            f.professor_id, f.course_a_id, draft.profile_id, artifact["artifact_id"]
        )
    assert canonical_sha({"a": 1}) == canonical_sha({"a": 1})


def test_preview_snapshot_rejects_another_owners_session_before_sources():
    from types import SimpleNamespace
    from services.api.app.routers.publication import _generated_snapshot

    sessions = SimpleNamespace(
        get=lambda _: SimpleNamespace(
            owner_account_id="someone-else", course_id="course", policy=object()
        )
    )
    with pytest.raises(TeachingProfileError, match="owned"):
        _generated_snapshot("owner", "course", request(), sessions, None)


@pytest.mark.asyncio
async def test_review_is_immutable_and_withdrawal_cannot_be_reapproved(environment):
    app, _, f, profiles, *_ = environment
    draft = new_profile(environment)
    service = app.state.generated_preview_service
    artifact = await service.create(
        f.professor_id,
        f.course_a_id,
        draft.profile_id,
        request(),
        resolve_snapshot=lambda _: snapshot(environment),
    )

    def review(choice):
        return GeneratedPreviewApproval(
            artifact_sha256=artifact["artifact_sha256"],
            decisions=[{"case_id": "case1", "decision": choice}],
        )

    service.approve(
        f.professor_id,
        f.course_a_id,
        draft.profile_id,
        artifact["artifact_id"],
        review("accept"),
        resolve_snapshot=lambda _: snapshot(environment),
    )
    with pytest.raises(ValueError, match="immutable"):
        service.approve(
            f.professor_id,
            f.course_a_id,
            draft.profile_id,
            artifact["artifact_id"],
            review("revise"),
            resolve_snapshot=lambda _: snapshot(environment),
        )
    profiles.withdraw(f.professor_id, f.course_a_id, draft.profile_id)
    with pytest.raises(TeachingProfileError, match="Withdrawn"):
        service.approve(
            f.professor_id,
            f.course_a_id,
            draft.profile_id,
            artifact["artifact_id"],
            review("accept"),
            resolve_snapshot=lambda _: snapshot(environment),
        )


@pytest.mark.asyncio
async def test_failed_provider_preview_is_saved_but_not_approvable(environment):
    from src.digital_twin.llm import LlmUnavailableError

    app, _, f, *_ = environment

    async def failed(**kwargs):
        raise LlmUnavailableError()

    service = app.state.generated_preview_service
    service.runner = failed
    draft = new_profile(environment)
    artifact = await service.create(
        f.professor_id,
        f.course_a_id,
        draft.profile_id,
        request(),
        resolve_snapshot=lambda _: snapshot(environment),
    )
    assert artifact["status"] == "failed"
    assert (
        service.get(
            f.professor_id, f.course_a_id, draft.profile_id, artifact["artifact_id"]
        )
        == artifact
    )
    approval = GeneratedPreviewApproval(
        artifact_sha256=artifact["artifact_sha256"],
        decisions=[{"case_id": "case1", "decision": "accept"}],
    )
    with pytest.raises(TeachingProfileError):
        service.approve(
            f.professor_id,
            f.course_a_id,
            draft.profile_id,
            artifact["artifact_id"],
            approval,
            resolve_snapshot=lambda _: snapshot(environment),
        )


@pytest.mark.asyncio
async def test_saved_preview_and_review_survive_repository_restart(
    environment, tmp_path
):
    app, _, f, *_ = environment
    service = app.state.generated_preview_service
    draft = new_profile(environment)
    artifact = await service.create(
        f.professor_id,
        f.course_a_id,
        draft.profile_id,
        request(),
        resolve_snapshot=lambda _: snapshot(environment),
    )
    configuration = service.configuration()

    async def must_not_generate(**kwargs):
        pytest.fail("Reading or reviewing saved evidence must not call a provider")

    reopened = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    try:
        restored = GeneratedProfilePreviewService(
            TeachingProfileService(reopened),
            runner=must_not_generate,
            configuration=lambda: configuration,
        )
        assert (
            restored.get(
                f.professor_id, f.course_a_id, draft.profile_id, artifact["artifact_id"]
            )
            == artifact
        )
        reviewed = restored.approve(
            f.professor_id,
            f.course_a_id,
            draft.profile_id,
            artifact["artifact_id"],
            GeneratedPreviewApproval(
                artifact_sha256=artifact["artifact_sha256"],
                decisions=[{"case_id": "case1", "decision": "accept"}],
            ),
            resolve_snapshot=lambda _: snapshot(environment),
        )
        assert reviewed["review_status"] == "accepted"
    finally:
        reopened.close()
    reopened = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    try:
        restored = GeneratedProfilePreviewService(
            TeachingProfileService(reopened),
            runner=must_not_generate,
            configuration=lambda: configuration,
        )
        assert (
            restored.get(
                f.professor_id, f.course_a_id, draft.profile_id, artifact["artifact_id"]
            )
            == reviewed
        )
        assert (
            reopened.get_teaching_profile(draft.profile_id).preview_sha256
            == artifact["artifact_sha256"]
        )
    finally:
        reopened.close()


@pytest.mark.asyncio
async def test_changed_composition_cannot_approve_saved_preview(environment):
    app, repo, f, *_ = environment
    service = app.state.generated_preview_service
    draft = new_profile(environment)
    artifact = await service.create(
        f.professor_id,
        f.course_a_id,
        draft.profile_id,
        request(),
        resolve_snapshot=lambda _: snapshot(environment),
    )
    original = service.configuration()
    service.configuration = lambda: {**original, "model": "changed-model"}
    with pytest.raises(TeachingProfileError, match="changed"):
        service.approve(
            f.professor_id,
            f.course_a_id,
            draft.profile_id,
            artifact["artifact_id"],
            GeneratedPreviewApproval(
                artifact_sha256=artifact["artifact_sha256"],
                decisions=[{"case_id": "case1", "decision": "accept"}],
            ),
            resolve_snapshot=lambda _: snapshot(environment),
        )
    assert repo.get_teaching_profile(draft.profile_id).status == "draft"
    assert (
        service.get(
            f.professor_id, f.course_a_id, draft.profile_id, artifact["artifact_id"]
        )["review_status"]
        == "unreviewed"
    )


def test_withdrawal_cancels_pending_and_queued_outreach(environment):
    from src.digital_twin.student import (
        OutreachChannel,
        ProactiveOutreachError,
        ProactiveOutreachService,
    )
    from tests.digital_twin.test_proactive_outreach import NOW, _schedule

    _, repo, f, profiles, profile, _, _ = environment
    outreach = ProactiveOutreachService(repo)
    outreach.update_preference(
        f.student_a_id,
        f.course_a_id,
        channel=OutreachChannel.DISCORD,
        enabled=True,
        timezone="UTC",
        quiet_hours_start="23:00",
        quiet_hours_end="06:00",
        max_messages_per_7_days=3,
        destination_ref="synthetic-private-destination",
        private_destination=True,
    )
    queued_trigger = _schedule(outreach, f, channel=OutreachChannel.DISCORD)
    queued = outreach.process_trigger(queued_trigger.id, now=NOW)
    assert queued.outcome == "queued"
    pending = _schedule(
        outreach,
        f,
        channel=OutreachChannel.DISCORD,
        idempotency_key="pending-before-profile-withdrawal",
    )
    assert repo.list_delivery_outbox()[0].status == "pending"
    profiles.withdraw(f.professor_id, f.course_a_id, profile.profile_id)
    assert repo.get_proactive_trigger(pending.id).status == "cancelled"
    assert repo.get_proactive_message(queued.message.message.id).status == "cancelled"
    assert repo.list_delivery_outbox()[0].status == "cancelled"
    assert outreach.process_trigger(pending.id, now=NOW).outcome == "suppressed"
    with pytest.raises(ProactiveOutreachError, match="withdrawn"):
        _schedule(
            outreach,
            f,
            channel=OutreachChannel.DISCORD,
            idempotency_key="after-profile-withdrawal",
        )


def test_owned_ingestion_to_generated_preview_and_approval_api(environment):
    from fastapi.testclient import TestClient
    from src.digital_twin.onboarding import create_session
    from src.digital_twin.tutor_policy import SourceLabel
    from tests.api.test_publication_api import _headers

    app, repo, f, _, _, release, provider = environment
    session = create_session("preview-api-owned-session")
    session.owner_account_id = f.professor_id
    session.course_id = f.course_a_id
    session.policy = release.policy
    app.state.session_repository.save(session)
    job, created = app.state.ingestion_job_service.enqueue_source(
        b"Cache coherence keeps replicated processor data consistent.",
        mime_type="text/plain",
        deidentified_reviewed=True,
        course_id=f.course_a_id,
        artifact_id="preview-api-notes",
        title="Synthetic teaching notes",
        version=1,
        professor_id=f.professor_id,
        display_allowed=True,
        source_label=SourceLabel.COURSE_APPROVED,
        idempotency_key="preview-api-source",
    )
    assert created
    completed = app.state.ingestion_job_service.process_one("preview-api-worker")
    assert completed.status.value == "succeeded", completed.error_message
    draft = new_profile(environment)
    payload = request().model_dump(mode="json")
    payload.update(session_id=session.session_id, ingestion_job_ids=[job.id])
    url = f"/api/professor/courses/{f.course_a_id}/teaching-profiles/{draft.profile_id}/generated-previews"
    client = TestClient(app)
    try:
        headers = _headers(f.professor_id)
        result = client.post(url, headers=headers, json=payload)
        assert result.status_code == 201, result.text
        artifact = result.json()
        assert artifact["status"] == "complete", artifact
        assert artifact["cases"][0]["turns"][0]["citations"]
        calls = len(provider.calls)
        assert client.get(url, headers=_headers(f.student_a_id)).status_code == 403
        assert client.get(url, headers=headers).json() == [artifact]
        saved_url = url + "/" + artifact["artifact_id"]
        assert client.get(saved_url, headers=headers).json() == artifact
        approved = client.post(
            saved_url + "/approve",
            headers=headers,
            json={
                "artifact_sha256": artifact["artifact_sha256"],
                "decisions": [{"case_id": "case1", "decision": "accept"}],
            },
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["review_status"] == "accepted"
        assert (
            repo.get_teaching_profile(draft.profile_id).preview_sha256
            == artifact["artifact_sha256"]
        )
        assert len(provider.calls) == calls
    finally:
        client.close()
