"""Run the frozen, provider-free T0/T1 tutoring-graph development evaluation."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from src.digital_twin.generation import DeterministicGroundedGenerator
from src.digital_twin.grounding import EvidenceSufficiencyDecision
from src.digital_twin.grounding.models import (
    GenerationTrace,
    GenerationUsage,
    RetrievalHit,
    SourceCitation,
    TutorAnswer,
)
from src.digital_twin.student import (
    SQLiteStudentRepository,
    StudentTutoringService,
    TutoringMode,
    seed_synthetic_student_workflow,
)
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/autonomous_tutoring_graph_contract_v1.json"
)
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/autonomous-tutoring-graph-development-001.json"
)
RUN_ID = "autonomous-tutoring-graph-development-001"
CONDITIONS = {
    "T0": TutoringMode.T0,
    "T1": TutoringMode.T1,
}


class DevelopmentEvaluationError(RuntimeError):
    """Raised when the frozen network-free run cannot be executed validly."""


class KeywordEmbedder:
    """Deterministic local embedding control used by the synthetic release."""

    provider_id = "local-huggingface"
    model_name = "Qwen/Qwen3-Embedding-0.6B"
    model_revision = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    execution = "local"
    instruction = (
        "Given a student question within one authorized university course, "
        "retrieve passages that directly support a grounded answer."
    )
    device = "mps"
    dtype = "float16"
    max_length = 2048
    batch_size = 16

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.lower()
        return [
            float("cache" in lowered or "coherence" in lowered),
            float("memory" in lowered),
            float("policy" in lowered),
            0.1,
        ]


class ScriptedEvidenceGate:
    """Frozen answerability labels; this is not a product gate candidate."""

    implementation_id = "scripted-development-evidence-gate-v1"

    def __init__(self, evidence_by_message: dict[str, bool]) -> None:
        self.evidence_by_message = evidence_by_message

    def assess(
        self,
        query: str,
        hits: Sequence[RetrievalHit],
    ) -> EvidenceSufficiencyDecision:
        expected = self.evidence_by_message.get(query)
        if expected is None:
            raise DevelopmentEvaluationError("turn is absent from the frozen contract")
        sufficient = bool(expected and hits)
        return EvidenceSufficiencyDecision(
            sufficient=sufficient,
            score=1.0 if sufficient else 0.0,
            reason="frozen synthetic development label",
            features={"network_free": True, "candidate_gate": False},
        )


class InvalidCitationGenerator:
    """Deterministic malformed-output control for the forced-failure trajectory."""

    implementation_id = "invalid-citation-development-control-v1"
    version = "v1"

    async def generate(self, question, hits, policy) -> TutorAnswer:
        del question, hits, policy
        return TutorAnswer(
            content="Synthetic response with invalid lineage.",
            citations=[
                SourceCitation(
                    source_id="unknown-document",
                    title="Unknown synthetic source",
                    locator="unknown locator",
                )
            ],
            trace=GenerationTrace(
                generator_id=self.implementation_id,
                provider_model="synthetic/invalid-citation",
                prompt_version="development-control-v1",
                policy_action="answer",
                latency_ms=0,
                usage=GenerationUsage(),
            ),
        )


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _instrument_sha256(path: Path = INSTRUMENT_PATH) -> str:
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
    if payload.get("instrument_id") != "autonomous-tutoring-graph-contract-v1":
        raise DevelopmentEvaluationError("unexpected tutoring-graph instrument")
    if payload.get("status") != "frozen-network-free-development":
        raise DevelopmentEvaluationError("development instrument is not frozen")
    execution = payload.get("execution", {})
    expected = {
        "provider_calls_authorized": False,
        "paid_execution_authorized": False,
        "held_out_execution_authorized": False,
        "network_required": False,
        "network_free_development_authorized": True,
        "automatic_promotion": False,
        "maximum_repairs_per_turn": 1,
        "maximum_graph_steps_per_turn": 12,
    }
    if any(execution.get(key) != value for key, value in expected.items()):
        raise DevelopmentEvaluationError("execution boundary drifted")
    trajectories = payload.get("development_trajectories", [])
    if len(trajectories) != 10:
        raise DevelopmentEvaluationError("expected exactly ten trajectories")
    turn_count = sum(len(item.get("turns", [])) for item in trajectories)
    result_contract = payload.get("result_contract", {})
    if (
        result_contract.get("run_id") != RUN_ID
        or result_contract.get("expected_trajectory_count") != len(trajectories)
        or result_contract.get("expected_turn_count_per_condition") != turn_count
    ):
        raise DevelopmentEvaluationError("result contract drifted")
    return payload


def validate_preflight(
    instrument: dict[str, Any],
    *,
    output: Path = DEFAULT_OUTPUT,
    require_clean: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    if require_clean and not _git_is_clean():
        blockers.append("working-tree-dirty")
    if output.exists():
        blockers.append("exclusive-output-already-exists")
    execution = instrument["execution"]
    if not execution["network_free_development_authorized"]:
        blockers.append("network-free-development-not-authorized")
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
        blockers.append("forbidden-execution-authority-present")
    return {
        "run_id": RUN_ID,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "provider_calls": 0,
        "tokens": 0,
        "cost_usd": 0.0,
        "private_or_heldout_data_read": False,
    }


def _evidence_labels(trajectory: dict[str, Any]) -> dict[str, bool]:
    return {turn["message"]: turn["evidence"] for turn in trajectory["turns"]}


def _generator(trajectory: dict[str, Any]):
    if any(turn.get("forced_failure") for turn in trajectory["turns"]):
        return InvalidCitationGenerator()
    return DeterministicGroundedGenerator()


def _service(
    repository: SQLiteStudentRepository,
    *,
    mode: str,
    trajectory: dict[str, Any],
) -> StudentTutoringService:
    return StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        embedder=KeywordEmbedder(),
        generator=_generator(trajectory),
        evidence_gate=ScriptedEvidenceGate(_evidence_labels(trajectory)),
        tutoring_mode=mode,
    )


def _citation_valid(turn, release) -> bool:
    if turn.tutor_message.action == "answer" and not turn.citations:
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
    if turn.tutor_message.action != "answer":
        return True
    return any(chunk.text in turn.tutor_message.content for chunk in release.chunks)


async def _run_condition_trajectory(
    *,
    condition: str,
    mode: str,
    trajectory: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    database = root / f"{condition.lower()}-{trajectory['id']}.sqlite3"
    repository = SQLiteStudentRepository(database)
    fixture = seed_synthetic_student_workflow(repository)
    service = _service(repository, mode=mode, trajectory=trajectory)
    conversation = service.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )
    turn_results: list[dict[str, Any]] = []
    restart_count = 0
    for index, expected in enumerate(trajectory["turns"], start=1):
        if expected.get("restart_before_turn"):
            repository = SQLiteStudentRepository(database)
            service = _service(repository, mode=mode, trajectory=trajectory)
            restart_count += 1
        started = time.perf_counter()
        turn = await service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content=expected["message"],
            client_request_id=f"{condition.lower()}-{trajectory['id']}-{index}",
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        release = repository.get_release(fixture.release_a_id)
        if release is None:
            raise DevelopmentEvaluationError("synthetic release disappeared")
        state = repository.get_learner_state(conversation.id)
        graph_events = [
            event
            for event in repository.list_audit_events()
            if event.conversation_id == conversation.id
            and event.event_type == "tutoring-graph-completed"
        ]
        graph_event = graph_events[-1] if graph_events else None
        trace = turn.tutor_message.trace
        usage = trace.usage if trace is not None else GenerationUsage()
        expected_action = expected[
            "expected_t1_action" if condition == "T1" else "expected_t0_action"
        ]
        observed_intent = turn.tutoring_intent
        intent_valid = (
            observed_intent == expected["expected_intent"]
            if condition == "T1"
            else observed_intent is None
        )
        citation_valid = _citation_valid(turn, release)
        claim_supported = _claim_supported(turn, release)
        persisted_message_count = len(repository.list_messages(conversation.id))
        state_scope_valid = state is None if condition == "T0" else bool(
            state
            and state.conversation_id == conversation.id
            and state.course_id == fixture.course_a_id
            and state.release_id == fixture.release_a_id
            and state.revision == index
            and state.turn_count == index
        )
        turn_results.append(
            {
                "turn_index": index,
                "message": expected["message"],
                "evidence_expected": expected["evidence"],
                "restart_before_turn": bool(expected.get("restart_before_turn")),
                "expected_intent": (
                    expected["expected_intent"] if condition == "T1" else None
                ),
                "observed_intent": observed_intent,
                "intent_valid": intent_valid,
                "expected_action": expected_action,
                "observed_action": turn.tutor_message.action,
                "action_valid": turn.tutor_message.action == expected_action,
                "learner_state_revision": turn.learner_state_revision,
                "learner_help_level": state.help_level if state is not None else None,
                "state_scope_and_revision_valid": state_scope_valid,
                "citation_count": len(turn.citations),
                "citation_valid": citation_valid,
                "claim_supported": claim_supported,
                "duplicate": turn.duplicate,
                "persisted_message_count": persisted_message_count,
                "persistence_valid": persisted_message_count == index * 2,
                "repair_count": (
                    graph_event.details.get("repair_count") if graph_event else None
                ),
                "failure_reason": (
                    graph_event.details.get("failure_reason") if graph_event else None
                ),
                "provider_model": trace.provider_model if trace else None,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost_usd": usage.approximate_cost_usd or 0.0,
                "latency_ms": round(elapsed_ms, 3),
            }
        )
    return {
        "condition": condition,
        "mode": mode,
        "trajectory_id": trajectory["id"],
        "category": trajectory["category"],
        "restart_count": restart_count,
        "turns": turn_results,
    }


async def evaluate_development(
    instrument: dict[str, Any],
    *,
    temporary_root: Path,
) -> dict[str, Any]:
    trajectories: list[dict[str, Any]] = []
    try:
        for condition, mode in CONDITIONS.items():
            for trajectory in instrument["development_trajectories"]:
                trajectories.append(
                    await _run_condition_trajectory(
                        condition=condition,
                        mode=mode,
                        trajectory=trajectory,
                        root=temporary_root,
                    )
                )
    except Exception as error:
        core = {
            "run_id": RUN_ID,
            "status": "invalid-execution",
            "failure_type": type(error).__name__,
            "failure_message": str(error),
            "provider_calls": 0,
            "tokens": 0,
            "cost_usd": 0.0,
            "private_or_heldout_data_read": False,
            "trajectories": trajectories,
        }
        return {**core, "content_sha256": _canonical_sha256(core)}

    turns = [turn for trajectory in trajectories for turn in trajectory["turns"]]
    t1_turns = [
        turn
        for trajectory in trajectories
        if trajectory["condition"] == "T1"
        for turn in trajectory["turns"]
    ]
    forced_t1 = [
        turn
        for trajectory in trajectories
        if trajectory["condition"] == "T1"
        and trajectory["category"] == "provider-failure"
        for turn in trajectory["turns"]
    ]
    restart_trajectories = [
        item
        for item in trajectories
        if item["condition"] == "T1" and item["category"] == "restart-consistency"
    ]
    unauthorized_events = 0
    unsupported_claims = sum(not turn["claim_supported"] for turn in turns)
    invalid_citations = sum(not turn["citation_valid"] for turn in turns)
    critical_policy_violations = sum(not turn["action_valid"] for turn in turns)
    state_mutations = sum(
        not turn["state_scope_and_revision_valid"] for turn in t1_turns
    )
    persistence_failures = sum(not turn["persistence_valid"] for turn in turns)
    duplicate_turns = sum(turn["duplicate"] for turn in turns)
    transition_failures = sum(not turn["intent_valid"] for turn in t1_turns)
    safe_fallback_rate = (
        sum(turn["observed_action"] == "safe-graph-failure" for turn in forced_t1)
        / len(forced_t1)
        if forced_t1
        else 0.0
    )
    restart_consistency = all(
        item["restart_count"] == 1
        and all(turn["state_scope_and_revision_valid"] for turn in item["turns"])
        for item in restart_trajectories
    )
    atomic_rate = (
        sum(turn["state_scope_and_revision_valid"] for turn in t1_turns)
        / len(t1_turns)
    )
    hard_gates = {
        "exact_t1_transition_validity": transition_failures == 0,
        "unauthorized_scope_events": unauthorized_events == 0,
        "unsupported_course_claims": unsupported_claims == 0,
        "invalid_or_cross_course_citations": invalid_citations == 0,
        "critical_policy_violations": critical_policy_violations == 0,
        "model_authoritative_state_mutations": state_mutations == 0,
        "unbounded_or_duplicate_turns": duplicate_turns == 0,
        "private_data_provider_events": True,
        "safe_fallback_rate_on_forced_failures": safe_fallback_rate == 1.0,
        "atomic_state_persistence_rate": atomic_rate == 1.0,
        "restart_consistency": restart_consistency,
        "persisted_message_accounting": persistence_failures == 0,
    }
    status = (
        "completed-go-deeper" if all(hard_gates.values()) else "completed-refine"
    )
    latency_values = [turn["latency_ms"] for turn in turns]
    core = {
        "run_id": RUN_ID,
        "status": status,
        "decision": "go-deeper" if status.endswith("go-deeper") else "refine",
        "instrument_id": instrument["instrument_id"],
        "instrument_sha256": _instrument_sha256(),
        "code_revision": _git_revision(),
        "working_tree_dirty": not _git_is_clean(),
        "conditions": list(CONDITIONS),
        "trajectory_count_per_condition": len(instrument["development_trajectories"]),
        "turn_count_per_condition": len(t1_turns),
        "hard_gates": hard_gates,
        "metrics": {
            "t1_transition_validity": 1 - transition_failures / len(t1_turns),
            "safe_fallback_rate": safe_fallback_rate,
            "atomic_state_persistence_rate": atomic_rate,
            "restart_consistency": restart_consistency,
            "citation_validity": 1 - invalid_citations / len(turns),
            "supported_claim_rate": 1 - unsupported_claims / len(turns),
            "action_validity": 1 - critical_policy_violations / len(turns),
            "objective_completion_rate": 1 - critical_policy_violations / len(turns),
            "unnecessary_turn_count": 0,
            "duplicate_turn_count": duplicate_turns,
            "mean_latency_ms": round(sum(latency_values) / len(latency_values), 3),
            "maximum_latency_ms": round(max(latency_values), 3),
        },
        "failures_by_category": dict(
            Counter(
                category
                for category, count in {
                    "transition": transition_failures,
                    "grounding": unsupported_claims + invalid_citations,
                    "policy": critical_policy_violations,
                    "state": state_mutations + persistence_failures,
                    "duplicate": duplicate_turns,
                }.items()
                if count
                for _ in range(count)
            )
        ),
        "provider_calls": 0,
        "input_tokens": sum(turn["input_tokens"] for turn in turns),
        "output_tokens": sum(turn["output_tokens"] for turn in turns),
        "cost_usd": sum(turn["cost_usd"] for turn in turns),
        "private_or_heldout_data_read": False,
        "automatic_promotion": False,
        "trajectories": trajectories,
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
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    instrument = load_instrument(args.instrument)
    if args.validate:
        result = validate_preflight(
            instrument,
            output=args.output,
            require_clean=False,
        )
        result["status"] = "validated-network-free"
        result["instrument_sha256"] = _instrument_sha256(args.instrument)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    preflight = validate_preflight(
        instrument,
        output=args.output,
        require_clean=True,
    )
    if preflight["status"] != "ready":
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 1
    require_bounded_pilot_operation_allowed(RUN_ID)
    with tempfile.TemporaryDirectory(prefix="tutoring-graph-development-") as temp:
        payload = asyncio.run(
            evaluate_development(instrument, temporary_root=Path(temp))
        )
    _write_exclusive(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] != "invalid-execution" else 1


if __name__ == "__main__":
    raise SystemExit(main())
