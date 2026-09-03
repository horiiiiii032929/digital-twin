#!/usr/bin/env python3
"""Discover the immutable semantic frames used by selection 022.

The discovery executes the real product boundary with deterministic learner
wording.  It records only public synthetic utterance frames and their
semantic-hash-bound keys.  No provider is called and no model-authored text is
accepted here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_governed_full_autonomy_v2_1_persona_robust_selection_022 import (  # noqa: E402
    ABLATION_CONDITION,
    DEFAULT_SEEDS,
    PRIMARY_CONDITIONS,
    PROGRAM_ID,
    _is_ablation_cell,
    run_case,
)
from src.digital_twin.evaluation.learner_simulator import (  # noqa: E402
    PERSONA_ROBUST_PERSONAS,
    LearnerPersona,
    SimulatorFamily,
)
from src.digital_twin.evaluation.provider_json import canonical_sha256  # noqa: E402
from src.digital_twin.evaluation.simulated_learner_v2 import (  # noqa: E402
    ResponseRealizationMethod,
)
from src.digital_twin.evaluation.simulated_learner_v1 import (  # noqa: E402
    LearnerUtterance,
)


REQUIREMENTS_ID = "governed-full-autonomy-v2-1-persona-wording-requirements-022"
DEFAULT_OUTPUT = ROOT / "research/05_evaluation/datasets" / f"{REQUIREMENTS_ID}.json"


class LearnerWordingRequirementV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=16, max_length=512)
    persona: str = Field(min_length=2, max_length=80)
    family: str = Field(min_length=2, max_length=80)
    seed: int
    kind: str = Field(pattern=r"^(attempt|question|misconception)$")
    concept_id: str = Field(min_length=2, max_length=160)
    hidden_correct: bool | None
    prompted: bool
    canonical_text: str = Field(min_length=4, max_length=800)


class LearnerWordingRequirementsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    requirements_id: str
    selection_program_id: str
    source_code_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    discovery_method: str
    virtual_days_per_history: int = Field(ge=1)
    discovery_history_count: int = Field(ge=1)
    requirement_count: int = Field(ge=1)
    requirements: list[LearnerWordingRequirementV1]
    provider_calls: int = 0
    private_data_used: bool = False
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_package(self) -> "LearnerWordingRequirementsV1":
        if self.requirements_id != REQUIREMENTS_ID:
            raise ValueError("wording requirements ID drifted")
        if self.selection_program_id != PROGRAM_ID:
            raise ValueError("selection program ID drifted")
        if self.discovery_method != ResponseRealizationMethod.DETERMINISTIC_FRAME:
            raise ValueError("requirements must come from deterministic discovery")
        if self.requirement_count != len(self.requirements):
            raise ValueError("wording requirement count drifted")
        keys = [item.key for item in self.requirements]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("wording requirement keys must be sorted and unique")
        if self.provider_calls != 0 or self.private_data_used:
            raise ValueError("requirements discovery must remain network-free and public")
        payload = self.model_dump(exclude={"content_sha256"}, mode="json")
        if self.content_sha256 != canonical_sha256(payload):
            raise ValueError("wording requirements content hash drifted")
        return self


def _revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _requirement_from_utterance(
    *,
    persona: LearnerPersona,
    family: SimulatorFamily,
    seed: int,
    item: LearnerUtterance,
) -> LearnerWordingRequirementV1:
    if not item.realization_key:
        raise ValueError("deterministic utterance is missing its semantic realization key")
    return LearnerWordingRequirementV1(
        key=item.realization_key,
        persona=persona.name,
        family=family.value,
        seed=seed,
        kind=item.kind,
        concept_id=item.concept_id,
        hidden_correct=item.hidden_correct,
        prompted=item.prompted,
        canonical_text=item.text,
    )


async def discover_requirements(
    *,
    runtime_root: Path,
    days: int = 30,
    personas: tuple[LearnerPersona, ...] = PERSONA_ROBUST_PERSONAS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    code_revision: str | None = None,
) -> LearnerWordingRequirementsV1:
    revision = code_revision or _revision()
    requirements: dict[str, LearnerWordingRequirementV1] = {}
    history_count = 0
    for persona_index, persona in enumerate(personas):
        for family in SimulatorFamily:
            for seed in seeds:
                conditions = list(PRIMARY_CONDITIONS)
                if _is_ablation_cell(
                    persona_index=persona_index,
                    method_index=0,
                    family=family,
                    seed=seed,
                ):
                    conditions.append(ABLATION_CONDITION)
                for condition in conditions:
                    observed: list[LearnerUtterance] = []
                    await run_case(
                        root=runtime_root,
                        condition=condition,
                        persona=persona,
                        family=family,
                        method=ResponseRealizationMethod.DETERMINISTIC_FRAME,
                        seed=seed,
                        days=days,
                        bank=None,
                        code_revision=revision,
                        utterance_observer=observed.append,
                    )
                    history_count += 1
                    for utterance in observed:
                        requirement = _requirement_from_utterance(
                            persona=persona,
                            family=family,
                            seed=seed,
                            item=utterance,
                        )
                        prior = requirements.get(requirement.key)
                        if prior is not None and prior != requirement:
                            raise ValueError(
                                f"semantic realization key collision: {requirement.key}"
                            )
                        requirements[requirement.key] = requirement
    rows = [requirements[key] for key in sorted(requirements)]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "requirements_id": REQUIREMENTS_ID,
        "selection_program_id": PROGRAM_ID,
        "source_code_revision": revision,
        "discovery_method": str(ResponseRealizationMethod.DETERMINISTIC_FRAME),
        "virtual_days_per_history": days,
        "discovery_history_count": history_count,
        "requirement_count": len(rows),
        "requirements": [row.model_dump(mode="json") for row in rows],
        "provider_calls": 0,
        "private_data_used": False,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    return LearnerWordingRequirementsV1.model_validate(payload)


def load_requirements(path: Path) -> LearnerWordingRequirementsV1:
    return LearnerWordingRequirementsV1.model_validate_json(path.read_text())


def write_exclusive(path: Path, package: LearnerWordingRequirementsV1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(package.model_dump_json(indent=2))
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--build", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--days", type=int, default=30)
    arguments = parser.parse_args()
    if arguments.validate:
        package = load_requirements(arguments.output)
    else:
        with tempfile.TemporaryDirectory(prefix="persona-wording-discovery-") as temp:
            package = asyncio.run(
                discover_requirements(
                    runtime_root=Path(temp),
                    days=arguments.days,
                )
            )
        write_exclusive(arguments.output, package)
    print(
        json.dumps(
            {
                "requirements_id": package.requirements_id,
                "status": "passed-network-free",
                "history_count": package.discovery_history_count,
                "requirement_count": package.requirement_count,
                "content_sha256": package.content_sha256,
                "provider_calls": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
