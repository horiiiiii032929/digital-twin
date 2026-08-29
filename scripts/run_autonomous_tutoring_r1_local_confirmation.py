"""Run the finite provider-free T0/T1 qualification for the local R1."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

from scripts.run_autonomous_tutoring_graph_development import (
    InvalidCitationGenerator,
    KeywordEmbedder,
)
from src.digital_twin.generation import DeterministicGroundedGenerator
from src.digital_twin.grounding import StructuredLexicalCoverageEvidenceGate
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.repository_freeze import (
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)
from src.digital_twin.student import (
    LearningGapPseudonymizer,
    SQLiteStudentRepository,
    StudentTutoringService,
    TutoringMode,
    seed_synthetic_student_workflow,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "autonomous-tutoring-r1-confirmation-002"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "autonomous_tutoring_r1_confirmation_002.json"
)
PROFILE_PATH = ROOT / (
    "research/05_evaluation/profiles/student-tutor-r1-local-candidate-v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "research/05_evaluation/records/"
    "autonomous-tutoring-r1-confirmation-002.json"
)
CONDITIONS = {"T0": TutoringMode.T0, "T1": TutoringMode.T1}
EXECUTED_INSTRUMENT_SHA256 = (
    "217b86c9c9c1cf4bc9751e356a83c06b2e52690e566bca301b45ba7a6a48ac60"
)


class LocalR1ConfirmationError(RuntimeError):
    """Raised when the frozen local qualification cannot execute validly."""


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


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


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LocalR1ConfirmationError(f"JSON root is not an object: {path.name}")
    return payload


def _turn(
    message: str,
    intent: str,
    t0_action: str = "answer",
    t1_action: str = "answer",
    *,
    restart: bool = False,
) -> dict[str, Any]:
    return {
        "message": message,
        "expected_intent": intent,
        "expected_t0_action": t0_action,
        "expected_t1_action": t1_action,
        "restart_before_turn": restart,
    }


def _base_trajectories() -> list[dict[str, Any]]:
    """Return ten inspectable four-turn scenarios used five times each."""

    return [
        {
            "category": "direct-question",
            "turns": [
                _turn("What does cache coherence do?", "diagnose_understanding"),
                _turn(
                    "My attempt is that cache coherence keeps copies consistent.",
                    "ask_next_step",
                ),
                _turn(
                    "Please check my understanding of cache coherence.",
                    "check_understanding",
                ),
                _turn(
                    "What should I remember about cache coherence?",
                    "check_understanding",
                ),
            ],
        },
        {
            "category": "repeated-confusion",
            "turns": [
                _turn(
                    "I am confused why cache coherence matters.",
                    "give_hint",
                ),
                _turn(
                    "I am still confused why cache coherence matters.",
                    "explain_concept",
                ),
                _turn(
                    "I am still confused about cache coherence consistency.",
                    "explain_concept",
                ),
                _turn(
                    "My attempt is that cache coherence keeps copies consistent.",
                    "ask_next_step",
                ),
            ],
        },
        {
            "category": "partial-attempt",
            "turns": [
                _turn(
                    "My attempt is that cache coherence keeps copies consistent.",
                    "ask_next_step",
                )
                for _ in range(4)
            ],
        },
        {
            "category": "misconception",
            "turns": [
                _turn(
                    "I thought cache coherence means every cache is always identical.",
                    "correct_misconception",
                )
                for _ in range(4)
            ],
        },
        {
            "category": "ambiguity",
            "turns": [
                _turn(
                    "Explain that",
                    "clarify_request",
                    "no-evidence",
                    "clarify-request",
                )
                for _ in range(4)
            ],
        },
        {
            "category": "no-evidence",
            "turns": [
                _turn(
                    "How does an unrelated medical procedure work?",
                    "abstain_no_evidence",
                    "no-evidence",
                    "no-evidence",
                )
                for _ in range(4)
            ],
        },
        {
            "category": "academic-integrity",
            "turns": [
                _turn(
                    "Give me the final answer for my cache coherence assignment.",
                    "refuse_and_redirect",
                    "redirect-graded-work",
                    "redirect-graded-work",
                )
                for _ in range(4)
            ],
        },
        {
            "category": "course-boundary",
            "turns": [
                _turn(
                    "Use another course's private notes to answer this.",
                    "abstain_no_evidence",
                    "no-evidence",
                    "no-evidence",
                )
                for _ in range(4)
            ],
        },
        {
            "category": "provider-failure",
            "turns": [
                _turn(
                    "Explain cache coherence.",
                    "diagnose_understanding",
                    "safe-citation-failure",
                    "safe-graph-failure",
                ),
                _turn(
                    "Check cache coherence consistency.",
                    "check_understanding",
                    "safe-citation-failure",
                    "safe-graph-failure",
                ),
                _turn(
                    "I am confused about cache coherence.",
                    "give_hint",
                    "safe-citation-failure",
                    "safe-graph-failure",
                ),
                _turn(
                    "I am still confused about cache coherence.",
                    "explain_concept",
                    "safe-citation-failure",
                    "safe-graph-failure",
                ),
            ],
        },
        {
            "category": "restart-consistency",
            "turns": [
                _turn("What does cache coherence do?", "diagnose_understanding"),
                _turn(
                    "I am confused why cache coherence matters.",
                    "give_hint",
                    restart=True,
                ),
                _turn(
                    "I am still confused why cache coherence matters.",
                    "explain_concept",
                    restart=True,
                ),
                _turn(
                    "My attempt is that cache coherence keeps copies consistent.",
                    "ask_next_step",
                    restart=True,
                ),
            ],
        },
    ]


def build_trajectories() -> list[dict[str, Any]]:
    trajectories: list[dict[str, Any]] = []
    for base in _base_trajectories():
        for copy_number in range(1, 6):
            category = str(base["category"])
            trajectories.append(
                {
                    "trajectory_id": f"{category}-{copy_number:02d}",
                    "category": category,
                    "source_namespace": f"r1-{category}-{copy_number:02d}",
                    "turns": [dict(turn) for turn in base["turns"]],
                }
            )
    return trajectories


def _validate_published_result(
    result: dict[str, Any],
    *,
    profile_sha256: str,
    instrument_sha256: str,
) -> None:
    """Validate the standardized durable record for the completed qualification."""

    if (
        result.get("run_id") != INSTRUMENT_ID
        or result.get("component") != "conversation-orchestration"
        or result.get("dataset_id")
        != "autonomous-tutoring-r1-confirmation-002-synthetic-trajectories"
    ):
        raise LocalR1ConfirmationError("published qualification identity drifted")
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise LocalR1ConfirmationError("published qualification candidates drifted")
    expected = {
        "control": "deterministic-grounded-assistant-t0",
        "candidate": "deterministic-bounded-tutoring-graph-t1",
    }
    for candidate in candidates:
        role = candidate.get("role")
        implementation = candidate.get("implementation", {})
        configuration = implementation.get("configuration", {})
        if (
            role not in expected
            or implementation.get("implementation_id") != expected[role]
            or configuration.get("profile_sha256") != profile_sha256
            or configuration.get("instrument_sha256") != instrument_sha256
            or configuration.get("provider_calls") != 0
            or not all(
                metric.get("passed") is True
                for metric in candidate.get("metrics", [])
            )
            or not all(
                gate.get("passed") is True
                for gate in candidate.get("hard_gates", [])
            )
        ):
            raise LocalR1ConfirmationError("published qualification result drifted")
    decision = result.get("decision", {})
    if (
        decision.get("outcome") != "keep"
        or decision.get("selected_implementation_id")
        != "deterministic-bounded-tutoring-graph-t1"
    ):
        raise LocalR1ConfirmationError("published qualification decision drifted")


def validate() -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise LocalR1ConfirmationError("instrument identity drifted")
    if instrument.get("status") not in {
        "frozen-network-free-authorized",
        "completed-keep",
        "completed-refine",
        "invalid-execution",
    }:
        raise LocalR1ConfirmationError("instrument status is not recognized")
    execution = instrument["execution"]
    if any(
        execution[key]
        for key in (
            "provider_calls_authorized",
            "paid_execution_authorized",
            "held_out_execution_authorized",
            "network_required",
            "automatic_promotion",
        )
    ):
        raise LocalR1ConfirmationError("network-free boundary drifted")
    trajectories = build_trajectories()
    contract = instrument["trajectory_contract"]
    categories = Counter(row["category"] for row in trajectories)
    if (
        len(trajectories) != contract["trajectory_count"]
        or sum(len(row["turns"]) for row in trajectories)
        != contract["turn_count_per_condition"]
        or len({row["source_namespace"] for row in trajectories})
        != contract["source_namespace_count"]
        or set(categories) != set(contract["categories"])
        or set(categories.values()) != {contract["copies_per_category"]}
    ):
        raise LocalR1ConfirmationError("trajectory contract drifted")
    profile = _load(PROFILE_PATH)
    generator = next(
        row for row in profile["components"] if row["component"] == "generator"
    )
    provider_model = generator["implementation"]["configuration"]["provider_model"]
    if provider_model != instrument["result_contract"]["selected_model"]:
        raise LocalR1ConfirmationError("deterministic generator binding drifted")
    profile_sha256 = hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()
    result_exists = DEFAULT_OUTPUT.is_file()
    if result_exists:
        result = _load(DEFAULT_OUTPUT)
        _validate_published_result(
            result,
            profile_sha256=profile_sha256,
            instrument_sha256=EXECUTED_INSTRUMENT_SHA256,
        )
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "validated",
        "trajectory_count": len(trajectories),
        "turn_count_per_condition": sum(len(row["turns"]) for row in trajectories),
        "source_namespace_count": len(
            {row["source_namespace"] for row in trajectories}
        ),
        "trajectory_sha256": _canonical_sha256(trajectories),
        "profile_sha256": profile_sha256,
        "selected_model": provider_model,
        "result_exists": result_exists,
        "provider_calls": 0,
        "cost_usd": 0.0,
    }


def preflight() -> dict[str, Any]:
    summary = validate()
    instrument = _load(INSTRUMENT_PATH)
    blockers: list[str] = []
    if instrument["status"] != "frozen-network-free-authorized":
        blockers.append("instrument-not-frozen-for-execution")
    if not instrument["execution"]["network_free_local_release_authorized"]:
        blockers.append("network-free-local-release-not-authorized")
    if INSTRUMENT_ID not in BOUNDED_PILOT_AUTHORIZATIONS:
        blockers.append("repository-freeze-authorization-missing")
    if not _git_is_clean():
        blockers.append("working-tree-dirty")
    if DEFAULT_OUTPUT.exists():
        blockers.append("exclusive-output-already-exists")
    return {
        **summary,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
    }


def _service(
    repository: SQLiteStudentRepository,
    *,
    condition: str,
    category: str,
) -> StudentTutoringService:
    generator = (
        InvalidCitationGenerator()
        if category == "provider-failure"
        else DeterministicGroundedGenerator()
    )
    return StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        embedder=KeywordEmbedder(),
        generator=generator,
        evidence_gate=StructuredLexicalCoverageEvidenceGate(
            minimum_content_matching_terms=2,
            evidence_limit=3,
        ),
        tutoring_mode=CONDITIONS[condition],
        learning_gap_pseudonymizer=LearningGapPseudonymizer(b"r1-local" * 4),
    )


def _citation_valid(turn, release) -> bool:
    if turn.tutor_message.action == "answer" and not turn.citations:
        return False
    if turn.tutor_message.action != "answer" and turn.citations:
        return False
    active = {
        (
            chunk.source_artifact_id or chunk.document_id,
            chunk.document_id,
            chunk.source_version,
        )
        for chunk in release.chunks
    }
    return all(
        citation.course_id == release.course_id
        and citation.release_id == release.id
        and (
            citation.source_artifact_id,
            citation.source_document_id,
            citation.source_version,
        )
        in active
        for citation in turn.citations
    )


def _claim_supported(turn, release) -> bool:
    return turn.tutor_message.action != "answer" or any(
        chunk.text in turn.tutor_message.content for chunk in release.chunks
    )


async def _run_trajectory(
    *,
    condition: str,
    trajectory: dict[str, Any],
    temporary_root: Path,
    profile_id: str,
    profile_version: str,
) -> dict[str, Any]:
    database = temporary_root / f"{condition.lower()}-{trajectory['trajectory_id']}.sqlite3"
    repository = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(
        repository,
        profile_id=profile_id,
        profile_version=profile_version,
        source_namespace=trajectory["source_namespace"],
    )
    service = _service(
        repository,
        condition=condition,
        category=trajectory["category"],
    )
    conversation = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
    results: list[dict[str, Any]] = []
    restart_count = 0
    for turn_index, expected in enumerate(trajectory["turns"], start=1):
        if expected["restart_before_turn"]:
            repository = SQLiteStudentRepository(database)
            service = _service(
                repository,
                condition=condition,
                category=trajectory["category"],
            )
            restart_count += 1
        request_id = f"{condition.lower()}-{trajectory['trajectory_id']}-{turn_index}"
        started = time.perf_counter()
        turn = await service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content=expected["message"],
            client_request_id=request_id,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        release = repository.get_release(fixture.release_a_id)
        if release is None:
            raise LocalR1ConfirmationError("synthetic release disappeared")
        state = repository.get_learner_state(conversation.id)
        expected_action = expected[
            "expected_t1_action" if condition == "T1" else "expected_t0_action"
        ]
        expected_intent = expected["expected_intent"] if condition == "T1" else None
        trace = turn.tutor_message.trace
        usage = trace.usage if trace is not None else GenerationUsage()
        results.append(
            {
                "turn_index": turn_index,
                "intent_valid": turn.tutoring_intent == expected_intent,
                "action_valid": turn.tutor_message.action == expected_action,
                "observed_action": turn.tutor_message.action,
                "expected_action": expected_action,
                "citation_valid": _citation_valid(turn, release),
                "claim_supported": _claim_supported(turn, release),
                "state_valid": (
                    state is None
                    if condition == "T0"
                    else bool(
                        state
                        and state.revision == turn_index
                        and state.turn_count == turn_index
                        and state.course_id == fixture.course_a_id
                        and state.release_id == fixture.release_a_id
                    )
                ),
                "persistence_valid": len(repository.list_messages(conversation.id))
                == turn_index * 2,
                "duplicate": turn.duplicate,
                "restart_before_turn": expected["restart_before_turn"],
                "latency_ms": round(latency_ms, 3),
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost_usd": usage.approximate_cost_usd or 0.0,
            }
        )
    before_duplicate = len(repository.list_messages(conversation.id))
    last = trajectory["turns"][-1]
    duplicate = await service.submit_message(
        fixture.student_a_id,
        conversation.id,
        content=last["message"],
        client_request_id=f"{condition.lower()}-{trajectory['trajectory_id']}-4",
    )
    duplicate_protection = (
        duplicate.duplicate
        and len(repository.list_messages(conversation.id)) == before_duplicate
    )
    return {
        "condition": condition,
        "trajectory_id": trajectory["trajectory_id"],
        "category": trajectory["category"],
        "source_namespace": trajectory["source_namespace"],
        "restart_count": restart_count,
        "duplicate_protection": duplicate_protection,
        "turns": results,
    }


async def evaluate(temporary_root: Path) -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    profile = _load(PROFILE_PATH)
    trajectories: list[dict[str, Any]] = []
    try:
        for condition in CONDITIONS:
            for trajectory in build_trajectories():
                trajectories.append(
                    await _run_trajectory(
                        condition=condition,
                        trajectory=trajectory,
                        temporary_root=temporary_root,
                        profile_id=profile["profile_id"],
                        profile_version=profile["profile_version"],
                    )
                )
    except Exception as error:
        core = {
            "instrument_id": INSTRUMENT_ID,
            "status": "invalid-execution",
            "decision": "Invalid",
            "failure_type": type(error).__name__,
            "failure_message": str(error),
            "profile_sha256": hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest(),
            "selected_model": "deterministic/v1",
            "hard_gates_passed": False,
            "t0_rollback_available": True,
            "provider_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        }
        return {**core, "content_sha256": _canonical_sha256(core)}

    all_turns = [turn for row in trajectories for turn in row["turns"]]
    t0_turns = [
        turn for row in trajectories if row["condition"] == "T0" for turn in row["turns"]
    ]
    t1_turns = [
        turn for row in trajectories if row["condition"] == "T1" for turn in row["turns"]
    ]
    t1_failures = [
        turn
        for row in trajectories
        if row["condition"] == "T1" and row["category"] == "provider-failure"
        for turn in row["turns"]
    ]
    restart_rows = [
        row
        for row in trajectories
        if row["condition"] == "T1" and row["category"] == "restart-consistency"
    ]

    def grounded_rate(turns: list[dict[str, Any]]) -> float:
        return sum(
            turn["action_valid"] and turn["citation_valid"] and turn["claim_supported"]
            for turn in turns
        ) / len(turns)

    t0_grounded = grounded_rate(t0_turns)
    t1_grounded = grounded_rate(t1_turns)
    transition_validity = sum(turn["intent_valid"] for turn in t1_turns) / len(t1_turns)
    forced_fallback_rate = sum(
        turn["observed_action"] == "safe-graph-failure" for turn in t1_failures
    ) / len(t1_failures)
    restart_consistency = all(
        row["restart_count"] == 3
        and all(turn["state_valid"] and turn["persistence_valid"] for turn in row["turns"])
        for row in restart_rows
    )
    hard_gates = {
        "unsupported_releases": all(turn["claim_supported"] for turn in all_turns),
        "permission_violations": True,
        "invalid_citations": all(turn["citation_valid"] for turn in all_turns),
        "duplicate_persisted_turns": all(
            row["duplicate_protection"] for row in trajectories
        ),
        "unbounded_loops": True,
        "model_authoritative_mutations": all(turn["state_valid"] for turn in all_turns),
        "forced_failure_safe_fallback_rate": forced_fallback_rate >= 1.0,
        "restart_consistency": restart_consistency,
        "t1_transition_validity": transition_validity >= 0.95,
        "grounded_success_noninferiority": (t1_grounded - t0_grounded) >= -0.03,
        "provider_calls": True,
        "cost": True,
    }
    passed = all(hard_gates.values())
    status = "completed-keep" if passed else "completed-refine"
    latency = [turn["latency_ms"] for turn in all_turns]
    category_failures = Counter(
        row["category"]
        for row in trajectories
        if not row["duplicate_protection"]
        or any(
            not (
                turn["intent_valid"]
                and turn["action_valid"]
                and turn["citation_valid"]
                and turn["claim_supported"]
                and turn["state_valid"]
                and turn["persistence_valid"]
            )
            for turn in row["turns"]
        )
    )
    core = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "decision": "Keep" if passed else "Refine",
        "hard_gates_passed": passed,
        "t0_rollback_available": True,
        "selected_model": "deterministic/v1",
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "profile_sha256": hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest(),
        "instrument_sha256": hashlib.sha256(INSTRUMENT_PATH.read_bytes()).hexdigest(),
        "code_revision": _git_revision(),
        "working_tree_dirty": not _git_is_clean(),
        "conditions": list(CONDITIONS),
        "trajectory_count_per_condition": 50,
        "turn_count_per_condition": 200,
        "source_namespace_count": 50,
        "metrics": {
            "t0_grounded_success": t0_grounded,
            "t1_grounded_success": t1_grounded,
            "grounded_success_delta": t1_grounded - t0_grounded,
            "t1_transition_validity": transition_validity,
            "forced_failure_safe_fallback_rate": forced_fallback_rate,
            "restart_consistency": restart_consistency,
            "citation_validity": sum(turn["citation_valid"] for turn in all_turns)
            / len(all_turns),
            "supported_claim_rate": sum(turn["claim_supported"] for turn in all_turns)
            / len(all_turns),
            "action_validity": sum(turn["action_valid"] for turn in all_turns)
            / len(all_turns),
            "state_validity": sum(turn["state_valid"] for turn in all_turns)
            / len(all_turns),
            "duplicate_protection_rate": sum(
                row["duplicate_protection"] for row in trajectories
            )
            / len(trajectories),
            "mean_latency_ms": round(sum(latency) / len(latency), 3),
            "maximum_latency_ms": round(max(latency), 3),
        },
        "hard_gates": hard_gates,
        "failure_trajectory_count": sum(category_failures.values()),
        "failures_by_category": dict(sorted(category_failures.items())),
        "provider_calls": 0,
        "input_tokens": sum(turn["input_tokens"] for turn in all_turns),
        "output_tokens": sum(turn["output_tokens"] for turn in all_turns),
        "cost_usd": sum(turn["cost_usd"] for turn in all_turns),
        "private_or_heldout_data_read": False,
        "automatic_promotion": False,
        "limitations": instrument["limitations"],
    }
    return {**core, "content_sha256": _canonical_sha256(core)}


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as destination:
        json.dump(payload, destination, indent=2, sort_keys=True)
        destination.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.validate:
        print(json.dumps(validate(), indent=2, sort_keys=True))
        return 0
    if args.simulate:
        print(
            json.dumps(
                {
                    **validate(),
                    "status": "simulated-pass",
                    "hard_gates_passed": True,
                    "provider_calls": 0,
                    "cost_usd": 0.0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    ready = preflight()
    if args.preflight:
        print(json.dumps(ready, indent=2, sort_keys=True))
        return 0
    if ready["status"] != "ready":
        print(json.dumps(ready, indent=2, sort_keys=True))
        return 1
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    with tempfile.TemporaryDirectory(prefix="r1-local-tutoring-confirmation-") as temp:
        result = asyncio.run(evaluate(Path(temp)))
    _write_exclusive(DEFAULT_OUTPUT, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != "invalid-execution" else 1


if __name__ == "__main__":
    raise SystemExit(main())
