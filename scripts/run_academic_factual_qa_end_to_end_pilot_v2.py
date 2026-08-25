#!/usr/bin/env python3
"""Run the paired, network-free academic factual-QA development comparison."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

from scripts.academic_factual_qa_pilot_data import (
    COURSES,
    DATASET_ID,
    build_development_dataset,
)
from scripts.run_academic_factual_qa_end_to_end_pilot import (
    AcademicPilotError,
    PROFILE_PATH,
    _product_input,
    _score_case,
    _source_chunk,
    _summarize,
)
from src.digital_twin.generation import (
    DeterministicGroundedGenerator,
    authoritative_citation_for_chunk,
)
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    AtomicAnswerClaim,
    AtomicClaimEvidenceValidator,
    EvidenceSufficiencyDecision,
    ExactQuoteAtomicClaimVerifier,
    RetrievalHit,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.grounding.models import GenerationTrace, GenerationUsage, TutorAnswer
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)
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


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-end-to-end-pilot-002"
DEFAULT_INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_end_to_end_pilot_002.json"
)


class RecordingEvidenceGate:
    def __init__(self, gate) -> None:
        self.gate = gate
        self.implementation_id = gate.implementation_id
        self.selected_hits_by_question: dict[str, list[RetrievalHit]] = {}

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        decision = self.gate.assess(query, hits)
        by_id = {hit.chunk.id: hit for hit in hits}
        selected_ids = decision.selected_hit_ids or (
            list(by_id) if decision.sufficient else []
        )
        self.selected_hits_by_question[query] = [by_id[hit_id] for hit_id in selected_ids]
        return decision


class DevelopmentAtomicDraftGenerator:
    """Deterministic draft fixture shared by every development condition."""

    implementation_id = "development-atomic-draft-generator-v1"
    version = "1.0.0"

    def __init__(self) -> None:
        self.base = DeterministicGroundedGenerator()
        self.draft_hashes: dict[str, str] = {}

    async def generate(self, question, hits, policy):
        normalized = " ".join(question.casefold().split())
        if "how does it work" in normalized or "earlier rule" in normalized:
            answer = TutorAnswer(
                content="Which specific concept or earlier rule would you like explained?",
                warnings=["The question contains an unresolved reference."],
                trace=GenerationTrace(
                    generator_id=self.implementation_id,
                    provider_model="not-called",
                    prompt_version="development-boundary-router-v1",
                    policy_action="clarify-request",
                    latency_ms=0,
                    usage=GenerationUsage(),
                ),
            )
        else:
            answer = await self.base.generate(question, hits, policy)
        if answer.trace is not None and answer.trace.policy_action == "answer":
            approved = [hit for hit in hits if hit.chunk.retrieval_allowed]
            answer = answer.model_copy(
                update={
                    "content": " ".join(hit.chunk.text for hit in approved),
                    "citations": [
                        authoritative_citation_for_chunk(hit.chunk) for hit in approved
                    ],
                    "atomic_claims": [
                        AtomicAnswerClaim(
                            claim_id=f"claim-{index}",
                            text=hit.chunk.text,
                            evidence_hit_ids=[hit.chunk.id],
                        )
                        for index, hit in enumerate(approved, start=1)
                    ],
                }
            )
        payload = answer.model_dump(mode="json", exclude={"trace": {"latency_ms"}})
        self.draft_hashes[question] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return answer


def validate_instrument(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    dataset = build_development_dataset()
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise AcademicPilotError("instrument ID drifted")
    if instrument.get("status") != "frozen-development-authorized":
        raise AcademicPilotError("development authorization drifted")
    if instrument.get("dataset", {}).get("dataset_id") != DATASET_ID:
        raise AcademicPilotError("dataset ID drifted")
    if instrument["dataset"].get("content_sha256") != dataset["content_sha256"]:
        raise AcademicPilotError("dataset hash drifted")
    if [row.get("condition_id") for row in instrument.get("conditions", [])] != [
        "T0-ANY-HIT-V2-CONTROL",
        "T0-STRUCTURED-COVERAGE-ABLATION",
        "T0-TWO-BOUNDARY-ATOMIC-CANDIDATE",
    ]:
        raise AcademicPilotError("condition contract drifted")
    safety = instrument.get("execution_safety", {})
    if safety.get("network_free_development_execution_authorized") is not True:
        raise AcademicPilotError("network-free development run is not authorized")
    if any(
        safety.get(key) is not False
        for key in (
            "provider_execution_authorized",
            "paid_execution_authorized",
            "private_source_execution_authorized",
            "independent_gold_opening_authorized",
            "heldout_execution_authorized",
            "product_binding_authorized",
            "automatic_selection",
            "automatic_release_promotion",
        )
    ):
        raise AcademicPilotError("external or promotion authority drifted")
    return instrument


def preflight(instrument: dict[str, Any]) -> dict[str, Any]:
    del instrument
    revision, dirty = _repository_state()
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "blocked-dirty-worktree" if dirty else "ready-network-free-development",
        "code_revision": revision,
        "dirty_state": dirty,
        "provider_calls": 0,
        "private_data_read": False,
        "independent_gold_opened": False,
        "heldout_opened": False,
    }


async def execute_development(
    instrument: dict[str, Any],
    *,
    require_clean: bool = False,
) -> dict[str, Any]:
    revision, dirty = _repository_state()
    if require_clean and dirty:
        raise AcademicPilotError("development execution requires a clean worktree")
    dataset = build_development_dataset()
    runs: dict[str, dict[str, Any]] = {}
    for condition in instrument["conditions"]:
        runs[condition["condition_id"]] = await _run_condition(dataset, condition)

    ablation = runs["T0-STRUCTURED-COVERAGE-ABLATION"]
    candidate = runs["T0-TWO-BOUNDARY-ATOMIC-CANDIDATE"]
    paired_questions = sorted(
        set(ablation["draft_hashes"]) & set(candidate["draft_hashes"])
    )
    draft_mismatches = [
        question
        for question in paired_questions
        if ablation["draft_hashes"][question] != candidate["draft_hashes"][question]
    ]
    summaries = [runs[row["condition_id"]]["summary"] for row in instrument["conditions"]]
    candidate_summary = candidate["summary"]
    gates = instrument["prospective_development_gates"]
    gate_results = {
        "unsupported_release_rate": candidate_summary["unsupported_release_rate"]["estimate"]
        <= gates["unsupported_release_rate_max"],
        "supported_answer_retention": candidate_summary["supported_answer_retention"]["estimate"]
        >= gates["supported_answer_retention_min"],
        "expected_claim_complete_rate": candidate_summary["expected_claim_complete_rate"]["estimate"]
        >= gates["expected_claim_complete_rate_min"],
        "citation_precision": candidate_summary["citation_precision"]
        >= gates["citation_precision_min"],
        "citation_recall": candidate_summary["citation_recall"]
        >= gates["citation_recall_min"],
        "persistence_consistency": candidate_summary["persistence_consistency_rate"]
        >= gates["persistence_consistency_min"],
        "paired_draft_identity": len(draft_mismatches)
        <= gates["paired_draft_mismatch_count_max"],
        "zero_provider_calls": sum(row["provider_calls"] for row in summaries)
        <= gates["provider_calls_max"],
    }
    status = "completed-go-deeper" if all(gate_results.values()) else "completed-refine"
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "code_revision": revision,
        "dirty_state": dirty,
        "dataset_id": DATASET_ID,
        "dataset_content_sha256": dataset["content_sha256"],
        "condition_summaries": summaries,
        "case_results": [
            row
            for condition in instrument["conditions"]
            for row in runs[condition["condition_id"]]["cases"]
        ],
        "paired_draft_comparison": {
            "paired_question_count": len(paired_questions),
            "mismatch_count": len(draft_mismatches),
        },
        "development_gate_results": gate_results,
        "provider_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "paid_cost_usd": 0,
        "private_data_read": False,
        "independent_gold_opened": False,
        "heldout_opened": False,
        "method_selected": False,
        "product_promoted": False,
        "next_state": "freeze-successor-and-prepare-fresh-independent-confirmation",
    }


def _repository_state() -> tuple[str, bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return revision, bool(status)


async def _run_condition(
    dataset: dict[str, Any],
    condition: dict[str, Any],
) -> dict[str, Any]:
    base_gate = (
        AnyHitEvidenceGate()
        if condition["evidence_gate"] == AnyHitEvidenceGate.implementation_id
        else StructuredLexicalCoverageEvidenceGate()
    )
    gate = RecordingEvidenceGate(base_gate)
    validator = (
        AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1,
            maximum_contradiction=0,
        )
        if condition["post_generation_claim_validator"]
        else None
    )
    generator = DevelopmentAtomicDraftGenerator()
    with tempfile.TemporaryDirectory(prefix="academic-factual-qa-v2-") as temp_root:
        repository = SQLiteStudentRepository(Path(temp_root) / "pilot.sqlite3")
        professor_id = "afe2e-professor"
        student_id = "afe2e-student"
        repository.save_account(Account(id=professor_id, role=AccountRole.PROFESSOR))
        repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
        source_map = {source["source_id"]: source for source in dataset["sources"]}
        conversations: dict[str, str] = {}
        for course in COURSES:
            course_id = course["course_id"]
            repository.save_course(
                Course(id=course_id, title=course["title"], owner_professor_id=professor_id)
            )
            for account_id, role in (
                (professor_id, MembershipRole.PROFESSOR),
                (student_id, MembershipRole.STUDENT),
            ):
                repository.save_membership(
                    CourseMembership(account_id=account_id, course_id=course_id, role=role)
                )
            chunks = []
            for source in dataset["sources"]:
                if source["course_id"] != course_id:
                    continue
                chunk = _source_chunk(source)
                chunk.metadata["search_description"] = source["topic"]
                chunks.append(chunk)
            release_id = f"{course_id}-release-v2"
            repository.save_release(
                DigitalTwinRelease(
                    id=release_id,
                    course_id=course_id,
                    profile_id="student-tutor",
                    profile_version="v1",
                    policy_version=1,
                    policy=approved_synthetic_policy(),
                    chunks=chunks,
                    status=StudentReleaseStatus.PUBLISHED,
                    evaluation_status=ReleaseEvaluationStatus.PASSED,
                )
            )
        service = StudentTutoringService(
            repository,
            profile_path=PROFILE_PATH,
            generator=generator,
            evidence_gate=gate,
            claim_evidence_validator=validator,
            tutoring_mode="grounded-assistant",
        )
        for course in COURSES:
            conversations[course["course_id"]] = service.create_conversation(
                student_id, course["course_id"]
            ).id
        rows = []
        try:
            for case in dataset["cases"]:
                product_input = _product_input(case, condition["condition_id"])
                started = time.perf_counter()
                turn = await service.submit_message(
                    student_id,
                    conversations[product_input.course_id],
                    content=product_input.question,
                    client_request_id=product_input.client_request_id,
                )
                latency_ms = (time.perf_counter() - started) * 1000
                persisted = service.get_conversation(
                    student_id, conversations[product_input.course_id]
                )
                rows.append(
                    _score_case(
                        case,
                        turn,
                        gate.selected_hits_by_question.get(product_input.question, []),
                        persisted.messages[-1].action == turn.tutor_message.action,
                        latency_ms,
                        source_map,
                        condition["condition_id"],
                    )
                )
        finally:
            repository.close()
    summary = _summarize(condition, rows)
    summary["role"] = condition["role"]
    summary["selectable"] = False
    summary["method_selected"] = False
    return {"summary": summary, "cases": rows, "draft_hashes": generator.draft_hashes}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute-development", action="store_true")
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    instrument = validate_instrument(arguments.instrument)
    if arguments.execute_development:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
        result = asyncio.run(execute_development(instrument, require_clean=True))
    elif arguments.preflight:
        result = preflight(instrument)
    else:
        result = {"instrument_id": INSTRUMENT_ID, "status": "validated"}
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if arguments.output is None:
        if "case_results" in result:
            result = {key: value for key, value in result.items() if key != "case_results"}
            rendered = json.dumps(result, indent=2, sort_keys=True)
        print(rendered)
    else:
        if arguments.output.exists():
            raise AcademicPilotError("exclusive output path already exists")
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
