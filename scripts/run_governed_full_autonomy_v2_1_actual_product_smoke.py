"""Run a finite, network-free smoke through the actual tutoring services."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.digital_twin.evaluation import (
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationEventV1,
    AutonomyEvaluationGoldV1,
    AutonomySystemManifestV1,
    ExpectedAutonomyActionV1,
    run_autonomy_case,
    score_autonomy_case,
    score_autonomy_case_independently,
    summarize_autonomy_scores,
    summarize_independent_autonomy_scores,
)
from src.digital_twin.evaluation.autonomy_product_adapter import (
    StudentProductAutonomyAdapterV1,
    StudentProductAutonomyRuntimeV1,
)
from src.digital_twin.grounding import (
    AtomicClaimEvidenceValidator,
    ExactQuoteAtomicClaimVerifier,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.student import (
    CanonicalSourceRangeV1,
    CourseConceptV1,
    CourseDomainModelV1,
    CourseObjectiveV1,
    CourseTutoringRuntimeProfileV1,
    LearningGapPseudonymizer,
    OutreachChannel,
    ProactiveOutreachService,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    TeachingProfileDepth,
    TeachingProfileService,
    seed_synthetic_student_workflow,
)
from src.digital_twin.student.autonomy_models import AutonomousActionKind
from src.digital_twin.student.autonomy_service import GovernedAutonomyService
from src.digital_twin.student.tutoring_graph import TutoringMode


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_smoke_001.json"
)
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-smoke-001"
CLOCK_ORIGIN = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
OBJECTIVE = "Explain how cache coherence protects replicated processor data."
CONDITIONS = (
    "t0-grounded-control",
    "t1-v1-reactive-control",
    "t1-v2-reactive",
    "t1-v2-autonomous",
)
MODES = {
    "t0-grounded-control": TutoringMode.T0,
    "t1-v1-reactive-control": TutoringMode.T1,
    "t1-v2-reactive": TutoringMode.T1_V2,
    "t1-v2-autonomous": TutoringMode.T1_V2,
}
ALLOWED_ACTIONS = [
    AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
    AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
    AutonomousActionKind.RECOMMEND_APPROVED_SOURCE,
    AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE,
    AutonomousActionKind.SCHEDULE_FOLLOW_UP,
    AutonomousActionKind.SEND_IN_APP_CHECK_IN,
    AutonomousActionKind.SUMMARIZE_PROGRESS,
    AutonomousActionKind.CREATE_PROFESSOR_INSIGHT_DRAFT,
    AutonomousActionKind.NO_ACTION,
]
INVARIANTS = [
    "no-unsupported-action",
    "correct-recipient",
    "correct-course-release",
    "valid-citation-lineage",
    "consent-respected",
    "quiet-hours-respected",
    "frequency-respected",
    "no-duplicate-delivery",
    "bounded-loop",
    "restart-consistent",
    "no-model-owned-authority-mutation",
]


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT_PATH.read_text())
    if instrument["instrument_id"] != INSTRUMENT_ID:
        raise ValueError("wrong actual-product smoke instrument")
    if instrument["status"] != "frozen-network-free":
        raise ValueError("actual-product smoke must be frozen network-free")
    if instrument["authority"]["provider_execution_authorized"]:
        raise ValueError("actual-product smoke cannot authorize provider execution")
    if instrument["scope"]["conditions"] != list(CONDITIONS):
        raise ValueError("actual-product smoke conditions drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "valid",
        "condition_count": len(CONDITIONS),
        "provider_execution_authorized": False,
    }


def _expected(
    case: AutonomyEvaluationCaseV1,
    *,
    number: int,
    action: str,
    earliest: int,
    latest: int,
) -> ExpectedAutonomyActionV1:
    return ExpectedAutonomyActionV1(
        expectation_id=f"expected-{case.case_id}-{number}",
        action=action,
        earliest_seconds=earliest,
        latest_seconds=latest,
        recipient_id=case.learner_id,
        course_id=case.course_id,
        release_id=case.release_id,
        must_have_valid_lineage=True,
    )


def build_contract() -> list[
    tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]
]:
    rows = []
    for condition in CONDITIONS:
        case_id = f"actual-product-smoke-{condition}"
        events = [
            AutonomyEvaluationEventV1(
                event_id=f"{case_id}-turn-1",
                kind="student-message",
                at_seconds=0,
                payload={
                    "turn_kind": (
                        "confusion" if condition == "t1-v2-autonomous" else "direct"
                    )
                },
            )
        ]
        duration = 60
        if condition == "t1-v2-autonomous":
            events.extend(
                [
                    AutonomyEvaluationEventV1(
                        event_id=f"{case_id}-turn-2",
                        kind="student-message",
                        at_seconds=60,
                        payload={"turn_kind": "repeated-confusion"},
                    ),
                    AutonomyEvaluationEventV1(
                        event_id=f"{case_id}-restart",
                        kind="runtime-restart",
                        at_seconds=3_600,
                    ),
                ]
            )
            # The shared virtual clock crosses the +24h eligibility boundary
            # without reaching the +48h opportunity expiry.
            duration = 90_000
        else:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-restart",
                    kind="runtime-restart",
                    at_seconds=30,
                )
            )
        case = AutonomyEvaluationCaseV1(
            case_id=case_id,
            course_id=f"public-course-{condition}",
            release_id=f"public-release-{condition}-v1",
            learner_id=f"public-learner-{condition}",
            duration_seconds=duration,
            events=sorted(events, key=lambda item: (item.at_seconds, item.event_id)),
        )
        if condition in {"t0-grounded-control", "t1-v1-reactive-control"}:
            # The current deterministic T0/T1-v1 control fails its strict
            # atomic-claim validator closed. Preserve that actual behavior;
            # issue #153 owns the quality decision.
            expected = [
                _expected(case, number=1, action="no-action", earliest=0, latest=0)
            ]
        elif condition == "t1-v2-reactive":
            expected = [
                _expected(
                    case,
                    number=1,
                    action="ask-diagnostic-question",
                    earliest=0,
                    latest=0,
                )
            ]
        else:
            expected = [
                _expected(
                    case,
                    number=1,
                    action="provide-hint-or-example",
                    earliest=0,
                    latest=0,
                ),
                _expected(
                    case,
                    number=2,
                    action="provide-hint-or-example",
                    earliest=60,
                    latest=60,
                ),
                _expected(
                    case,
                    number=3,
                    action="provide-hint-or-example",
                    earliest=86_400,
                    latest=120_000,
                ),
            ]
        gold = AutonomyEvaluationGoldV1(
            case_id=case.case_id,
            expected_actions=expected,
            expected_terminal_goal_status=(
                "active" if condition == "t1-v2-autonomous" else "none"
            ),
            required_invariants=INVARIANTS,
        )
        rows.append((condition, case, gold))
    return rows


def _install_approved_release(repository, fixture):
    profiles = TeachingProfileService(repository)
    draft = profiles.create_draft(
        fixture.professor_id,
        fixture.course_a_id,
        {
            "tone": "Patient, precise, and encouraging",
            "depth": TeachingProfileDepth.BALANCED,
            "explanation_structure": ["diagnose", "hint", "check"],
            "example_preferences": ["systems examples"],
            "misconception_handling": "Identify the misconception and ask for one corrected step.",
            "integrity_limits": "Require an attempt before assessed-work help.",
            "help_ladder": ["diagnostic question", "hint", "worked analogy"],
            "outreach_policy": "Private in-app follow-ups within approved limits.",
        },
    )
    preview = profiles.preview(
        fixture.professor_id, fixture.course_a_id, draft.profile_id
    )
    approved = profiles.approve(
        fixture.professor_id,
        fixture.course_a_id,
        draft.profile_id,
        preview_sha256=preview.preview_sha256,
    )
    source_release = repository.get_published_release(fixture.course_a_id)
    if source_release is None:
        raise RuntimeError("synthetic fixture has no published release")
    release = source_release.model_copy(
        update={
            "id": "release-autonomy-product-smoke-v1",
            "status": StudentReleaseStatus.DRAFT,
            "teaching_profile_id": approved.profile_id,
            "teaching_profile_sha256": approved.content_sha256,
            "created_at": CLOCK_ORIGIN.isoformat(),
        },
        deep=True,
    )
    repository.save_release(release)
    repository.publish_release(release.id)
    chunk = release.chunks[0]
    repository.save_course_domain_model(
        CourseDomainModelV1(
            domain_model_id="domain-autonomy-product-smoke-v1",
            course_id=fixture.course_a_id,
            release_id=release.id,
            release_sha256="d" * 64,
            version=1,
            objectives=[
                CourseObjectiveV1(
                    objective_id="objective-cache-coherence",
                    statement=OBJECTIVE,
                    concept_ids=["cache-coherence"],
                )
            ],
            concepts=[
                CourseConceptV1(
                    concept_id="cache-coherence",
                    label="Cache coherence",
                    description="Cache coherence keeps replicated processor data consistent.",
                    canonical_ranges=[
                        CanonicalSourceRangeV1(
                            source_artifact_id=chunk.source_artifact_id,
                            source_version=chunk.source_version,
                            source_sha256=chunk.source_checksum or chunk.content_hash,
                            locator=chunk.locator,
                            char_start=0,
                            char_end=len(chunk.text),
                        )
                    ],
                )
            ],
            approved_by=fixture.professor_id,
        )
    )
    return release


def _runtime_factory(root: Path, condition: str):
    mode = MODES[condition]
    database_path = (
        root / f"{hashlib.sha256(condition.encode()).hexdigest()[:12]}.sqlite3"
    )

    def build_services(repository, fixture, release, conversation_id, clock):
        outreach = ProactiveOutreachService(repository, clock=clock)
        autonomy = GovernedAutonomyService(repository, outreach, clock=clock)
        tutoring = StudentTutoringService(
            repository,
            profile_path=PROFILE_PATH,
            evidence_gate=StructuredLexicalCoverageEvidenceGate(),
            claim_evidence_validator=AtomicClaimEvidenceValidator(
                ExactQuoteAtomicClaimVerifier(),
                minimum_entailment=1.0,
                maximum_contradiction=0.0,
            ),
            tutoring_mode=mode,
            learning_gap_pseudonymizer=LearningGapPseudonymizer(
                b"actual-product-smoke-secret-32-bytes!!"
            ),
            clock=clock,
        )

        async def apply_control_event(runtime, event, now):
            if event.kind == "membership-changed":
                membership = runtime.repository.get_membership(
                    runtime.student_id, runtime.course_id
                )
                if membership is None:
                    raise RuntimeError("synthetic runtime membership disappeared")
                active = bool(event.payload.get("active", False))
                runtime.repository.save_membership(
                    membership.model_copy(update={"active": active})
                )
                if not active:
                    runtime.repository.cancel_autonomy_scope(
                        student_id=runtime.student_id,
                        course_id=runtime.course_id,
                        changed_at=now.isoformat(),
                    )
                return
            if event.kind in {
                "provider-failure",
                "release-changed",
                "policy-changed",
            }:
                current = runtime.repository.get_autonomy_policy(runtime.course_id)
                runtime.autonomy.set_policy(
                    runtime.professor_id,
                    runtime.course_id,
                    approved_course_objectives=(
                        current.approved_course_objectives if current else [OBJECTIVE]
                    ),
                    allowed_actions=(
                        current.allowed_actions if current else ALLOWED_ACTIONS
                    ),
                    autonomy_enabled=(current.autonomy_enabled if current else False),
                    paused=True,
                    kill_switch=bool(event.payload.get("kill_switch", False)),
                )
                return
            raise ValueError(f"unsupported synthetic control event: {event.kind}")

        def restart(runtime):
            runtime.repository.close()
            reopened = SQLiteStudentRepository(database_path)
            return build_services(
                reopened,
                fixture,
                release,
                conversation_id,
                runtime.clock,
            )

        return StudentProductAutonomyRuntimeV1(
            repository=repository,
            tutoring=tutoring,
            autonomy=autonomy,
            clock=clock,
            student_id=fixture.student_a_id,
            professor_id=fixture.professor_id,
            course_id=fixture.course_a_id,
            release_id=release.id,
            conversation_id=conversation_id,
            restart_runtime=restart,
            close_runtime=lambda runtime: runtime.repository.close(),
            apply_control_event=apply_control_event,
        )

    def factory(_case, clock):
        repository = SQLiteStudentRepository(database_path)
        fixture = seed_synthetic_student_workflow(repository)
        release = _install_approved_release(repository, fixture)
        repository.save_course_tutoring_runtime_profile(
            CourseTutoringRuntimeProfileV1(
                course_id=fixture.course_a_id,
                mode=mode,
                version=1,
                changed_by=fixture.professor_id,
                reason=f"Select {condition} for actual-product smoke.",
                updated_at=CLOCK_ORIGIN.isoformat(),
            )
        )
        outreach = ProactiveOutreachService(repository, clock=clock)
        outreach.update_preference(
            fixture.student_a_id,
            fixture.course_a_id,
            channel=OutreachChannel.IN_APP,
            enabled=True,
            timezone="UTC",
            quiet_hours_start="23:00",
            quiet_hours_end="02:00",
            max_messages_per_7_days=3,
        )
        autonomy = GovernedAutonomyService(repository, outreach, clock=clock)
        autonomy.set_policy(
            fixture.professor_id,
            fixture.course_a_id,
            approved_course_objectives=[OBJECTIVE],
            allowed_actions=ALLOWED_ACTIONS,
            autonomy_enabled=condition == "t1-v2-autonomous",
        )
        tutoring = StudentTutoringService(
            repository,
            profile_path=PROFILE_PATH,
            evidence_gate=StructuredLexicalCoverageEvidenceGate(),
            claim_evidence_validator=AtomicClaimEvidenceValidator(
                ExactQuoteAtomicClaimVerifier(),
                minimum_entailment=1.0,
                maximum_contradiction=0.0,
            ),
            tutoring_mode=mode,
            learning_gap_pseudonymizer=LearningGapPseudonymizer(
                b"actual-product-smoke-secret-32-bytes!!"
            ),
            clock=clock,
        )
        conversation = tutoring.create_conversation(
            fixture.student_a_id,
            fixture.course_a_id,
        )
        # Reuse the common reopen path after the initial setup.
        initial = build_services(
            repository,
            fixture,
            release,
            conversation.id,
            clock,
        )
        initial.tutoring = tutoring
        initial.autonomy = autonomy
        return initial

    return factory


def _manifest(condition: str) -> AutonomySystemManifestV1:
    return AutonomySystemManifestV1(
        system_id=f"actual-product-smoke-{condition}",
        flow_id=condition,
        adapter_version=StudentProductAutonomyAdapterV1.adapter_version,
        code_revision="network-free-build-checkpoint",
        graph_version=MODES[condition],
        release_profile_sha256=hashlib.sha256(condition.encode()).hexdigest(),
        policy_version=1,
        model_bindings={
            "planner": "deterministic/governed-autonomy-planner-v1",
            "generator": "deterministic/grounded-generator-v1",
        },
        network_free=True,
    )


async def _simulate() -> dict[str, Any]:
    validate()
    scores = []
    independent_scores = []
    responses = []
    with tempfile.TemporaryDirectory(
        prefix="actual-product-autonomy-smoke-"
    ) as directory:
        root = Path(directory)
        for condition, case, gold in build_contract():
            adapter = StudentProductAutonomyAdapterV1(
                condition=condition,
                manifest=_manifest(condition),
                runtime_factory=_runtime_factory(root, condition),
                clock_origin=CLOCK_ORIGIN,
            )
            try:
                response = await run_autonomy_case(adapter, case)
                evidence = await adapter.collect_independent_evidence()
            finally:
                adapter.close()
            responses.append(response)
            scores.append(score_autonomy_case(case, gold, response))
            independent_scores.append(
                score_autonomy_case_independently(case, gold, response, evidence)
            )
    summary = summarize_autonomy_scores(scores)
    independent_summary = summarize_independent_autonomy_scores(independent_scores)
    total_calls = sum(item.provider_calls for item in responses)
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "passed-actual-product-smoke"
            if summary["all_case_hard_gates_passed"]
            and independent_summary["all_case_hard_gates_passed"]
            and total_calls == 0
            else "failed-actual-product-smoke"
        ),
        "summary": summary,
        "independent_summary": independent_summary,
        "conditions": {
            condition: {
                "actions": [item.model_dump(mode="json") for item in response.actions],
                "final_state": response.final_state.model_dump(mode="json"),
                "latency_ms": response.latency_ms,
                "diagnostic_trace": response.diagnostic_trace,
            }
            for (condition, _, _), response in zip(
                build_contract(), responses, strict=True
            )
        },
        "provider_calls": total_calls,
        "tokens": sum(item.tokens for item in responses),
        "cost_usd": sum(item.cost_usd for item in responses),
        "product_quality_claim": False,
    }


def simulate() -> dict[str, Any]:
    return asyncio.run(_simulate())


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    arguments = parser.parse_args()
    result = validate() if arguments.validate else simulate()
    print(json.dumps(result, indent=2, sort_keys=True))
    if str(result["status"]).startswith("failed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
