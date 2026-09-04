"""Run the frozen network-free mixed-initiative clarification confirmation."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.grounding.evidence_sufficiency import EvidenceSufficiencyDecision
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.student import (
    Account,
    AccountRole,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    MembershipRole,
    ReleaseEvaluationStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    approved_synthetic_policy,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/stateful_clarification_confirmation_001.json"
)
PROFILE = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/stateful-clarification-confirmation-001/result.json"
)


class ConfirmationMetricsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_count: int = Field(ge=1)
    answerable_case_count: int = Field(ge=1)
    candidate_grounded_completion: float = Field(ge=0, le=1)
    control_grounded_completion: float = Field(ge=0, le=1)
    paired_completion_delta: float = Field(ge=-1, le=1)
    unambiguous_control_success: float = Field(ge=0, le=1)
    clarification_resolution_accuracy: float = Field(ge=0, le=1)
    boundary_safety: float = Field(ge=0, le=1)
    invalid_reply_safety: float = Field(ge=0, le=1)
    source_version_validity: float = Field(ge=0, le=1)
    restart_consistency: float = Field(ge=0, le=1)
    idempotency_consistency: float = Field(ge=0, le=1)
    unsupported_or_wrong_scope_releases: int = Field(ge=0)
    duplicate_deliveries: int = Field(ge=0)
    clarification_turn_ceiling_violations: int = Field(ge=0)
    provider_calls: int = Field(ge=0)


class ConfirmationResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_id: str
    status: str
    decision: str
    code_revision: str
    dirty: bool
    instrument_sha256: str
    metrics: ConfirmationMetricsV1
    failed_gates: list[str]
    limitations: list[str]


class ScenarioRetriever:
    implementation_id = "stateful-clarification-scenario-retriever-v1"

    def __init__(
        self,
        chunks: Sequence[DocumentChunk],
        mapping: dict[str, list[str]],
    ) -> None:
        self._chunks = {chunk.id: chunk for chunk in chunks}
        self._mapping = mapping

    def retrieve(self, query: str, limit: int = 5) -> list[RetrievalHit]:
        return [
            RetrievalHit(chunk=self._chunks[identifier], relevance_score=1 - rank * 0.1)
            for rank, identifier in enumerate(self._mapping.get(query, [])[:limit])
        ]


class ScenarioEvidenceGate:
    implementation_id = "stateful-clarification-scenario-gate-v1"

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        if query.startswith("ambiguous-"):
            return EvidenceSufficiencyDecision(
                sufficient=False,
                score=0,
                reason="two supported interpretations remain tied",
                clarification_candidate_hit_ids=[hit.chunk.id for hit in hits],
                recommended_action="clarify",
            )
        if query.startswith("boundary-"):
            return EvidenceSufficiencyDecision(
                sufficient=False,
                score=0,
                reason="no approved source supports the request",
                recommended_action="abstain",
            )
        return EvidenceSufficiencyDecision(
            sufficient=True,
            score=1,
            reason="one current approved source supports the request",
            selected_hit_ids=[hit.chunk.id for hit in hits[:1]],
        )


def validate_instrument() -> dict:
    payload = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    if payload["evaluation_id"] != "stateful-clarification-confirmation-001":
        raise ValueError("unexpected clarification evaluation identity")
    if (
        sum(
            payload["dataset"][key]
            for key in (
                "resolvable_ambiguity",
                "unambiguous_answerable",
                "no_evidence_boundary",
                "invalid_clarification_reply",
            )
        )
        != payload["dataset"]["case_count"]
    ):
        raise ValueError("clarification evaluation allocation does not sum")
    if payload["execution"]["provider_calls"] != 0:
        raise ValueError("clarification confirmation must remain network-free")
    return payload


async def run_confirmation(database_path: Path) -> ConfirmationResultV1:
    instrument = validate_instrument()
    repository, service, student_id, mapping = _build_product(database_path)
    resolved_success = 0
    direct_success = 0
    boundary_success = 0
    invalid_reply_success = 0
    source_version_success = 0
    restart_checks = 0
    restart_success = 0
    idempotency_checks = 0
    idempotency_success = 0
    unsafe = 0
    duplicate_deliveries = 0
    clarification_turn_ceiling_violations = 0

    for index in range(1, 121):
        question = f"ambiguous-{index:03d}: What does the mechanism do?"
        conversation = service.create_conversation(student_id, "clarification-course")
        first = await service.submit_message(
            student_id,
            conversation.id,
            content=question,
            client_request_id=f"request-{index:03d}-a",
        )
        request = first.pending_clarification
        if request is None or first.tutor_message.action != "clarify-request":
            unsafe += 1
            continue
        expected_option = request.options[(index + 1) % 2]
        reply = (
            str((index + 1) % 2 + 1)
            if index % 3 == 0
            else expected_option.option_id
            if index % 3 == 1
            else expected_option.label
        )
        if index % 10 == 0:
            restart_checks += 1
            service = _restart_service(repository, mapping)
            if service.get_conversation(
                student_id, conversation.id
            ).pending_clarification:
                restart_success += 1
        second = await service.submit_message(
            student_id,
            conversation.id,
            content=reply,
            client_request_id=f"request-{index:03d}-b",
        )
        citation_ok = (
            second.tutor_message.action == "answer"
            and len(second.citations) == 1
            and second.citations[0].source_artifact_id
            == expected_option.source_artifact_id
        )
        if citation_ok:
            resolved_success += 1
            source_version_success += int(
                second.citations[0].source_version == expected_option.source_version
            )
        else:
            unsafe += int(second.tutor_message.action == "answer")
        if index % 11 == 0:
            idempotency_checks += 1
            before = len(repository.list_messages(conversation.id))
            duplicate = await service.submit_message(
                student_id,
                conversation.id,
                content=reply,
                client_request_id=f"request-{index:03d}-b",
            )
            after = len(repository.list_messages(conversation.id))
            if duplicate.duplicate and before == after:
                idempotency_success += 1
            else:
                duplicate_deliveries += 1

    for index in range(121, 161):
        question = f"direct-{index:03d}: What does the mechanism do?"
        conversation = service.create_conversation(student_id, "clarification-course")
        turn = await service.submit_message(
            student_id,
            conversation.id,
            content=question,
            client_request_id=f"request-{index:03d}",
        )
        expected = mapping[question][0]
        if (
            turn.tutor_message.action == "answer"
            and len(turn.citations) == 1
            and turn.citations[0].source_artifact_id == f"source-{expected}"
        ):
            direct_success += 1
            source_version_success += int(turn.citations[0].source_version == 1)
        else:
            unsafe += int(turn.tutor_message.action == "answer")

    for index in range(161, 181):
        question = f"boundary-{index:03d}: Answer from another course."
        conversation = service.create_conversation(student_id, "clarification-course")
        turn = await service.submit_message(
            student_id,
            conversation.id,
            content=question,
            client_request_id=f"request-{index:03d}",
        )
        if turn.tutor_message.action == "no-evidence" and not turn.citations:
            boundary_success += 1
        else:
            unsafe += int(turn.tutor_message.action == "answer")

    for index in range(181, 201):
        question = f"ambiguous-{index:03d}: What does the mechanism do?"
        conversation = service.create_conversation(student_id, "clarification-course")
        first = await service.submit_message(
            student_id,
            conversation.id,
            content=question,
            client_request_id=f"request-{index:03d}-a",
        )
        second = await service.submit_message(
            student_id,
            conversation.id,
            content="both or neither",
            client_request_id=f"request-{index:03d}-b",
        )
        if (
            first.pending_clarification is not None
            and second.tutor_message.action == "clarify-request"
            and second.pending_clarification == first.pending_clarification
            and not second.citations
        ):
            invalid_reply_success += 1
        else:
            unsafe += int(second.tutor_message.action == "answer")
        clarification_turn_ceiling_violations += int(
            len(repository.list_messages(conversation.id)) != 4
        )

    answerable = 160
    candidate_completed = resolved_success + direct_success
    control_completed = direct_success
    metrics = ConfirmationMetricsV1(
        case_count=200,
        answerable_case_count=answerable,
        candidate_grounded_completion=candidate_completed / answerable,
        control_grounded_completion=control_completed / answerable,
        paired_completion_delta=(candidate_completed - control_completed) / answerable,
        unambiguous_control_success=direct_success / 40,
        clarification_resolution_accuracy=resolved_success / 120,
        boundary_safety=boundary_success / 20,
        invalid_reply_safety=invalid_reply_success / 20,
        source_version_validity=source_version_success / answerable,
        restart_consistency=restart_success / restart_checks,
        idempotency_consistency=idempotency_success / idempotency_checks,
        unsupported_or_wrong_scope_releases=unsafe,
        duplicate_deliveries=duplicate_deliveries,
        clarification_turn_ceiling_violations=clarification_turn_ceiling_violations,
        provider_calls=0,
    )
    failed = _failed_gates(metrics)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    import hashlib

    result = ConfirmationResultV1(
        evaluation_id=instrument["evaluation_id"],
        status="completed-keep" if not failed else "completed-refine",
        decision="Keep" if not failed else "Refine",
        code_revision=revision,
        dirty=dirty,
        instrument_sha256=hashlib.sha256(INSTRUMENT.read_bytes()).hexdigest(),
        metrics=metrics,
        failed_gates=failed,
        limitations=[
            "Public-synthetic source pairs test mechanism correctness, not real-student usability.",
            "Student clarification replies are scripted and do not estimate natural-language response rates.",
            "The immutable known 10,000+1,000 benchmark was not read, rerun, or rescored.",
        ],
    )
    repository.close()
    return result


def _failed_gates(metrics: ConfirmationMetricsV1) -> list[str]:
    gates = {
        "candidate_grounded_completion": metrics.candidate_grounded_completion >= 0.95,
        "unambiguous_control_regression": metrics.unambiguous_control_success == 1,
        "clarification_resolution_accuracy": metrics.clarification_resolution_accuracy
        >= 0.95,
        "boundary_safety": metrics.boundary_safety == 1,
        "invalid_reply_safety": metrics.invalid_reply_safety == 1,
        "citation_source_version_validity": metrics.source_version_validity == 1,
        "restart_consistency": metrics.restart_consistency == 1,
        "idempotency_consistency": metrics.idempotency_consistency == 1,
        "unsupported_or_wrong_scope_releases": metrics.unsupported_or_wrong_scope_releases
        == 0,
        "duplicate_deliveries": metrics.duplicate_deliveries == 0,
        "unbounded_loops": metrics.clarification_turn_ceiling_violations == 0,
        "provider_calls": metrics.provider_calls == 0,
    }
    return [name for name, passed in gates.items() if not passed]


def _build_product(database_path: Path):
    repository = SQLiteStudentRepository(database_path)
    student_id = "clarification-student"
    professor_id = "clarification-professor"
    course_id = "clarification-course"
    repository.save_account(Account(id=professor_id, role=AccountRole.PROFESSOR))
    repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
    repository.save_course(
        Course(
            id=course_id,
            title="Clarification mechanics",
            owner_professor_id=professor_id,
        )
    )
    for account_id, role in (
        (professor_id, MembershipRole.PROFESSOR),
        (student_id, MembershipRole.STUDENT),
    ):
        repository.save_membership(
            CourseMembership(account_id=account_id, course_id=course_id, role=role)
        )
    chunks: list[DocumentChunk] = []
    mapping: dict[str, list[str]] = {}
    for index in range(1, 201):
        identifiers: list[str] = []
        count = 2 if index <= 120 or index >= 181 else 1
        for variant in range(1, count + 1):
            identifier = f"case-{index:03d}-variant-{variant}"
            identifiers.append(identifier)
            chunks.append(
                DocumentChunk(
                    id=identifier,
                    document_id=f"document-{identifier}",
                    text=(
                        f"In scenario {index:03d}, interpretation {variant} uses "
                        f"the approved mechanism variant {variant}."
                    ),
                    ordinal=0,
                    source_artifact_id=f"source-{identifier}",
                    source_version=1,
                    source_checksum=(f"{index:04x}{variant:x}" * 13)[:64].ljust(
                        64, "0"
                    ),
                    source_label=SourceLabel.COURSE_APPROVED,
                    locator=f"scenario {index:03d}, interpretation {variant}",
                    region_id=f"region-{identifier}",
                    retrieval_allowed=True,
                    display_allowed=True,
                    metadata={
                        "title": f"Scenario {index:03d} interpretation {variant}",
                        "semantic_atom_claim": (
                            f"scenario {index:03d} interpretation {variant} approved mechanism"
                        ),
                    },
                )
            )
        if index <= 120 or index >= 181:
            question = f"ambiguous-{index:03d}: What does the mechanism do?"
        elif index <= 160:
            question = f"direct-{index:03d}: What does the mechanism do?"
        else:
            question = f"boundary-{index:03d}: Answer from another course."
            identifiers = []
        mapping[question] = identifiers
    release = DigitalTwinRelease(
        id="clarification-release-v1",
        course_id=course_id,
        profile_id="student-tutor",
        profile_version="v1",
        policy_version=1,
        policy=approved_synthetic_policy(),
        chunks=chunks,
        status=StudentReleaseStatus.PUBLISHED,
        evaluation_status=ReleaseEvaluationStatus.PASSED,
    )
    repository.save_release(release)
    service = _restart_service(repository, mapping)
    return repository, service, student_id, mapping


def _restart_service(repository, mapping):
    return StudentTutoringService(
        repository,
        profile_path=PROFILE,
        evidence_gate=ScenarioEvidenceGate(),
        retriever_factory=lambda chunks, versions: ScenarioRetriever(chunks, mapping),
    )


def _write_exclusive(path: Path, result: ConfirmationResultV1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(result.model_dump(mode="json"), handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.validate:
        print(json.dumps({"status": "passed", "instrument": validate_instrument()}))
        return 0
    with tempfile.TemporaryDirectory(prefix="clarification-confirmation-") as directory:
        result = asyncio.run(run_confirmation(Path(directory) / "product.sqlite3"))
    if args.execute:
        _write_exclusive(args.output, result)
    print(result.model_dump_json(indent=2))
    return 0 if result.status == "completed-keep" else 2


if __name__ == "__main__":
    raise SystemExit(main())
