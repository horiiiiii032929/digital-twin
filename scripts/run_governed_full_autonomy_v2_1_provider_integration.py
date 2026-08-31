"""Run the bounded provider integration for the frozen V2.1 candidate.

This checkpoint proves that the actual reactive and proactive product services
can cross their direct OpenAI boundaries while deterministic code retains
authority. It is deliberately smaller than the academic evaluation in #157 and
cannot promote V2.1 into the release profile.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import httpx

from services.llm import BudgetedLlmClient, OpenAiResponsesClient
from src.digital_twin.action_router import DeterministicActionRouterV2
from src.digital_twin.generation import (
    BoundedPedagogicalPromptBuilder,
    DeterministicPolicyEnforcer,
    LiveAtomicGroundedGenerator,
)
from src.digital_twin.grounding import (
    AtomicClaimEvidenceValidator,
    ExactQuoteAtomicClaimVerifier,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmClient, LlmMessage, LlmResponse
from src.digital_twin.model_policy import (
    OPENAI_GPT_5_6_TERRA_MODEL,
    OPENAI_HIGH_VOLUME_MODEL,
)
from src.digital_twin.repository_freeze import (
    require_pre_evaluation_operation_allowed,
)
from src.digital_twin.student import (
    CanonicalSourceRangeV1,
    CourseConceptV1,
    CourseDomainModelV1,
    CourseMisconceptionV1,
    CourseObjectiveV1,
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
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
)
from src.digital_twin.student.autonomy_runtime import (
    GovernedAutonomousTutoringGraph,
    LiveAutonomousPlanner,
)
from src.digital_twin.student.autonomy_service import (
    GovernedAutonomyService,
    RepositoryGroundedWordingGenerator,
)
from src.digital_twin.student.tutoring_graph import (
    LiveReactiveSemanticPlanner,
    TutoringMode,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_provider_integration_001.json"
)
CANDIDATE_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_release_candidate_001.json"
)
PROFILE_PATH = ROOT / (
    "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)
OUTPUT_PATH = ROOT / (
    "reports/generated/governed-full-autonomy-v2-1-provider-integration-001/"
    "result.json"
)
NOW = datetime(2026, 8, 31, 13, 0, tzinfo=UTC)
OBJECTIVE = "Explain how cache coherence protects replicated processor data."
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


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    candidate = _load(CANDIDATE_PATH)
    if instrument["instrument_id"] != (
        "governed-full-autonomy-v2-1-provider-integration-001"
    ):
        raise ValueError("provider-integration instrument identity drifted")
    if candidate["manifest_id"] != (
        "governed-full-autonomy-v2-1-release-candidate-001"
    ):
        raise ValueError("release-candidate manifest identity drifted")
    if candidate["selection"]["selected_for_release"]:
        raise ValueError("build-only V2.1 candidate cannot be preselected")
    if instrument["execution"]["maximum_retries"] != 0:
        raise ValueError("provider integration must use zero retries")
    if instrument["execution"]["automatic_release_promotion"]:
        raise ValueError("provider integration cannot promote the release")
    if _sha256(PROFILE_PATH) != candidate["system"]["release_profile_sha256"]:
        raise ValueError("candidate release profile hash drifted")
    source_hashes = candidate["source_hashes"]
    expected = {
        ROOT / "compose.local-r1.yml": source_hashes["compose_local_r1_sha256"],
        ROOT / "src/digital_twin/student/tutoring_graph.py": source_hashes[
            "reactive_graph_sha256"
        ],
        ROOT / "src/digital_twin/student/autonomy_runtime.py": source_hashes[
            "proactive_runtime_sha256"
        ],
    }
    for path, digest in expected.items():
        if _sha256(path) != digest:
            raise ValueError(f"candidate source hash drifted: {path.relative_to(ROOT)}")
    return {"instrument": instrument, "candidate": candidate}


class _TaskFixtureClient:
    """Task-specific deterministic provider used only by --simulate."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.calls = 0

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        if not messages:
            raise ValueError("fixture provider requires messages")
        self.calls += 1
        if task == "reactive_tutoring_plan":
            content = json.dumps(
                {
                    "proposed_intent": "correct_misconception",
                    "concept_ids": ["cache-coherence"],
                    "hypothesis_kind": "misconception",
                    "hypothesis_concept_id": "cache-coherence",
                    "hypothesis_confidence": 0.8,
                    "reason_code": "cache-coherence-misconception",
                }
            )
        elif task == "autonomous_tutoring_plan":
            content = json.dumps(
                {
                    "action": "issue-retrieval-practice",
                    "reason_code": "spaced-review-due",
                    "expected_learner_action": "Explain the cited course statement.",
                    "required_evidence_keys": [],
                    "outcome_observation": "Observe the next learner reply.",
                    "stop_condition": "Stop after one intervention.",
                    "replan_condition": "Replan only after a new durable event.",
                }
            )
        elif task == "grounded_tutor_atomic_claims":
            content = json.dumps(
                {
                    "claims": [
                        {
                            "claim_id": "claim-cache-coherence",
                            "text": (
                                "Cache coherence keeps replicated processor data "
                                "consistent."
                            ),
                            "citation_ids": ["S1"],
                        }
                    ]
                }
            )
        else:
            raise ValueError(f"unexpected fixture task: {task}")
        return LlmResponse(
            content=content,
            provider_model=self.model,
            provider_revision=self.model,
            usage=GenerationUsage(
                input_tokens=20,
                output_tokens=20,
                total_tokens=40,
                approximate_cost_usd=0.0,
            ),
        )


