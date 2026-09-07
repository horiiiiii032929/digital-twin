"""Bounded shadow application for generated professor samples; no live learner writes."""

import hashlib
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from services.llm.budget import BudgetedLlmClient
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.student.generated_preview import (
    GeneratedProfilePreviewService,
    canonical_sha,
)
from src.digital_twin.student.repository import SQLiteStudentRepository
from src.digital_twin.student.models import (
    Account,
    Course,
    CourseMembership,
    DigitalTwinRelease,
)
from src.digital_twin.student.autonomy_models import (
    CourseDomainModelV1,
    CourseConceptV1,
    CourseObjectiveV1,
    CanonicalSourceRangeV1,
)
from src.digital_twin.student.teaching_profile import TeachingProfileStatus
from src.digital_twin.tutor_policy import TutorPolicy, timestamp_now


def attach_generated_preview(app, *, factory, factory_parameters, parent_budget):
    """Transient construction inputs are never serialized in an artifact."""
    root = Path(__file__).resolve().parents[3]

    def source_fingerprint():
        paths = sorted(
            [*(root / "src").rglob("*.py"), *(root / "services").rglob("*.py")]
        )
        return canonical_sha(
            {
                str(path.relative_to(root)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in paths
            }
        )

    startup_source_sha = source_fingerprint()

    def configuration():
        if source_fingerprint() != startup_source_sha:
            raise ValueError("Restart the application after composition source changes")
        generator = app.state.student_service.generator
        selected = getattr(app.state, "experimental_tutoring_configuration", None)
        if selected is None:
            raise ValueError(
                "Generated previews require an explicit experimental composition"
            )
        return {
            "implementation_id": generator.implementation_id,
            "model": generator.model_id,
            "selection": selected,
            "prompt_sha256": hashlib.sha256(
                generator._system_instruction().encode()
            ).hexdigest(),
            "implementation_sha256": startup_source_sha,
        }

    async def run(*, owner, course_id, profile, snapshot, request):
        if parent_budget is None:
            raise ValueError("A bounded provider composition is required")
        budget = BudgetedLlmClient(parent_budget, max_calls=60, max_cost_usd=9.6)
        rows = []
        with TemporaryDirectory(prefix="teaching-preview-") as directory:
            parameters = dict(factory_parameters)
            parameters.update(
                repository=None,
                student_repository=SQLiteStudentRepository(
                    Path(directory) / "preview.sqlite3"
                ),
                identity_repository=None,
                settings=replace(
                    app.state.settings,
                    data_root=Path(directory),
                    database_path=Path(directory) / "preview.sqlite3",
                ),
                autonomy_planner_client=budget,
            )
            shadow = factory(**parameters)
            repo = shadow.state.student_repository
            try:
                repo.save_account(Account(id=owner, role="professor"))
                repo.save_course(
                    Course(
                        id=course_id,
                        title="Isolated professor preview",
                        owner_professor_id=owner,
                    )
                )
                for account, role in [(owner, "professor")]:
                    repo.save_membership(
                        CourseMembership(
                            account_id=account, course_id=course_id, role=role
                        )
                    )
                # Preview-only trust is isolated from global profile approval.
                trusted = profile.model_copy(
                    update={
                        "status": TeachingProfileStatus.APPROVED,
                        "preview_sha256": "0" * 64,
                        "approved_at": timestamp_now(),
                    }
                )
                repo.save_teaching_profile(trusted)
                chunks = [
                    DocumentChunk.model_validate(value) for value in snapshot["chunks"]
                ]
                service = shadow.state.student_service
                release = DigitalTwinRelease(
                    id="preview-release-" + str(uuid4()),
                    course_id=course_id,
                    profile_id=service.profile_id,
                    profile_version=service.profile_version,
                    policy_version=snapshot["policy_version"],
                    policy=TutorPolicy.model_validate(snapshot["policy"]),
                    teaching_profile_id=profile.profile_id,
                    teaching_profile_sha256=profile.content_sha256,
                    chunks=chunks,
                    status="published",
                    evaluation_status="passed",
                )
                repo.save_release(release)
                ranges = []
                for chunk in chunks:
                    ranges.append(
                        CanonicalSourceRangeV1(
                            source_artifact_id=chunk.source_artifact_id,
                            source_version=chunk.source_version,
                            source_sha256=chunk.source_checksum,
                            locator=chunk.locator,
                            char_start=0,
                            char_end=max(1, len(chunk.text)),
                        )
                    )
                # Owner supplied semantics apply only to this preview namespace.
                concept = CourseConceptV1(
                    concept_id="preview-concept",
                    label=request.concept_label,
                    description=request.concept_description,
                    canonical_ranges=ranges,
                )
                repo.save_course_domain_model(
                    CourseDomainModelV1(
                        domain_model_id="preview-domain",
                        course_id=course_id,
                        release_id=release.id,
                        release_sha256=hashlib.sha256(
                            release.model_dump_json().encode()
                        ).hexdigest(),
                        version=1,
                        concepts=[concept],
                        objectives=[
                            CourseObjectiveV1(
                                objective_id="preview-objective",
                                statement=request.objective,
                                concept_ids=[concept.concept_id],
                            )
                        ],
                        approved_by=owner,
                    )
                )
                for case in request.cases:
                    student = "preview-student-" + str(uuid4())
                    repo.save_account(Account(id=student, role="student"))
                    repo.save_membership(
                        CourseMembership(
                            account_id=student, course_id=course_id, role="student"
                        )
                    )
                    row = {
                        "case_id": case.case_id,
                        "student_messages": case.student_messages,
                        "turns": [],
                        "error_code": None,
                    }
                    rows.append(row)
                    try:
                        conversation = service.create_conversation(student, course_id)
                        for index, message in enumerate(case.student_messages):
                            turn = await service.submit_message(
                                student,
                                conversation.id,
                                content=message,
                                client_request_id=f"preview-{case.case_id}-{index}",
                            )
                            row["turns"].append(
                                {
                                    "student": turn.student_message.content,
                                    "tutor": turn.tutor_message.content,
                                    "action": turn.tutor_message.action,
                                    "citations": [
                                        citation.model_dump(mode="json")
                                        for citation in turn.citations
                                    ],
                                    "trace": turn.tutor_message.trace.model_dump(
                                        mode="json"
                                    )
                                    if turn.tutor_message.trace
                                    else None,
                                }
                            )
                            if turn.tutor_message.action.startswith("safe-") or (
                                turn.tutor_message.trace is not None
                                and "failure" in turn.tutor_message.trace.policy_action
                            ):
                                row["error_code"] = "tutoring_guard_failure"
                    except Exception as error:
                        row["error_code"] = type(error).__name__
            finally:
                for name in (
                    "student_repository",
                    "identity_repository",
                    "ingestion_job_repository",
                ):
                    getattr(shadow.state, name).close()
        ledger = budget.snapshot()
        complete = (
            len(rows) == len(request.cases)
            and all(
                row["error_code"] is None
                and len(row["turns"]) == len(row["student_messages"])
                for row in rows
            )
            and not ledger["unknown_cost_calls"]
        )
        return {
            "cases": rows,
            "status": "complete" if complete else "failed",
            "error_code": None if complete else "preview_incomplete",
            "usage": {
                "max_calls": 60,
                "max_cost_usd": 9.6,
                "actual_calls": ledger["calls"],
                "known_cost_usd": ledger["reported_cost_usd"]
                if not ledger["unknown_cost_calls"]
                else None,
                "unknown_cost_calls": ledger["unknown_cost_calls"],
            },
        }

    app.state.generated_preview_service = GeneratedProfilePreviewService(
        app.state.teaching_profile_service, runner=run, configuration=configuration
    )
