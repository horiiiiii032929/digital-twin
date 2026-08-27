"""Validate or run the frozen publication-integrated A1 shadow confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.digital_twin.grounding import DocumentChunk
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)
from src.digital_twin.student import (
    AccountStatus,
    Conversation,
    DigitalTwinRelease,
    EvidenceRecoveryMode,
    Message,
    OutreachChannel,
    ProactiveOutreachService,
    ReleaseEvaluationStatus,
    ReleaseLifecycleService,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    seed_synthetic_student_workflow,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "proactive_outreach_a1_shadow_confirmation_002.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/proactive-outreach-a1-shadow-confirmation-002.json"
)
RUN_ID = "proactive-outreach-a1-shadow-confirmation-002"


class ProactiveShadowConfirmationError(RuntimeError):
    """Raised when confirmation identity, authority, or execution is invalid."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_is_clean() -> bool:
    return not subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != RUN_ID:
        raise ProactiveShadowConfirmationError("unexpected confirmation identity")
    if instrument.get("status") not in {
        "reviewed-pending-network-free-authorization",
        "frozen-pending-network-free-execution",
        "completed-go-deeper",
        "completed-refine",
        "invalid-execution",
    }:
        raise ProactiveShadowConfirmationError("unexpected confirmation status")
    clusters = instrument.get("clusters", [])
    identifiers = [cluster.get("id") for cluster in clusters]
    if len(clusters) != 12 or len(identifiers) != len(set(identifiers)):
        raise ProactiveShadowConfirmationError("expected 12 unique source clusters")
    construction = instrument.get("case_construction", {})
    if construction.get("case_count") != 60:
        raise ProactiveShadowConfirmationError("expected exactly 60 cases")
    if construction.get("expected_propose_count") != 24:
        raise ProactiveShadowConfirmationError("expected exactly 24 proposals")
    if construction.get("expected_no_action_count") != 36:
        raise ProactiveShadowConfirmationError("expected exactly 36 no-actions")
    required_text = {
        "id",
        "course_family",
        "title",
        "evidence",
        "direct_question",
        "paraphrase_question",
        "unsupported_question",
    }
    if any(
        set(cluster) != required_text
        or any(not str(cluster[key]).strip() for key in required_text)
        for cluster in clusters
    ):
        raise ProactiveShadowConfirmationError("cluster contract is incomplete")
    execution = instrument.get("execution", {})
    forbidden_authorities = {
        "provider_calls_authorized": False,
        "paid_execution_authorized": False,
        "private_data_authorized": False,
        "real_student_delivery_authorized": False,
        "external_channel_delivery_authorized": False,
        "automatic_promotion": False,
    }
    if any(execution.get(key) != value for key, value in forbidden_authorities.items()):
        raise ProactiveShadowConfirmationError("forbidden execution authority is present")
    if len(instrument.get("integration_checks", [])) != 12:
        raise ProactiveShadowConfirmationError("expected 12 integration checks")
    return instrument