def _build_scope(database_path: Path):
    repository = SQLiteStudentRepository(database_path)
    fixture = seed_synthetic_student_workflow(
        repository,
        profile_id="student-tutor-r1-openai-candidate",
        profile_version="v1-build-only",
        source_namespace="v2-provider-integration",
    )
    profiles = TeachingProfileService(repository)
    draft = profiles.create_draft(
        fixture.professor_id,
        fixture.course_a_id,
        {
            "tone": "Patient, precise, and encouraging",
            "depth": TeachingProfileDepth.BALANCED,
            "explanation_structure": ["diagnose", "hint", "check"],
            "example_preferences": ["systems examples"],
            "misconception_handling": (
                "Identify the misconception and ask for one corrected step."
            ),
            "integrity_limits": "Require an attempt before assessed-work help.",
            "help_ladder": ["diagnostic question", "hint", "worked analogy"],
            "outreach_policy": "Private in-app follow-ups within approved limits.",
        },
    )
    preview = profiles.preview(fixture.professor_id, fixture.course_a_id, draft.profile_id)
    approved = profiles.approve(
        fixture.professor_id,
        fixture.course_a_id,
        draft.profile_id,
        preview_sha256=preview.preview_sha256,
    )
    old_release = repository.get_published_release(fixture.course_a_id)
    if old_release is None:
        raise RuntimeError("synthetic source release is missing")
    release = old_release.model_copy(
        update={
            "id": "release-v2-provider-integration",
            "status": StudentReleaseStatus.DRAFT,
            "teaching_profile_id": approved.profile_id,
            "teaching_profile_sha256": approved.content_sha256,
            "created_at": NOW.isoformat(),
        },
        deep=True,
    )
    repository.save_release(release)
    repository.publish_release(release.id)
    chunk = release.chunks[0]
    repository.save_course_domain_model(
        CourseDomainModelV1(
            domain_model_id="domain-v2-provider-integration",
            course_id=fixture.course_a_id,
            release_id=release.id,
            release_sha256=hashlib.sha256(
                release.model_dump_json().encode("utf-8")
            ).hexdigest(),
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
                    description=chunk.text,
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
            misconceptions=[
                CourseMisconceptionV1(
                    misconception_id="misconception-invalidation-diverges",
                    concept_id="cache-coherence",
                    description="Invalidation makes every cache silently diverge.",
                    diagnostic_cues=["invalidation makes every copy stale"],
                )
            ],
            approved_by=fixture.professor_id,
        )
    )
    outreach = ProactiveOutreachService(repository)
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
    return repository, fixture, release, outreach


