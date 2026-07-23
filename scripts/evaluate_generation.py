"""Evaluate deterministic or explicitly authorized grounded-generation candidates."""

import argparse
import asyncio
import json
import subprocess
import tempfile
from pathlib import Path

from services.llm import LiteLlmClient
from scripts.synthetic_course_corpus import build_retrieval_evaluation_chunks
from src.digital_twin.generation import (
    DeterministicGroundedGenerator,
    LiveGroundedGenerator,
    evaluate_generator,
    load_generation_evaluation_set,
)
from src.digital_twin.grounding import BM25Retriever
from src.digital_twin.tutor_policy import (
    FieldStatus,
    ReleaseStatus,
    build_initial_policy,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "research" / "05_evaluation" / "generation_v1.json"


def main() -> None:
    arguments = _arguments()
    summary = asyncio.run(_evaluate(arguments))
    live = arguments.model is not None
    payload = {
        "dataset": str(arguments.dataset.relative_to(ROOT)),
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "paid_provider_called": _paid_provider_called(arguments.model),
        "provider_selection": (
            f"unselected candidate: {arguments.model}"
            if live
            else (
                "DeepSeek API constrained but unqualified; synthetic-only "
                "budget approved at USD 10"
            )
        ),
        "evaluation_mode": _evaluation_mode(arguments.model),
        "result": summary.model_dump(mode="json"),
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is None:
        compact = {
            **{key: value for key, value in payload.items() if key != "result"},
            "result": summary.model_dump(mode="json", exclude={"cases"}),
        }
        print(json.dumps(compact, indent=2, sort_keys=True))
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")
    if not live:
        _check_regressions(summary)


async def _evaluate(arguments):
    evaluation_set = load_generation_evaluation_set(arguments.dataset)
    with tempfile.TemporaryDirectory(prefix="digital-twin-generation-") as temp:
        chunks = build_retrieval_evaluation_chunks(Path(temp))
        retriever = BM25Retriever(chunks, k1=1.2, b=0.75)
        policy = _approved_synthetic_policy()
        generator = (
            LiveGroundedGenerator(
                LiteLlmClient(
                    arguments.model,
                    timeout_seconds=arguments.timeout_seconds,
                    max_output_tokens=arguments.max_output_tokens,
                    response_format=(
                        {"type": "json_object"} if arguments.json_mode else None
                    ),
                )
            )
            if arguments.model is not None
            else DeterministicGroundedGenerator()
        )
        return await evaluate_generator(
            (
                f"live-grounded-generator-{arguments.model}"
                if arguments.model is not None
                else "deterministic-grounded-generator-v1"
            ),
            generator,
            retriever,
            policy,
            evaluation_set,
        )


def _approved_synthetic_policy():
    policy = build_initial_policy().model_copy(deep=True)
    for field in policy.all_fields:
        if field.status == FieldStatus.BLOCKS_RELEASE:
            field.status = FieldStatus.RESOLVED
        if field.id == "knowledge_source_policy":
            field.value = {**field.value, "confirmed": True}
        if field.id in {"academic_integrity_policy", "professor_release_approval"}:
            field.status = FieldStatus.RESOLVED
        if field.id == "professor_release_approval":
            field.value = "approved"
    policy.status = ReleaseStatus.APPROVED
    policy.release_status = ReleaseStatus.APPROVED
    return policy


def _check_regressions(summary) -> None:
    failures = []
    for metric in (
        "policy_action_accuracy",
        "citation_validity",
        "graded_work_redirect_accuracy",
        "no_evidence_accuracy",
        "provider_suppression_accuracy",
    ):
        if getattr(summary, metric) < 1:
            failures.append(f"{metric} below 1.0")
    if summary.total_input_tokens or summary.total_output_tokens:
        failures.append("deterministic control used provider tokens")
    if summary.approximate_cost_usd is not None:
        failures.append("deterministic control reported provider cost")
    if failures:
        raise SystemExit("; ".join(failures))


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--json-mode", action="store_true")
    parser.add_argument(
        "--allow-external-provider",
        action="store_true",
        help=(
            "Acknowledge that a non-Ollama model can make an external, "
            "potentially billable provider call."
        ),
    )
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--max-output-tokens", type=int, default=600)
    arguments = parser.parse_args()
    if _external_provider_requires_acknowledgment(
        arguments.model,
        arguments.allow_external_provider,
    ):
        parser.error(
            "a non-Ollama model requires --allow-external-provider and a "
            "separately recorded budget decision"
        )
    return arguments


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _paid_provider_called(model: str | None) -> bool:
    """Conservatively classify non-Ollama live calls as potentially billable."""
    return model is not None and not model.startswith("ollama/")


def _external_provider_requires_acknowledgment(
    model: str | None,
    allowed: bool,
) -> bool:
    return _paid_provider_called(model) and not allowed


def _evaluation_mode(model: str | None) -> str:
    if model is None:
        return "deterministic-control"
    if model.startswith("ollama/"):
        return "live-local-candidate"
    return "live-external-candidate"


if __name__ == "__main__":
    main()