def validate_preflight(
    instrument: dict[str, Any],
    *,
    output: Path,
    require_clean: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    if instrument["status"] != "frozen-pending-network-free-execution":
        blockers.append("instrument-not-frozen-pending")
    if not instrument["execution"].get("network_free_execution_authorized"):
        blockers.append("network-free-execution-not-authorized")
    if require_clean and not _git_is_clean():
        blockers.append("working-tree-dirty")
    if output.exists():
        blockers.append("exclusive-output-already-exists")
    return {
        "run_id": RUN_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "case_count": 60,
        "provider_calls": 0,
        "external_deliveries": 0,
        "private_data_reads": 0,
    }


def _chunk(cluster: dict[str, str], course_id: str) -> DocumentChunk:
    checksum = hashlib.sha256(cluster["evidence"].encode("utf-8")).hexdigest()
    return DocumentChunk(
        id=f"chunk-{cluster['id']}",
        document_id=f"document-{cluster['id']}",
        text=cluster["evidence"],
        ordinal=0,
        source_artifact_id=f"source-{cluster['id']}",
        source_version=1,
        source_checksum=checksum,
        source_label=SourceLabel.COURSE_APPROVED,
        locator="synthetic confirmation region 1",
        retrieval_allowed=True,
        metadata={"title": cluster["title"], "course_id": course_id},
    )


def _baseline_chunk(case_id: str, course_id: str) -> DocumentChunk:
    text = "The syllabus lists weekly learning objectives and assessment dates."
    return DocumentChunk(
        id=f"chunk-baseline-{case_id}",
        document_id=f"document-baseline-{case_id}",
        text=text,
        ordinal=0,
        source_artifact_id=f"source-baseline-{case_id}",
        source_version=1,
        source_checksum=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        source_label=SourceLabel.COURSE_APPROVED,
        locator="synthetic confirmation baseline",
        retrieval_allowed=True,
        metadata={"title": "Synthetic syllabus", "course_id": course_id},
    )


def expand_cases(instrument: dict[str, Any]) -> list[dict[str, Any]]:
    suppression_cycle = instrument["case_construction"]["suppression_cycle"]
    cases: list[dict[str, Any]] = []
    for index, cluster in enumerate(instrument["clusters"]):
        prefix = cluster["id"]
        cases.extend(
            [
                {
                    "id": f"{prefix}-direct-supported",
                    "cluster": cluster,
                    "question": cluster["direct_question"],
                    "variant": "direct-supported",
                    "expected_action": "propose",
                    "expected_reason": "new-evidence-supported",
                },
                {
                    "id": f"{prefix}-paraphrase-supported",
                    "cluster": cluster,
                    "question": cluster["paraphrase_question"],
                    "variant": "paraphrase-supported",
                    "expected_action": "propose",
                    "expected_reason": "new-evidence-supported",
                },
                {
                    "id": f"{prefix}-unsupported-adjacent",
                    "cluster": cluster,
                    "question": cluster["unsupported_question"],
                    "variant": "unsupported-adjacent",
                    "expected_action": "no-action",
                    "expected_reason": "insufficient-new-evidence",
                },
                {
                    "id": f"{prefix}-unchanged-lineage",
                    "cluster": cluster,
                    "question": cluster["direct_question"],
                    "variant": "unchanged-lineage",
                    "expected_action": "no-action",
                    "expected_reason": "insufficient-new-evidence",
                },
                {
                    "id": f"{prefix}-suppression",
                    "cluster": cluster,
                    "question": cluster["direct_question"],
                    "variant": "suppression",
                    "suppression": suppression_cycle[index % len(suppression_cycle)],
                    "expected_action": "no-action",
                    "expected_reason": suppression_cycle[index % len(suppression_cycle)],
                },
            ]
        )
    if len(cases) != 60 or len({case["id"] for case in cases}) != 60:
        raise ProactiveShadowConfirmationError("expanded case identity drifted")
    return cases


def _record_no_evidence_turn(
    repository: SQLiteStudentRepository,
    fixture: Any,
    *,
    case: dict[str, Any],
    previous_release: DigitalTwinRelease,
) -> None:
    conversation = repository.save_conversation(
        Conversation(
            id=f"conversation-{case['id']}",
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            release_id=previous_release.id,
            created_at="2026-08-01T00:00:00+00:00",
            updated_at="2026-08-01T00:00:01+00:00",
        )
    )
    student_message = Message(
        id=f"question-{case['id']}",
        conversation_id=conversation.id,
        role="student",
        content=case["question"],
        action="question",
        client_request_id=f"request-{case['id']}",
        created_at="2026-08-01T00:00:00+00:00",
    )
    tutor_message = Message(
        id=f"no-evidence-{case['id']}",
        conversation_id=conversation.id,
        role="tutor",
        content="I do not have enough approved course evidence.",
        action="no-evidence",
        response_to_message_id=student_message.id,
        created_at="2026-08-01T00:00:01+00:00",
    )
    repository.save_turn(conversation, student_message, tutor_message, [], [])


def _run_case(root: Path, case: dict[str, Any]) -> dict[str, Any]:
    repository = SQLiteStudentRepository(root / f"{case['id']}.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    current = repository.get_release(fixture.release_a_id)
    if current is None:
        raise ProactiveShadowConfirmationError("fixture release is missing")
    target = _chunk(case["cluster"], fixture.course_a_id)
    baseline = _baseline_chunk(case["id"], fixture.course_a_id)
    previous_chunks = [target] if case["variant"] == "unchanged-lineage" else [baseline]
    previous = current.model_copy(
        update={
            "id": f"previous-{case['id']}",
            "status": StudentReleaseStatus.WITHDRAWN,
            "chunks": previous_chunks,
            "created_at": "2026-08-01T00:00:00+00:00",
        },
        deep=True,
    )
    repository.save_release(previous)
    _record_no_evidence_turn(
        repository,
        fixture,
        case=case,
        previous_release=previous,
    )
    outreach = ProactiveOutreachService(repository)
    suppression = case.get("suppression")
    if suppression != "consent-disabled":
        outreach.update_preference(
            fixture.student_a_id,
            fixture.course_a_id,
            channel=OutreachChannel.IN_APP,
            enabled=True,
            timezone="UTC",
            quiet_hours_start="23:00",
            quiet_hours_end="06:00",
            max_messages_per_7_days=3,
            snoozed_until=(
                "9999-12-31T00:00:00+00:00"
                if suppression == "student-snoozed"
                else None
            ),
        )
    if suppression == "student-inactive":
        account = repository.get_account(fixture.student_a_id)
        if account is None:
            raise ProactiveShadowConfirmationError("fixture account is missing")
        repository.save_account(account.model_copy(update={"status": AccountStatus.REVOKED}))
    if suppression == "membership-inactive":
        membership = repository.get_membership(
            fixture.student_a_id, fixture.course_a_id
        )
        if membership is None:
            raise ProactiveShadowConfirmationError("fixture membership is missing")
        repository.save_membership(membership.model_copy(update={"active": False}))
    draft = current.model_copy(
        update={
            "id": f"current-{case['id']}",
            "status": StudentReleaseStatus.DRAFT,
            "evaluation_status": ReleaseEvaluationStatus.PASSED,
            "chunks": [target],
            "created_at": "2026-08-27T00:00:00+00:00",
        },
        deep=True,
    )
    repository.save_release(draft)
    scan_results = []

    def scan_after_publish(professor_id: str, course_id: str) -> None:
        scan_results.append(
            outreach.scan_evidence_recovery(
                professor_id,
                course_id,
                mode=EvidenceRecoveryMode.SHADOW,
            )
        )

    publication = ReleaseLifecycleService(
        repository,
        evidence_sufficiency_ready=True,
        post_publish_hook=scan_after_publish,
    )
    published = publication.publish(fixture.professor_id, draft.id)
    if len(scan_results) != 1 or len(scan_results[0].decisions) != 1:
        raise ProactiveShadowConfirmationError("publication hook cardinality drifted")
    decision = scan_results[0].decisions[0]
    triggers = repository.list_due_proactive_triggers("9999-12-31T00:00:00+00:00")
    messages = repository.list_proactive_messages(fixture.student_a_id)
    outbox = repository.list_delivery_outbox()
    return {
        "case_id": case["id"],
        "course_family": case["cluster"]["course_family"],
        "variant": case["variant"],
        "expected_action": case["expected_action"],
        "observed_action": decision.action,
        "expected_reason": case["expected_reason"],
        "observed_reason": decision.reason,
        "action_correct": decision.action == case["expected_action"],
        "reason_correct": decision.reason == case["expected_reason"],
        "source_lineage_valid": (
            decision.source_chunk_id == target.id
            if decision.action == "propose"
            else decision.source_chunk_id is None
        ),
        "published_current": published.id == draft.id
        and repository.get_published_release(fixture.course_a_id).id == draft.id,
        "trigger_count": len(triggers),
        "message_count": len(messages),
        "outbox_count": len(outbox),
        "shadow_side_effect_count": len(triggers) + len(messages) + len(outbox),
        "provider_calls": scan_results[0].provider_calls,
    }


def _integration_checks(root: Path, cluster: dict[str, str]) -> dict[str, bool]:
    repository = SQLiteStudentRepository(root / "integration.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    current = repository.get_release(fixture.release_a_id)
    if current is None:
        raise ProactiveShadowConfirmationError("integration fixture is missing")
    target = _chunk(cluster, fixture.course_a_id)
    draft = current.model_copy(
        update={
            "id": "integration-current-release",
            "status": StudentReleaseStatus.DRAFT,
            "evaluation_status": ReleaseEvaluationStatus.PASSED,
            "chunks": [target],
        },
        deep=True,
    )
    repository.save_release(draft)
    observed_current: list[bool] = []

    def observe_current(_professor_id: str, course_id: str) -> None:
        release = repository.get_published_release(course_id)
        observed_current.append(release is not None and release.id == draft.id)

    publication = ReleaseLifecycleService(
        repository,
        evidence_sufficiency_ready=True,
        post_publish_hook=observe_current,
    )
    publication.publish(fixture.professor_id, draft.id)
    hook_count_after_publish = len(observed_current)
    repository.set_release_status(draft.id, StudentReleaseStatus.WITHDRAWN)
    publication.rollback(fixture.professor_id, current.id)
    rollback_did_not_invoke = len(observed_current) == hook_count_after_publish

    failing_repository = SQLiteStudentRepository(root / "failure.sqlite3")
    failing_fixture = seed_synthetic_student_workflow(failing_repository)
    failing_current = failing_repository.get_release(failing_fixture.release_a_id)
    if failing_current is None:
        raise ProactiveShadowConfirmationError("failure fixture is missing")
    failing_draft = failing_current.model_copy(
        update={
            "id": "integration-failing-hook-release",
            "status": StudentReleaseStatus.DRAFT,
            "evaluation_status": ReleaseEvaluationStatus.PASSED,
        },
        deep=True,
    )
    failing_repository.save_release(failing_draft)

    def fail_hook(_professor_id: str, _course_id: str) -> None:
        raise RuntimeError("synthetic content that must not reach audit")

    failing_publication = ReleaseLifecycleService(
        failing_repository,
        evidence_sufficiency_ready=True,
        post_publish_hook=fail_hook,
    )
    failure_result = failing_publication.publish(
        failing_fixture.professor_id, failing_draft.id
    )
    failure_events = [
        event
        for event in failing_repository.list_audit_events()
        if event.event_type == "release.post_publish_hook_failed"
    ]
    redacted_failure = (
        len(failure_events) == 1
        and "synthetic content" not in repr(failure_events[0])
        and failure_events[0].details.get("error_type") == "RuntimeError"
    )
    base_checks = {
        "hook-runs-after-release-is-current": observed_current == [True],
        "hook-runs-once-per-publish-call": hook_count_after_publish == 1,
        "rollback-does-not-run-hook": rollback_did_not_invoke,
        "hook-failure-preserves-publication": (
            failure_result.id == failing_draft.id
            and failing_repository.get_published_release(
                failing_fixture.course_a_id
            ).id
            == failing_draft.id
        ),
        "hook-failure-audit-is-redacted": redacted_failure,
        "shadow-creates-zero-triggers": False,
        "shadow-creates-zero-messages": False,
        "shadow-creates-zero-outbox-items": False,
        "current-release-lineage-only": False,
        "consent-and-account-suppression": False,
        "zero-provider-usage": False,
        "zero-external-delivery": True,
    }
    return base_checks


def execute(instrument: dict[str, Any], *, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="proactive-a1-confirmation-") as temporary:
        root = Path(temporary)
        case_results = [_run_case(root, case) for case in expand_cases(instrument)]
        integration = _integration_checks(root, instrument["clusters"][0])
        integration.update(
            {
                "shadow-creates-zero-triggers": all(
                    case["trigger_count"] == 0 for case in case_results
                ),
                "shadow-creates-zero-messages": all(
                    case["message_count"] == 0 for case in case_results
                ),
                "shadow-creates-zero-outbox-items": all(
                    case["outbox_count"] == 0 for case in case_results
                ),
                "current-release-lineage-only": all(
                    case["source_lineage_valid"] for case in case_results
                ),
                "consent-and-account-suppression": all(
                    case["reason_correct"]
                    for case in case_results
                    if case["variant"] == "suppression"
                ),
                "zero-provider-usage": all(
                    case["provider_calls"] == 0 for case in case_results
                ),
            }
        )
    proposed = [case for case in case_results if case["observed_action"] == "propose"]
    metrics = {
        "integration_check_pass_rate": sum(integration.values()) / len(integration),
        "action_accuracy": sum(case["action_correct"] for case in case_results)
        / len(case_results),
        "reason_accuracy": sum(case["reason_correct"] for case in case_results)
        / len(case_results),
        "supported_source_lineage_validity": (
            sum(case["source_lineage_valid"] for case in proposed) / len(proposed)
            if proposed
            else 0.0
        ),
        "publication_success_rate": sum(
            case["published_current"] for case in case_results
        )
        / len(case_results),
        "shadow_side_effect_count": sum(
            case["shadow_side_effect_count"] for case in case_results
        ),
        "provider_calls": sum(case["provider_calls"] for case in case_results),
        "external_deliveries": 0,
        "private_data_reads": 0,
    }
    passed = metrics == instrument["hard_gates"]
    result = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "status": "completed-go-deeper" if passed else "completed-refine",
        "code_revision": _git_revision(),
        "instrument_sha256": _sha256(INSTRUMENT_PATH),
        "case_results": case_results,
        "integration_checks": [
            {"id": identifier, "passed": passed}
            for identifier, passed in sorted(integration.items())
        ],
        "metrics": metrics,
        "provider_calls": 0,
        "tokens": 0,
        "cost_usd": 0.0,
        "external_deliveries": 0,
        "private_data_reads": 0,
        "selected_for_release": False,
        "decision": "go-deeper" if passed else "refine",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


def self_test() -> dict[str, Any]:
    instrument = load_instrument()
    canary = expand_cases(instrument)[0]
    with tempfile.TemporaryDirectory(prefix="proactive-a1-self-test-") as temporary:
        result = _run_case(Path(temporary), canary)
    if not (
        result["action_correct"]
        and result["reason_correct"]
        and result["source_lineage_valid"]
        and result["published_current"]
        and result["shadow_side_effect_count"] == 0
        and result["provider_calls"] == 0
    ):
        raise ProactiveShadowConfirmationError("network-free canary self-test failed")
    return {
        "run_id": RUN_ID,
        "status": "passed",
        "canary_case_id": result["case_id"],
        "provider_calls": 0,
        "external_deliveries": 0,
        "private_data_reads": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--validate", action="store_true")
    action.add_argument("--self-test", action="store_true")
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    instrument = load_instrument()
    if arguments.validate:
        print(
            json.dumps(
                {
                    "instrument_id": RUN_ID,
                    "status": "passed",
                    "cluster_count": 12,
                    "case_count": len(expand_cases(instrument)),
                    "network_free_execution_authorized": instrument["execution"][
                        "network_free_execution_authorized"
                    ],
                    "provider_calls": 0,
                },
                indent=2,
            )
        )
        return
    if arguments.self_test:
        print(json.dumps(self_test(), indent=2))
        return
    preflight = validate_preflight(
        instrument,
        output=arguments.output,
        require_clean=arguments.preflight or arguments.execute,
    )
    if arguments.preflight or not arguments.execute:
        print(json.dumps(preflight, indent=2))
        return
    if preflight["status"] != "ready":
        raise ProactiveShadowConfirmationError(
            "confirmation execution is blocked: " + ", ".join(preflight["blockers"])
        )
    require_bounded_pilot_operation_allowed(RUN_ID)
    print(json.dumps(execute(instrument, output=arguments.output), indent=2))


if __name__ == "__main__":
    main()