async def _execute_product(
    *,
    planner_client: LlmClient,
    generator_client: LlmClient,
    planner_budget: BudgetedLlmClient,
    generator_budget: BudgetedLlmClient,
) -> dict[str, Any]:
    del planner_client, generator_client
    with tempfile.TemporaryDirectory(prefix="v2-provider-integration-") as directory:
        database_path = Path(directory) / "candidate.sqlite3"
        repository, fixture, release, outreach = _build_scope(database_path)
        validator = AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
            maximum_claims=8,
            evidence_limit=5,
        )
        generator = LiveAtomicGroundedGenerator(
            generator_budget,
            prompt_builder=BoundedPedagogicalPromptBuilder(),
            policy_enforcer=DeterministicPolicyEnforcer(
                action_router=DeterministicActionRouterV2()
            ),
        )
        tutoring = StudentTutoringService(
            repository,
            profile_path=PROFILE_PATH,
            generator=generator,
            evidence_gate=StructuredLexicalCoverageEvidenceGate(),
            claim_evidence_validator=validator,
            tutoring_mode=TutoringMode.T1_V2,
            learning_gap_pseudonymizer=LearningGapPseudonymizer(
                b"v2-provider-integration-secret-32-bytes"
            ),
            reactive_semantic_planner=LiveReactiveSemanticPlanner(
                planner_budget,
                model_id=OPENAI_GPT_5_6_TERRA_MODEL,
            ),
        )
        conversation = tutoring.create_conversation(
            fixture.student_a_id,
            fixture.course_a_id,
        )
        simple = await tutoring.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="How does cache coherence keep replicated processor data consistent?",
            client_request_id="provider-integration-simple",
        )
        complex_turn = await tutoring.submit_message(
            fixture.student_a_id,
            conversation.id,
            content=(
                "I am confused: my attempt says invalidation makes every copy stale, "
                "so cache coherence causes the copies to diverge."
            ),
            client_request_id="provider-integration-complex",
        )
        proactive_graph = GovernedAutonomousTutoringGraph(
            planner=LiveAutonomousPlanner(
                planner_budget,
                model_id=OPENAI_GPT_5_6_TERRA_MODEL,
            ),
            generator=RepositoryGroundedWordingGenerator(
                repository,
                generator,
                model_id=OPENAI_HIGH_VOLUME_MODEL,
                claim_validator=validator,
            ),
            checkpoint_database_path=str(database_path),
        )
        autonomy = GovernedAutonomyService(
            repository,
            outreach,
            graph=proactive_graph,
        )
        autonomy.set_policy(
            fixture.professor_id,
            fixture.course_a_id,
            approved_course_objectives=[OBJECTIVE],
            allowed_actions=ALLOWED_ACTIONS,
            autonomy_enabled=True,
        )
        goal = autonomy.create_goal(
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            approved_course_objective=OBJECTIVE,
            learner_subgoal="Recall why replicated cache data needs coherence.",
            success_condition="Explain the cited consistency purpose.",
            expires_at=(NOW + timedelta(days=7)).isoformat(),
        )
        autonomy.create_opportunity(
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            goal_id=goal.goal_id,
            event_kind=AutonomousEventKind.SPACED_REVIEW_DUE,
            concept_id="cache-coherence",
            source_chunk_id=release.chunks[0].id,
            earliest_action_at=(NOW - timedelta(minutes=1)).isoformat(),
            latest_action_at=(NOW + timedelta(hours=1)).isoformat(),
            idempotency_key="provider-integration-proactive",
        )
        first_due = await autonomy.process_due(worker_id="provider-worker-a", now=NOW)
        duplicate_due = await autonomy.process_due(
            worker_id="provider-worker-b", now=NOW
        )
        traces = repository.list_agent_traces_v2(
            fixture.course_a_id,
            conversation_id=conversation.id,
        )
        inbox = outreach.list_inbox(fixture.student_a_id)
        action_count = len(repository.list_autonomous_actions(fixture.course_a_id))
        original_counts = (len(traces), len(inbox), action_count)
        repository.close()

        restored = SQLiteStudentRepository(database_path)
        restored_counts = (
            len(
                restored.list_agent_traces_v2(
                    fixture.course_a_id,
                    conversation_id=conversation.id,
                )
            ),
            len(ProactiveOutreachService(restored).list_inbox(fixture.student_a_id)),
            len(restored.list_autonomous_actions(fixture.course_a_id)),
        )
        restored.close()

    released_turns = [simple, complex_turn]
    planner_snapshot = planner_budget.snapshot()
    generator_snapshot = generator_budget.snapshot()
    total_calls = int(planner_snapshot["calls"]) + int(generator_snapshot["calls"])
    total_cost = float(planner_snapshot["reported_cost_usd"]) + float(
        generator_snapshot["reported_cost_usd"]
    )
    gates = {
        "reactive_turns_grounded": all(turn.citations for turn in released_turns),
        "reactive_atomic_claims_persisted": len(traces) == 2,
        "simple_fast_path_used": any(trace.fast_path for trace in traces),
        "complex_planner_bounded": any(
            not trace.fast_path and trace.planning_calls == 1 for trace in traces
        ),
        "exact_generator_identity": all(
            trace.generator_model == OPENAI_HIGH_VOLUME_MODEL for trace in traces
        ),
        "exact_planner_identity": all(
            trace.planner_model == OPENAI_GPT_5_6_TERRA_MODEL for trace in traces
        ),
        "proactive_job_terminal": len(first_due) == 1,
        "duplicate_job_zero": duplicate_due == [],
        "restart_consistent": original_counts == restored_counts,
        "provider_calls_bounded": total_calls <= 12,
        "reported_cost_complete": (
            not planner_snapshot["cost_reporting_failed"]
            and not generator_snapshot["cost_reporting_failed"]
        ),
        "budget_respected": total_cost <= 1.0,
    }
    return {
        "instrument_id": (
            "governed-full-autonomy-v2-1-provider-integration-001"
        ),
        "status": "completed-go-deeper" if all(gates.values()) else "completed-refine",
        "hard_gates_passed": all(gates.values()),
        "gates": gates,
        "reactive_turn_count": len(released_turns),
        "proactive_job_count": len(first_due),
        "proactive_outcome": first_due[0].outcome if first_due else "missing",
        "delivered_message_count": len(inbox),
        "planner": planner_snapshot,
        "generator": generator_snapshot,
        "total_calls": total_calls,
        "reported_cost_usd": round(total_cost, 8),
        "selected_for_release": False,
        "limitations": [
            "This is a public-synthetic provider integration check, not #157's academic evaluation.",
            "A pass leaves V2.1 unselected and records only that the real provider boundaries work.",
        ],
    }


