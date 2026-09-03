#!/usr/bin/env python3
"""Generate the frozen LLM wording bank used by persona selection 022."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from dotenv import load_dotenv
import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_governed_full_autonomy_v2_1_persona_wording_requirements_022 import (  # noqa: E402
    DEFAULT_OUTPUT as REQUIREMENTS_PATH,
    LearnerWordingRequirementV1,
    load_requirements,
)
from scripts.governed_full_autonomy_v2_1_hidden_state_runtime import (  # noqa: E402
    HIDDEN_STATE_CONCEPT_CARDS,
)
from src.digital_twin.evaluation.provider_json import (  # noqa: E402
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    canonical_sha256,
)
from src.digital_twin.evaluation.simulated_learner_v2 import (  # noqa: E402
    FrozenLearnerUtteranceBankV1,
    FrozenLearnerUtteranceV1,
    validate_frozen_utterance,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


ATTEMPTS = ("001", "002")
INSTRUMENT_ID = ""
INSTRUMENT_PATH = Path()
OUTPUT_PATH = Path()
LEDGER_PATH = Path()
RESULT_PATH = Path()


def _select_attempt(attempt: str) -> None:
    if attempt not in ATTEMPTS:
        raise ValueError(f"unknown persona wording-bank attempt: {attempt}")
    global INSTRUMENT_ID, INSTRUMENT_PATH, OUTPUT_PATH, LEDGER_PATH, RESULT_PATH
    suffix = "" if attempt == "001" else "-attempt-002"
    file_suffix = "" if attempt == "001" else "_attempt_002"
    INSTRUMENT_ID = f"governed-full-autonomy-v2-1-persona-wording-bank-022{suffix}"
    INSTRUMENT_PATH = ROOT / "research/05_evaluation/instruments" / (
        f"governed_full_autonomy_v2_1_persona_wording_bank_022{file_suffix}.json"
    )
    OUTPUT_PATH = ROOT / "research/05_evaluation/datasets" / f"{INSTRUMENT_ID}.json"
    LEDGER_PATH = ROOT / "reports/generated" / f"{INSTRUMENT_ID}.sqlite3"
    RESULT_PATH = ROOT / "research/05_evaluation/records" / f"{INSTRUMENT_ID}.json"


_select_attempt("002")


class WordingRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=16, max_length=512)
    text: str = Field(min_length=4, max_length=800)


class WordingBatchV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WordingRowV1]


def _load_instrument() -> dict[str, Any]:
    value = json.loads(INSTRUMENT_PATH.read_text())
    if not isinstance(value, dict) or value.get("instrument_id") != INSTRUMENT_ID:
        raise ValueError("persona wording-bank instrument drifted")
    return value


def _revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _batches(rows: list[Any], size: int) -> list[list[Any]]:
    return [rows[start : start + size] for start in range(0, len(rows), size)]


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["key", "text"],
                    "properties": {
                        "key": {"type": "string"},
                        "text": {"type": "string"}
                    }
                }
            }
        }
    }


_PERSONA_GUIDANCE = {
    "typical-engaged": "engaged, concise, and willing to explain their thinking",
    "beginner": "tentative, plain-spoken, and unfamiliar with technical vocabulary",
    "overconfident": "confident and direct, including when their stated belief is wrong",
    "low-engagement": "brief and low-effort, but still semantically interpretable",
    "entrenched-misconception": "firmly attached to the stated misconception",
    "notification-ignoring": "brief and somewhat detached without changing the meaning",
}


def _prompt(rows: list[LearnerWordingRequirementV1]) -> tuple[str, str]:
    system = (
        "Rewrite synthetic learner utterances for an evaluation. Change wording only. "
        "Preserve the named concept, question/attempt/misconception type, correctness "
        "stance, and all meaning in the canonical text. Do not add facts, answers, "
        "citations, instructions, or new claims. Return each supplied key exactly once."
    )
    items = [
        {
            "key": row.key,
            "persona": row.persona,
            "persona_style": _PERSONA_GUIDANCE[row.persona],
            "utterance_kind": row.kind,
            "concept_id": row.concept_id,
            "canonical_text": row.canonical_text,
        }
        for row in rows
    ]
    prompt = json.dumps({"task": "learner-wording-only", "items": items}, sort_keys=True)
    return system, prompt


def _parse_rows(
    *,
    content: dict[str, Any],
    expected: list[LearnerWordingRequirementV1],
) -> tuple[list[WordingRowV1], list[dict[str, str]]]:
    try:
        batch = WordingBatchV1.model_validate(content)
    except ValidationError as error:
        return [], [{"key": "batch", "reason": f"malformed:{error.errors()[0]['type']}"}]
    expected_by_key = {row.key: row for row in expected}
    observed_keys = [row.key for row in batch.items]
    if len(observed_keys) != len(set(observed_keys)):
        return [], [{"key": "batch", "reason": "duplicate-key"}]
    if set(observed_keys) != set(expected_by_key):
        return [], [{"key": "batch", "reason": "id-set-mismatch"}]
    cards = {row.concept_id: row for row in HIDDEN_STATE_CONCEPT_CARDS}
    accepted: list[WordingRowV1] = []
    rejected: list[dict[str, str]] = []
    for row in batch.items:
        requirement = expected_by_key[row.key]
        failure = validate_frozen_utterance(
            text=row.text,
            kind=requirement.kind,
            card=cards[requirement.concept_id],
            hidden_correct=requirement.hidden_correct,
        )
        if failure is None:
            accepted.append(row)
        else:
            rejected.append({"key": row.key, "reason": failure})
    return accepted, rejected


def validate() -> dict[str, Any]:
    instrument = _load_instrument()
    requirements = load_requirements(REQUIREMENTS_PATH)
    execution = instrument["execution"]
    batches = _batches(requirements.requirements, execution["requirements_per_batch"])
    if len(batches) != execution["maximum_calls"]:
        raise ValueError("persona wording-bank batch count drifted")
    if requirements.content_sha256 != instrument["requirements_content_sha256"]:
        raise ValueError("persona wording requirements binding drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "requirement_count": requirements.requirement_count,
        "batch_count": len(batches),
        "maximum_cost_usd": execution["maximum_cost_usd"],
        "provider_calls": 0,
        "provider_execution_authorized": execution["provider_execution_authorized"],
    }


def preflight(*, resume: bool) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        validate()
    except Exception as error:  # noqa: BLE001
        blockers.append(f"validation-failed:{type(error).__name__}")
    instrument = _load_instrument()
    verified = datetime.fromisoformat(instrument["provider"]["verified_at"])
    age = (datetime.now(UTC) - verified.astimezone(UTC)).total_seconds() / 3600
    if age < 0 or age > instrument["provider"]["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if _dirty():
        blockers.append("repository-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    if instrument["status"] != "frozen-pending-execution":
        blockers.append("instrument-not-frozen")
    if not instrument["execution"]["provider_execution_authorized"]:
        blockers.append("provider-execution-not-authorized")
    if not instrument["execution"]["paid_execution_authorized"]:
        blockers.append("paid-execution-not-authorized")
    if resume and not LEDGER_PATH.is_file():
        blockers.append("resume-ledger-missing")
    if not resume and LEDGER_PATH.exists():
        blockers.append("exclusive-ledger-path-used")
    if OUTPUT_PATH.exists() or RESULT_PATH.exists():
        blockers.append("exclusive-output-path-used")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
    }


async def preflight_live(*, resume: bool) -> dict[str, Any]:
    result = preflight(resume=resume)
    provider = _load_instrument()["provider"]
    key = os.getenv("OPENAI_API_KEY", "").strip()
    identity = None
    if key:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.get(
                    f"https://api.openai.com/v1/models/{provider['provider_model']}",
                    headers={"Authorization": f"Bearer {key}"},
                )
            value = response.json()
            if response.is_error or value.get("id") != provider["provider_model"]:
                result["blockers"].append("model-unavailable-or-identity-drifted")
            else:
                identity = value["id"]
        except (httpx.HTTPError, ValueError):
            result["blockers"].append("model-metadata-check-failed")
    result["blockers"] = sorted(set(result["blockers"]))
    result["status"] = "ready" if not result["blockers"] else "blocked"
    result["live_model_identity"] = identity
    result["provider_inference_calls"] = 0
    return result


def _write_exclusive(path: Path, value: BaseModel | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


async def execute(*, resume: bool) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    readiness = await preflight_live(resume=resume)
    if readiness["status"] != "ready":
        raise RuntimeError("persona wording-bank preflight blocked: " + ", ".join(readiness["blockers"]))
    instrument = _load_instrument()
    requirements = load_requirements(REQUIREMENTS_PATH)
    provider = instrument["provider"]
    execution = instrument["execution"]
    run_binding = {
        "instrument_id": INSTRUMENT_ID,
        "requirements_content_sha256": requirements.content_sha256,
        "provider_binding_sha256": canonical_sha256(provider),
        "code_revision": _revision(),
    }
    ledger = ProviderCallLedgerV1(
        LEDGER_PATH,
        run_binding=run_binding,
        maximum_calls=execution["maximum_calls"],
        maximum_cost_usd=execution["maximum_cost_usd"],
        resume=resume,
        maximum_transport_retries_total=0,
    )
    accepted: dict[str, FrozenLearnerUtteranceV1] = {}
    rejected: list[dict[str, str]] = []
    try:
        for number, rows in enumerate(
            _batches(requirements.requirements, execution["requirements_per_batch"]),
            start=1,
        ):
            system, prompt = _prompt(rows)
            prompt_hash = hashlib.sha256((system + "\n" + prompt).encode()).hexdigest()
            response = await DirectProviderJsonTransport(provider).call_with_ledger(
                ledger=ledger,
                request_key=f"wording-{number:03d}",
                provider_role="learner-wording-author",
                system=system,
                prompt=prompt,
                task="persona-learner-wording",
                schema=_schema(),
            )
            valid_rows, failures = _parse_rows(content=response.content, expected=rows)
            rejected.extend(failures)
            for row in valid_rows:
                accepted[row.key] = FrozenLearnerUtteranceV1(
                    key=row.key,
                    text=row.text,
                    model_id=response.provider_model,
                    prompt_sha256=prompt_hash,
                )
        ledger.mark_complete()
        accounting = ledger.snapshot()
    except KeyboardInterrupt:
        ledger.mark_interrupted()
        raise
    except Exception:
        if ledger.snapshot().get("status") == "running":
            ledger.mark_invalid_execution()
        raise
    finally:
        ledger.close()
    bank = FrozenLearnerUtteranceBankV1(
        bank_id=f"{INSTRUMENT_ID}-output-001",
        entries=[accepted[key] for key in sorted(accepted)],
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": "completed",
        "decision": "Keep" if len(accepted) / requirements.requirement_count >= 0.95 else "Refine",
        "requirements_content_sha256": requirements.content_sha256,
        "requirement_count": requirements.requirement_count,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "coverage": len(accepted) / requirements.requirement_count,
        "rejections": rejected,
        "provider_accounting": accounting,
        "model_output_authoritative": False,
        "private_data_used": False,
    }
    result["content_sha256"] = canonical_sha256(result)
    _write_exclusive(OUTPUT_PATH, bank)
    _write_exclusive(RESULT_PATH, result)
    return result


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--preflight-live", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--attempt", choices=ATTEMPTS, default="002")
    arguments = parser.parse_args()
    _select_attempt(arguments.attempt)
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate()
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.preflight_live:
        result = asyncio.run(preflight_live(resume=arguments.resume))
    else:
        result = asyncio.run(execute(resume=arguments.resume))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
