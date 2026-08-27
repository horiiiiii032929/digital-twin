"""Run the frozen network-free P0/P1 proactive-outreach development evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from src.digital_twin.student import (
    AccountStatus,
    Conversation,
    DeliveryOutboxItem,
    DiscordWebhookDeliveryAdapter,
    DiscordWebhookRoute,
    EvidenceRecoveryMode,
    Message,
    OutreachChannel,
    ProactiveMessage,
    ProactiveMessageStatus,
    ProactiveOutreachError,
    ProactiveOutreachService,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    seed_synthetic_student_workflow,
)
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/proactive_outreach_a1_development_001.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated/proactive-outreach-a1-development-001.json"
RUN_ID = "proactive-outreach-a1-development-001"
NOW = "2026-08-27T12:00:00+00:00"


class ProactiveDevelopmentError(RuntimeError):
    """Raised when the frozen evaluation cannot execute validly."""


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
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("instrument_id") != RUN_ID:
        raise ProactiveDevelopmentError("unexpected proactive-outreach instrument")
    if payload.get("status") not in {
        "frozen-pending-network-free-execution",
        "completed-go-deeper",
    }:
        raise ProactiveDevelopmentError("unexpected proactive-outreach status")
    cases = payload.get("p1_shadow_cases", [])
    identifiers = [case.get("id") for case in cases]
    if len(cases) != 20 or len(identifiers) != len(set(identifiers)):
        raise ProactiveDevelopmentError("expected 20 unique P1 shadow cases")
    checks = payload.get("p0_mechanism_checks", [])
    if len(checks) != 12 or len(checks) != len(set(checks)):
        raise ProactiveDevelopmentError("expected 12 unique P0 checks")
    expected_execution = {
        "provider_calls_authorized": False,
        "paid_execution_authorized": False,
        "private_data_authorized": False,
        "real_student_delivery_authorized": False,
        "external_channel_delivery_authorized": False,
        "automatic_promotion": False,
    }
    execution = payload.get("execution", {})
    if any(execution.get(key) != value for key, value in expected_execution.items()):
        raise ProactiveDevelopmentError("forbidden execution authority is present")
    return payload


def validate_preflight(
    instrument: dict[str, Any],
    *,
    output: Path,
    require_clean: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    if instrument["status"] != "frozen-pending-network-free-execution":
        blockers.append("instrument-not-pending")
    if not instrument["execution"].get("network_free_execution_authorized"):
        blockers.append("network-free-execution-not-authorized")
    if require_clean and not _git_is_clean():
        blockers.append("working-tree-dirty")
    if output.exists():
        blockers.append("exclusive-output-already-exists")
    return {
        "run_id": RUN_ID,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "provider_calls": 0,
        "external_deliveries": 0,
        "private_data_reads": 0,
    }


def _record_prior_turn(
    repository: SQLiteStudentRepository,
    fixture,
    case: dict[str, Any],
) -> None:
    current = repository.get_release(fixture.release_a_id)
    if current is None:
        raise ProactiveDevelopmentError("synthetic current release is missing")
    previous_chunks = (
        current.chunks
        if case.get("previous_contains_current_evidence", False)
        else [current.chunks[1]]
    )
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
    conversation = repository.save_conversation(
        Conversation(
            id=f"conversation-{case['id']}",
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            release_id=previous.id,
            created_at="2026-08-10T00:00:00+00:00",
            updated_at="2026-08-10T00:00:01+00:00",
        )
    )
    student_message = Message(
        id=f"student-message-{case['id']}",
        conversation_id=conversation.id,
        role="student",
        content=case["question"],
        action="question",
        client_request_id=f"request-{case['id']}",
        created_at="2026-08-10T00:00:00+00:00",
    )
    tutor_message = Message(
        id=f"tutor-message-{case['id']}",
        conversation_id=conversation.id,
        role="tutor",
        content="I do not have enough approved course evidence.",
        action="no-evidence",
        response_to_message_id=student_message.id,
        created_at="2026-08-10T00:00:01+00:00",
    )
    repository.save_turn(
        conversation,
        student_message,
        tutor_message,
        [],
        [],
    )


def _prepare_case(
    root: Path,
    case: dict[str, Any],
) -> tuple[dict[str, Any], SQLiteStudentRepository, Any]:
    repository = SQLiteStudentRepository(root / f"{case['id']}.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    _record_prior_turn(repository, fixture, case)
    service = ProactiveOutreachService(repository)
    if case.get("consent_enabled", True):
        service.update_preference(
            fixture.student_a_id,
            fixture.course_a_id,
            channel=OutreachChannel.IN_APP,
            enabled=True,
            timezone="UTC",
            quiet_hours_start="23:00",
            quiet_hours_end="06:00",
            max_messages_per_7_days=3,
            snoozed_until=(
                "2026-08-28T12:00:00+00:00" if case.get("snoozed") else None
            ),
        )
    if not case.get("student_active", True):
        account = repository.get_account(fixture.student_a_id)
        repository.save_account(account.model_copy(update={"status": AccountStatus.REVOKED}))
    if not case.get("membership_active", True):
        membership = repository.get_membership(
            fixture.student_a_id, fixture.course_a_id
        )
        repository.save_membership(membership.model_copy(update={"active": False}))
    result = service.scan_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        mode=EvidenceRecoveryMode.SHADOW,
        now=_instant(),
    )
    if len(result.decisions) != 1:
        raise ProactiveDevelopmentError("each frozen case must yield one decision")
    decision = result.decisions[0]
    observed = {
        "case_id": case["id"],
        "expected_action": case["expected_action"],
        "observed_action": decision.action,
        "expected_reason": case["expected_reason"],
        "observed_reason": decision.reason,
        "evidence_score": decision.evidence_score,
        "source_chunk_id": decision.source_chunk_id,
        "action_correct": decision.action == case["expected_action"],
        "reason_correct": decision.reason == case["expected_reason"],
        "shadow_trigger_count": result.trigger_count,
        "provider_calls": result.provider_calls,
    }
    return observed, repository, fixture


def _instant():
    from datetime import datetime

    return datetime.fromisoformat(NOW)


def _active_checks(root: Path, supported_case: dict[str, Any]) -> dict[str, bool]:
    repository = SQLiteStudentRepository(root / "active-check.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    _record_prior_turn(repository, fixture, supported_case)
    shadow = ProactiveOutreachService(repository)
    shadow.update_preference(
        fixture.student_a_id,
        fixture.course_a_id,
        channel=OutreachChannel.IN_APP,
        enabled=True,
        timezone="UTC",
        quiet_hours_start="23:00",
        quiet_hours_end="06:00",
        max_messages_per_7_days=3,
    )
    failed_closed = False
    try:
        shadow.scan_evidence_recovery(
            fixture.professor_id,
            fixture.course_a_id,
            mode=EvidenceRecoveryMode.ACTIVE,
            now=_instant(),
        )
    except ProactiveOutreachError as error:
        failed_closed = error.code == "evidence_recovery_not_authorized"
    active = ProactiveOutreachService(repository, evidence_recovery_active=True)
    first = active.scan_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        mode=EvidenceRecoveryMode.ACTIVE,
        now=_instant(),
    )
    second = active.scan_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        mode=EvidenceRecoveryMode.ACTIVE,
        now=_instant(),
    )
    trigger_id = first.decisions[0].trigger_id
    delivered = active.process_trigger(trigger_id, now=_instant())
    lineage_valid = bool(
        delivered.message
        and delivered.message.citations
        and delivered.message.citations[0].release_id == fixture.release_a_id
        and delivered.message.citations[0].source_document_id == "document-cache"
    )
    return {
        "active-mode-fails-closed": failed_closed,
        "active-idempotency": (
            first.trigger_count == 1
            and second.trigger_count == 0
            and second.duplicate_count == 1
        ),
        "current-release-citation-lineage": lineage_valid,
    }


def _discord_check() -> bool:
    message = ProactiveMessage(
        id="synthetic-private-message",
        trigger_id="synthetic-private-trigger",
        student_id="synthetic-student",
        course_id="synthetic-course",
        release_id="synthetic-release",
        channel=OutreachChannel.DISCORD,
        content="SENSITIVE misconception: cache coherence was misunderstood.",
        status=ProactiveMessageStatus.QUEUED,
    )
    item = DeliveryOutboxItem(
        id="synthetic-delivery",
        message_id=message.id,
        channel=OutreachChannel.DISCORD,
        destination_ref="private-destination",
    )
    route = DiscordWebhookRoute(
        destination_ref="private-destination",
        webhook_url=SecretStr("https://discord.com/api/webhooks/123/secret"),
        private_destination=True,
    )
    prepared = DiscordWebhookDeliveryAdapter(
        enabled=True,
        routes={route.destination_ref: route},
        in_app_base_url="https://tutor.example.edu",
    ).prepare(item, message)
    content = str(prepared.payload.get("content", ""))
    return (
        message.content not in content
        and "misconception" not in content.casefold()
        and "https://tutor.example.edu/student?" in content
        and prepared.payload.get("allowed_mentions") == {"parse": []}
    )


def execute(instrument: dict[str, Any], *, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="proactive-a1-") as temporary:
        root = Path(temporary)
        case_results = []
        for case in instrument["p1_shadow_cases"]:
            observed, repository, _ = _prepare_case(root, case)
            observed["persisted_trigger_count"] = len(
                repository.list_due_proactive_triggers(NOW)
            )
            case_results.append(observed)

        by_id = {item["case_id"]: item for item in case_results}
        p0 = {
            "shadow-zero-side-effects": all(
                item["shadow_trigger_count"] == 0
                and item["persisted_trigger_count"] == 0
                for item in case_results
            ),
            "zero-provider-usage": all(
                item["provider_calls"] == 0 for item in case_results
            ),
            **_active_checks(root, instrument["p1_shadow_cases"][0]),
            "consent-enforcement": by_id["consent-01"]["reason_correct"],
            "snooze-enforcement": by_id["snooze-01"]["reason_correct"],
            "inactive-account-enforcement": by_id["account-01"]["reason_correct"],
            "inactive-membership-enforcement": by_id["membership-01"]["reason_correct"],
            "unchanged-evidence-no-action": by_id["unchanged-01"]["reason_correct"],
            "unsupported-question-no-action": all(
                item["observed_action"] == "no-action"
                for item in case_results
                if item["case_id"].startswith(("unsupported-", "symbols-", "same-topic-"))
            ),
            "discord-generic-deep-link-only": _discord_check(),
        }
        expected_checks = set(instrument["p0_mechanism_checks"])
        if set(p0) != expected_checks:
            raise ProactiveDevelopmentError("P0 check implementation drifted")
        action_accuracy = sum(item["action_correct"] for item in case_results) / len(
            case_results
        )
        reason_accuracy = sum(item["reason_correct"] for item in case_results) / len(
            case_results
        )
        proposed = [item for item in case_results if item["observed_action"] == "propose"]
        lineage_validity = (
            sum(item["source_chunk_id"] == "chunk-cache-synthetic" for item in proposed)
            / len(proposed)
            if proposed
            else 0.0
        )
        gates = {
            "p0_mechanism_pass_rate": sum(p0.values()) / len(p0),
            "p1_action_accuracy": action_accuracy,
            "p1_reason_accuracy": reason_accuracy,
            "supported_source_lineage_validity": lineage_validity,
            "shadow_side_effect_count": sum(
                item["persisted_trigger_count"] for item in case_results
            ),
            "provider_calls": 0,
            "external_deliveries": 0,
            "private_data_reads": 0,
        }
        expected = instrument["hard_gates"]
        passed = all(gates[key] == value for key, value in expected.items())
        result = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "status": "completed-go-deeper" if passed else "completed-refine",
            "code_revision": _git_revision(),
            "instrument_sha256": _sha256(INSTRUMENT_PATH),
            "p0_checks": [
                {"id": key, "passed": value} for key, value in sorted(p0.items())
            ],
            "p1_case_results": case_results,
            "metrics": gates,
            "provider_calls": 0,
            "tokens": 0,
            "cost_usd": 0.0,
            "external_deliveries": 0,
            "private_data_reads": 0,
            "selected_for_release": False,
            "decision": "go-deeper" if passed else "refine",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if sum((args.validate, args.preflight, args.execute)) != 1:
        raise SystemExit("select exactly one of --validate, --preflight, or --execute")
    instrument = load_instrument()
    if args.validate:
        print(
            json.dumps(
                {
                    "instrument_id": RUN_ID,
                    "status": "passed",
                    "p0_check_count": len(instrument["p0_mechanism_checks"]),
                    "p1_case_count": len(instrument["p1_shadow_cases"]),
                    "provider_calls": 0,
                },
                indent=2,
            )
        )
        return
    preflight = validate_preflight(
        instrument,
        output=args.output,
        require_clean=not args.allow_dirty,
    )
    if args.preflight or preflight["status"] != "ready":
        print(json.dumps(preflight, indent=2))
        if args.execute and preflight["status"] != "ready":
            raise SystemExit(2)
        return
    require_bounded_pilot_operation_allowed(RUN_ID)
    print(json.dumps(execute(instrument, output=args.output), indent=2))


if __name__ == "__main__":
    main()