def _budgets(*, fixture: bool):
    if fixture:
        planner_client: LlmClient = _TaskFixtureClient(OPENAI_GPT_5_6_TERRA_MODEL)
        generator_client: LlmClient = _TaskFixtureClient(OPENAI_HIGH_VOLUME_MODEL)
    else:
        planner_client = OpenAiResponsesClient(
            OPENAI_GPT_5_6_TERRA_MODEL,
            timeout_seconds=30,
            max_output_tokens=500,
            reasoning_effort="low",
        )
        generator_client = OpenAiResponsesClient(
            OPENAI_HIGH_VOLUME_MODEL,
            timeout_seconds=30,
            max_output_tokens=600,
            reasoning_effort="none",
        )
    return (
        planner_client,
        generator_client,
        BudgetedLlmClient(planner_client, max_calls=4, max_cost_usd=0.5),
        BudgetedLlmClient(generator_client, max_calls=8, max_cost_usd=0.5),
    )


def simulate() -> dict[str, Any]:
    validate()
    planner, generator, planner_budget, generator_budget = _budgets(fixture=True)
    return asyncio.run(
        _execute_product(
            planner_client=planner,
            generator_client=generator,
            planner_budget=planner_budget,
            generator_budget=generator_budget,
        )
    )


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _model_metadata(model: str, api_key: str) -> dict[str, str]:
    response = httpx.get(
        f"https://api.openai.com/v1/models/{model}",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("id") != model or payload.get("object") != "model":
        raise ValueError(f"OpenAI metadata identity drifted for {model}")
    return {"id": str(payload["id"]), "owned_by": str(payload.get("owned_by", ""))}


def live_preflight() -> dict[str, Any]:
    payload = validate()
    instrument = payload["instrument"]
    candidate = payload["candidate"]
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {"status": "blocked-missing-credential", "provider_calls": 0}
    verified_at = datetime.fromisoformat(
        instrument["models"]["api"]["verified_at"].replace("Z", "+00:00")
    )
    metadata_fresh = datetime.now(UTC) - verified_at <= timedelta(
        hours=instrument["models"]["api"]["metadata_maximum_age_hours"]
    )
    head = _git("rev-parse", "HEAD")
    ancestor = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            candidate["source_revision"],
            head,
        ],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    clean = not _git("status", "--porcelain")
    models = {
        model: _model_metadata(model, api_key)
        for model in (OPENAI_GPT_5_6_TERRA_MODEL, OPENAI_HIGH_VOLUME_MODEL)
    }
    checks = {
        "metadata_fresh": metadata_fresh,
        "candidate_revision_is_ancestor": ancestor,
        "worktree_clean": clean,
        "exclusive_output_unused": not OUTPUT_PATH.exists(),
        "credential_present": True,
        "model_metadata_exact": all(models[name]["id"] == name for name in models),
        "provider_execution_authorized": instrument["execution"][
            "provider_execution_authorized"
        ],
        "paid_execution_authorized": instrument["execution"][
            "paid_execution_authorized"
        ],
    }
    ready_except_authority = all(
        value
        for key, value in checks.items()
        if key not in {"provider_execution_authorized", "paid_execution_authorized"}
    )
    return {
        "status": (
            "ready"
            if all(checks.values())
            else (
                "blocked-not-authorized"
                if ready_except_authority
                else "blocked-preflight-failure"
            )
        ),
        "checks": checks,
        "models": models,
        "provider_calls": 0,
        "maximum_calls": instrument["execution"]["maximum_calls"],
        "maximum_cost_usd": instrument["execution"]["maximum_cost_usd"],
    }


def execute() -> dict[str, Any]:
    preflight = live_preflight()
    if preflight["status"] != "ready":
        raise RuntimeError(f"provider integration is not ready: {preflight['status']}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists():
        raise FileExistsError("provider integration output already exists")
    planner, generator, planner_budget, generator_budget = _budgets(fixture=False)
    try:
        result = asyncio.run(
            _execute_product(
                planner_client=planner,
                generator_client=generator,
                planner_budget=planner_budget,
                generator_budget=generator_budget,
            )
        )
    except BaseException as error:
        result = {
            "instrument_id": (
                "governed-full-autonomy-v2-1-provider-integration-001"
            ),
            "status": "invalid-execution",
            "failure_type": type(error).__name__,
            "selected_for_release": False,
        }
    temporary = OUTPUT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, OUTPUT_PATH)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--live-preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_pre_evaluation_operation_allowed("external_model_evaluation")
    if arguments.validate:
        result = {"status": "valid", **validate()}
    elif arguments.simulate:
        result = simulate()
    elif arguments.live_preflight:
        result = live_preflight()
    else:
        result = execute()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] in {"completed-refine", "invalid-execution", "blocked-preflight-failure"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
