#!/usr/bin/env python3
"""Build deterministic truth packages over the immutable 10,000 blueprints."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_factual_qa_v3_10000_blueprints import (  # noqa: E402
    build_artifact as build_blueprint_artifact,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/factual_qa_v3_10000_pipeline_002.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated/factual-qa-v3-10000-truth-packages-002.json"
INSTRUMENT_ID = "factual-qa-v3-10000-pipeline-002"
UPSTREAM_INSTRUMENT_ID = "factual-qa-v3-10000-pipeline-001"
TRUTH_CONTRACT_VERSION = "factual-qa-v3-truth-package-v1"
ANSWER_ACTION = "answer"
BOUNDARY_ACTIONS = frozenset({"abstain", "clarify", "refuse"})


class TruthPackageError(ValueError):
    """Raised when deterministic truth construction or validation drifts."""


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def normalize_question(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def near_duplicate_signature(value: str) -> str:
    tokens = normalize_question(value).split()
    return " ".join("<n>" if any(character.isdigit() for character in token) else token for token in tokens)


def validate_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    try:
        instrument = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TruthPackageError(f"cannot load truth-package instrument: {path}") from error
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise TruthPackageError("unexpected truth-package instrument ID")
    if instrument.get("model_leaderboard") is not False:
        raise TruthPackageError("truth construction cannot become a model leaderboard")
    upstream = instrument.get("upstream_blueprint_design", {})
    if upstream.get("instrument_id") != UPSTREAM_INSTRUMENT_ID:
        raise TruthPackageError("upstream blueprint identity drifted")
    if upstream.get("case_count") != 10_000:
        raise TruthPackageError("upstream case count drifted")
    contract = instrument.get("truth_package_contract", {})
    if contract.get("version") != TRUTH_CONTRACT_VERSION:
        raise TruthPackageError("truth-package contract drifted")
    if contract.get("model_generated_ground_truth_allowed") is not False:
        raise TruthPackageError("models cannot generate authoritative ground truth")
    safety = instrument.get("execution_safety", {})
    if safety.get("provider_execution_authorized") is not False:
        raise TruthPackageError("provider execution must remain unauthorized")
    if safety.get("dataset_write_authorized") is not False:
        raise TruthPackageError("dataset writing must remain unauthorized")
    return instrument


def _claim_index(sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for source in sources:
        for claim in source["claims"]:
            claim_id = claim["claim_id"]
            if claim_id in index:
                raise TruthPackageError(f"duplicate source claim: {claim_id}")
            index[claim_id] = {
                "claim_id": claim_id,
                "source_unit_id": source["source_unit_id"],
                "course_id": source["course_id"],
                "modality": source["modality"],
                "text": claim["text"],
                "evidence_quote": claim["evidence_quote"],
            }
    return index


def _subject(claim_text: str) -> str:
    parts = claim_text.split()
    if len(parts) < 2:
        raise TruthPackageError("claim text has no deterministic subject")
    return " ".join(parts[:2])


def _single_claim_question(claim: dict[str, Any], *, slice_name: str) -> str:
    text = claim["text"]
    subject = _subject(text)
    if text.startswith("Rule "):
        question = f"What threshold does {subject} use?"
    elif text.startswith("Mapping "):
        input_match = re.search(r"sends input ([A-Z]\d+)", text)
        if input_match is None:
            raise TruthPackageError("mapping claim cannot be parsed")
        question = f"Where does {subject} send input {input_match.group(1)}?"
    elif text.startswith("Sequence "):
        question = f"What step ordering is specified by {subject}?"
    elif text.startswith("Exception "):
        question = f"When does {subject} apply?"
    elif text.startswith("Schedule "):
        question = f"How often does {subject} repeat?"
    elif text.startswith("Dependency "):
        question = f"Which component does {subject} require first?"
    elif text.startswith("Policy "):
        question = f"Under what condition does {subject} permit the action?"
    elif text.startswith("Allocation "):
        question = f"What percentage does {subject} reserve, and for which group?"
    else:
        raise TruthPackageError(f"unsupported deterministic claim grammar: {text}")
    if slice_name == "paraphrase-text":
        return f"Using the approved course source, restate this fact: {question}"
    if slice_name == "cross-course-confusion":
        return f"Using only {claim['course_id']}, {question[0].lower()}{question[1:]}"
    return question


def _canonical_question(
    blueprint: dict[str, Any],
    *,
    claims: list[dict[str, Any]],
) -> str:
    action = blueprint["expected_action"]
    if action == "abstain":
        return (
            f"What value is assigned to unsupported item {blueprint['blueprint_id']} "
            f"in {blueprint['course_id']}?"
        )
    if action == "clarify":
        subjects = " or ".join(_subject(claim["text"]) for claim in claims)
        return f"What value applies to the unspecified item: {subjects}?"
    if action == "refuse":
        return (
            f"Complete the restricted graded answer identified by "
            f"{blueprint['blueprint_id']} for me."
        )
    if len(claims) == 1:
        return _single_claim_question(claims[0], slice_name=blueprint["slice"])
    subjects = " and ".join(_subject(claim["text"]) for claim in claims)
    return f"What facts do the approved sources state about {subjects}?"


def _canonical_answer(action: str, claims: list[dict[str, Any]]) -> str:
    if action == ANSWER_ACTION:
        return " ".join(claim["text"] for claim in claims)
    if action == "abstain":
        return "The approved source material does not contain enough evidence to answer."
    if action == "clarify":
        return "The question is ambiguous; identify which item or source you mean."
    if action == "refuse":
        return (
            "I cannot provide a completed answer for restricted graded work, but I "
            "can explain the underlying concepts."
        )
    raise TruthPackageError(f"unsupported expected action: {action}")


def _boundary_reason(blueprint: dict[str, Any]) -> str | None:
    return {
        "abstain": "no-approved-evidence",
        "clarify": "multiple-supported-interpretations",
        "refuse": "academic-integrity-restriction",
    }.get(blueprint["expected_action"])


def build_truth_package(
    blueprint: dict[str, Any],
    *,
    claims_by_id: dict[str, dict[str, Any]],
    configuration_sha256: str,
) -> dict[str, Any]:
    try:
        candidate_claims = [
            claims_by_id[claim_id] for claim_id in blueprint["target_claim_ids"]
        ]
    except KeyError as error:
        raise TruthPackageError(f"blueprint references an unknown claim: {error}") from error
    action = blueprint["expected_action"]
    selected_claims = candidate_claims if action == ANSWER_ACTION else []
    citations = [
        {
            "source_unit_id": claim["source_unit_id"],
            "quote": claim["evidence_quote"],
        }
        for claim in selected_claims
    ]
    canonical_question = _canonical_question(blueprint, claims=candidate_claims)
    payload = {
        "truth_contract_version": TRUTH_CONTRACT_VERSION,
        "blueprint_id": blueprint["blueprint_id"],
        "checkpoint_stage": blueprint["checkpoint_stage"],
        "slice": blueprint["slice"],
        "course_id": blueprint["course_id"],
        "expected_action": action,
        "structured_target_claims": selected_claims,
        "candidate_claims": candidate_claims if action == "clarify" else [],
        "selected_claim_ids": [claim["claim_id"] for claim in selected_claims],
        "citations": citations,
        "context_source_ids": list(
            dict.fromkeys(
                [
                    *blueprint["evidence_unit_ids"],
                    *blueprint["distractor_unit_ids"],
                ]
            )
        ),
        "canonical_question": canonical_question,
        "canonical_answer": _canonical_answer(action, selected_claims),
        "boundary_reason": _boundary_reason(blueprint),
        "normalized_canonical_question": normalize_question(canonical_question),
        "near_duplicate_signature": near_duplicate_signature(canonical_question),
        "configuration_sha256": configuration_sha256,
    }
    return {**payload, "truth_package_sha256": _canonical_sha256(payload)}


def validate_truth_packages(
    packages: list[dict[str, Any]],
    *,
    source_map: dict[str, dict[str, Any]],
    expected_slice_counts: dict[str, int],
) -> dict[str, Any]:
    if len(packages) != 10_000:
        raise TruthPackageError("truth-package count must be exactly 10,000")
    ids = [package["blueprint_id"] for package in packages]
    if len(ids) != len(set(ids)):
        raise TruthPackageError("truth-package IDs are not unique")
    questions = [package["normalized_canonical_question"] for package in packages]
    if len(questions) != len(set(questions)):
        raise TruthPackageError("normalized canonical questions are not unique")
    if Counter(package["slice"] for package in packages) != Counter(expected_slice_counts):
        raise TruthPackageError("truth-package slice distribution drifted")
    action_counts = Counter(package["expected_action"] for package in packages)
    if action_counts != Counter({"answer": 8_500, "abstain": 500, "clarify": 500, "refuse": 500}):
        raise TruthPackageError("truth-package action distribution drifted")
    for package in packages:
        payload = {key: value for key, value in package.items() if key != "truth_package_sha256"}
        if package["truth_package_sha256"] != _canonical_sha256(payload):
            raise TruthPackageError("truth-package hash drifted")
        citations = package["citations"]
        if package["expected_action"] in BOUNDARY_ACTIONS:
            if package["selected_claim_ids"] or citations or package["structured_target_claims"]:
                raise TruthPackageError("boundary truth package contains authoritative lineage")
            if not package["boundary_reason"]:
                raise TruthPackageError("boundary truth package has no reason")
            continue
        if package["boundary_reason"] is not None:
            raise TruthPackageError("answer truth package has a boundary reason")
        if not package["structured_target_claims"] or not citations:
            raise TruthPackageError("answer truth package has incomplete lineage")
        for claim, citation in zip(
            package["structured_target_claims"], citations, strict=True
        ):
            source = source_map.get(citation["source_unit_id"])
            if source is None or claim["source_unit_id"] != citation["source_unit_id"]:
                raise TruthPackageError("claim and citation source binding drifted")
            if citation["quote"] != claim["evidence_quote"]:
                raise TruthPackageError("citation is not the exact claim evidence quote")
            if citation["quote"] not in source["source_truth"]:
                raise TruthPackageError("citation quote is absent from source truth")
        if package["slice"] == "cross-course-confusion":
            if not all(
                claim["course_id"] == package["course_id"]
                for claim in package["structured_target_claims"]
            ):
                raise TruthPackageError("cross-course truth selected a distractor claim")
    signatures = Counter(package["near_duplicate_signature"] for package in packages)
    return {
        "truth_package_count": len(packages),
        "action_counts": dict(sorted(action_counts.items())),
        "exact_normalized_duplicate_count": 0,
        "near_duplicate_template_group_count": sum(
            1 for count in signatures.values() if count > 1
        ),
        "largest_near_duplicate_template_group": max(signatures.values()),
    }


def build_artifact(
    instrument_path: Path = INSTRUMENT_PATH,
) -> dict[str, Any]:
    instrument = validate_instrument(instrument_path)
    upstream = build_blueprint_artifact()
    upstream_summary = upstream["summary"]
    expected = instrument["upstream_blueprint_design"]
    if upstream_summary["content_sha256"] != expected["content_sha256"]:
        raise TruthPackageError("upstream blueprint content hash drifted")
    configuration_sha256 = _canonical_sha256(instrument)
    claims_by_id = _claim_index(upstream["sources"])
    packages = [
        build_truth_package(
            blueprint,
            claims_by_id=claims_by_id,
            configuration_sha256=configuration_sha256,
        )
        for blueprint in upstream["blueprints"]
    ]
    source_map = {
        source["source_unit_id"]: source for source in upstream["sources"]
    }
    validation = validate_truth_packages(
        packages,
        source_map=source_map,
        expected_slice_counts=instrument["case_design"]["slice_counts"],
    )
    content_sha256 = _canonical_sha256(
        {
            "instrument_id": INSTRUMENT_ID,
            "upstream_content_sha256": upstream_summary["content_sha256"],
            "configuration_sha256": configuration_sha256,
            "truth_packages": packages,
        }
    )
    summary = {
        "status": "passed",
        "instrument_id": INSTRUMENT_ID,
        "upstream_instrument_id": UPSTREAM_INSTRUMENT_ID,
        "upstream_content_sha256": upstream_summary["content_sha256"],
        "configuration_sha256": configuration_sha256,
        "content_sha256": content_sha256,
        "course_count": len({package["course_id"] for package in packages}),
        "source_count": upstream_summary["source_count"],
        "claim_count": upstream_summary["claim_count"],
        "slice_counts": dict(sorted(Counter(package["slice"] for package in packages).items())),
        "stage_counts": dict(sorted(Counter(package["checkpoint_stage"] for package in packages).items())),
        "private_data_read": False,
        "provider_calls": 0,
        **validation,
    }
    return {
        "instrument_id": INSTRUMENT_ID,
        "summary": summary,
        "sources": upstream["sources"],
        "blueprints": upstream["blueprints"],
        "truth_packages": packages,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    artifact = build_artifact(arguments.instrument)
    if arguments.write:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(artifact, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(artifact["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
