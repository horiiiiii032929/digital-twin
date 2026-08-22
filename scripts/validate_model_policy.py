#!/usr/bin/env python3
"""Validate current model bindings without making a model call."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.judge_professor_fidelity import JUDGE_MODELS
from scripts.second_review_multimodal_benchmark import (
    DEFAULT_MODEL as HISTORICAL_CLAUDE_MODEL,
)
from services.embeddings.jina_client import DEFAULT_MODEL as JINA_EMBEDDING_MODEL
from services.reranking.jina_client import DEFAULT_MODEL as JINA_RERANKER_MODEL
from src.digital_twin.model_policy import (
    CURRENT_MODEL_BINDINGS,
    LOCAL_GENERAL_MODEL,
    LOCAL_GENERAL_MODEL_DIGEST,
    OPENROUTER_DEEPSEEK_MODEL,
    OPENROUTER_GEMINI_REVIEW_MODEL,
    OPENROUTER_INDEPENDENT_REVIEW_MODEL,
    OPENROUTER_QWEN_REVIEW_MODEL,
    POLICY_ID,
    ModelPolicyError,
    controlled_openrouter_provider_options,
    require_model_allowed,
    require_registered_current_model,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "package.json"
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
POLICY_DOC_PATH = ROOT / "research/00_admin/2026-08-21-current-model-policy-v3.md"

PROHIBITED_COMMAND_MARKERS = (
    "gemma",
    "claude",
    "--model qwen3:4b",
    "--model qwen3.5:4b",
    "huihui_ai/qwen3-abliterated",
)

HISTORICAL_MODEL_ENTRYPOINTS = (
    "scripts/build_multimodal_development_artifacts.py",
    "scripts/run_it5002_retrieval_rapid.py",
    "scripts/build_it5002_rapid_dataset.py",
    "scripts/draft_cross_course_benchmark.py",
    "scripts/second_review_cross_course_benchmark.py",
    "scripts/run_course_tutor_hybrid_review.py",
    "scripts/review_generator_qualification_v2.py",
    "scripts/run_factual_qa_quality_pilot.py",
    "scripts/second_review_multimodal_benchmark.py",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate() -> dict[str, Any]:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    scripts = package["scripts"]
    violations = {
        name: marker
        for name, command in scripts.items()
        for marker in PROHIBITED_COMMAND_MARKERS
        if marker in f"{name} {command}".casefold()
    }
    _require(not violations, f"package commands expose retired models: {violations}")

    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    components = {
        component["component"]: component
        for component in profile["components"]
    }
    generator_model = components["generator"]["implementation"]["configuration"][
        "provider_model"
    ]
    embedding_model = components["retriever"]["implementation"]["configuration"][
        "embedding_model"
    ]
    require_registered_current_model(generator_model)
    require_registered_current_model(embedding_model)
    require_registered_current_model(JINA_EMBEDDING_MODEL)
    require_registered_current_model(JINA_RERANKER_MODEL)
    require_registered_current_model(OPENROUTER_DEEPSEEK_MODEL)
    require_registered_current_model(OPENROUTER_INDEPENDENT_REVIEW_MODEL)
    require_registered_current_model(OPENROUTER_QWEN_REVIEW_MODEL)
    require_registered_current_model(OPENROUTER_GEMINI_REVIEW_MODEL)
    try:
        require_model_allowed(HISTORICAL_CLAUDE_MODEL)
    except ModelPolicyError:
        pass
    else:
        raise ValueError("the historical Claude entrypoint is not prohibited")
    _require(
        JUDGE_MODELS == ("deepseek-v4-pro", LOCAL_GENERAL_MODEL),
        "professor-fidelity judge bindings are not current",
    )
    for model in JUDGE_MODELS:
        require_registered_current_model(model)

    _require(
        re.fullmatch(r"[0-9a-f]{64}", LOCAL_GENERAL_MODEL_DIGEST) is not None,
        "the local Qwen3.5 artifact must be pinned to its full digest",
    )
    _require(POLICY_DOC_PATH.is_file(), "current model policy record is missing")
    _require(
        controlled_openrouter_provider_options()
        == {
            "extra_body": {
                "provider": {
                    "allow_fallbacks": False,
                    "require_parameters": True,
                    "data_collection": "deny",
                    "zdr": True,
                }
            }
        },
        "controlled OpenRouter routing policy drifted",
    )

    guarded_entrypoints = []
    for relative in HISTORICAL_MODEL_ENTRYPOINTS:
        source = (ROOT / relative).read_text(encoding="utf-8")
        _require(
            "require_model_allowed" in source
            or "require_registered_current_model" in source,
            f"historical model entrypoint lacks execution guard: {relative}",
        )
        guarded_entrypoints.append(relative)

    registered = [
        {
            "role": binding.role,
            "model": binding.provider_model,
            "status": binding.status,
        }
        for binding in CURRENT_MODEL_BINDINGS
    ]
    return {
        "status": "passed",
        "policy_id": POLICY_ID,
        "gemma_execution_allowed": False,
        "claude_execution_allowed": False,
        "retired_general_qwen_execution_allowed": False,
        "local_general_model": LOCAL_GENERAL_MODEL,
        "local_general_model_digest": LOCAL_GENERAL_MODEL_DIGEST,
        "openrouter_models": [
            OPENROUTER_DEEPSEEK_MODEL,
            OPENROUTER_INDEPENDENT_REVIEW_MODEL,
            OPENROUTER_QWEN_REVIEW_MODEL,
            OPENROUTER_GEMINI_REVIEW_MODEL,
        ],
        "openrouter_provider_options": controlled_openrouter_provider_options(),
        "active_profile": {
            "generator": generator_model,
            "embedding": embedding_model,
        },
        "registered_models": registered,
        "guarded_historical_entrypoints": guarded_entrypoints,
        "model_called": False,
    }


def main() -> int:
    print(json.dumps(validate(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
