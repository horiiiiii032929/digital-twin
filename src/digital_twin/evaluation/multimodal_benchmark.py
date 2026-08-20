"""Multimodal benchmark split, seal, and development-only loading rules."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SPLIT_SEED = "multimodal-retrieval-v1-split-v1"
SEAL_ID = "multimodal-retrieval-v1-seal"
DEVELOPMENT_CASES = 16
HELDOUT_CASES = 24
DEVELOPMENT_SLICE_TARGETS = {
    "visual_answerable": 10,
    "text_control": 3,
    "no_evidence": 1,
    "adversarial_integrity": 2,
}


class MultimodalSealError(ValueError):
    """Raised when a multimodal split or seal violates the frozen contract."""


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _group_order(asset_id: str, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{asset_id}".encode()).hexdigest()


def choose_development_assets(
    dataset: dict[str, Any],
    *,
    development_cases: int = DEVELOPMENT_CASES,
    slice_targets: dict[str, int] = DEVELOPMENT_SLICE_TARGETS,
    seed: str = SPLIT_SEED,
) -> frozenset[str]:
    """Choose an exact deterministic split while keeping page cases together."""
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in dataset["cases"]:
        grouped[case["asset_id"]].append(case)
    groups = sorted(grouped.items(), key=lambda item: _group_order(item[0], seed))
    suffix_cases = [0] * (len(groups) + 1)
    for index in range(len(groups) - 1, -1, -1):
        suffix_cases[index] = suffix_cases[index + 1] + len(groups[index][1])

    target = Counter(slice_targets)
    best: tuple[tuple[Any, ...], frozenset[str]] | None = None

    def search(
        index: int,
        selected_assets: tuple[str, ...],
        selected_cases: tuple[dict[str, Any], ...],
        counts: Counter[str],
    ) -> None:
        nonlocal best
        total = len(selected_cases)
        if total > development_cases or total + suffix_cases[index] < development_cases:
            return
        if any(counts[name] > expected for name, expected in target.items()):
            return
        if index == len(groups):
            if total != development_cases or counts != target:
                return
            courses = Counter(
                assets[case["asset_id"]]["course_id"] for case in selected_cases
            )
            modalities = {
                case["modality"]
                for case in selected_cases
                if case["slice"] == "visual_answerable"
            }
            tie_break = hashlib.sha256("|".join(selected_assets).encode()).hexdigest()
            score = (
                len(courses),
                len(modalities),
                -max(courses.values()),
                tie_break,
            )
            candidate = (score, frozenset(selected_assets))
            if best is None or candidate[0] > best[0]:
                best = candidate
            return

        asset_id, cases = groups[index]
        delta = Counter(case["slice"] for case in cases)
        search(
            index + 1,
            selected_assets + (asset_id,),
            selected_cases + tuple(cases),
            counts + delta,
        )
        search(index + 1, selected_assets, selected_cases, counts)

    search(0, (), (), Counter())
    if best is None:
        raise MultimodalSealError(
            "no asset-grouped split satisfies the development targets"
        )
    return best[1]


def partition_dataset(
    dataset: dict[str, Any],
    *,
    development_assets: frozenset[str],
    development: bool,
) -> dict[str, Any]:
    """Create one sealed partition and retain only its referenced assets."""
    if not isinstance(development, bool):
        raise ValueError("development must be a boolean")
    known_assets = {asset["asset_id"] for asset in dataset["source_assets"]}
    if not development_assets <= known_assets:
        raise MultimodalSealError("development split references an unknown asset")
    partition = copy.deepcopy(dataset)
    partition["dataset_status"] = "sealed"
    split = "development" if development else "heldout_draft"
    partition["cases"] = [
        case
        for case in partition["cases"]
        if (case["asset_id"] in development_assets) is development
    ]
    for case in partition["cases"]:
        case["split"] = split
    retained_assets = {case["asset_id"] for case in partition["cases"]}
    partition["source_assets"] = [
        asset
        for asset in partition["source_assets"]
        if asset["asset_id"] in retained_assets
    ]
    return partition


def load_sealed_development(
    *, root: Path, seal_path: Path, ledger_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load development and ledger metadata without reading the held-out file."""
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if seal.get("seal_id") != SEAL_ID:
        raise MultimodalSealError("unexpected multimodal seal ID")
    if seal.get("heldout_access_allowed") is not False:
        raise MultimodalSealError("held-out access must remain disabled")
    if seal.get("heldout_status") != "unopened":
        raise MultimodalSealError("seal does not report unopened held-out data")
    if ledger.get("seal_id") != SEAL_ID:
        raise MultimodalSealError("held-out ledger seal mismatch")
    if ledger.get("heldout_sha256") != seal.get("heldout_sha256"):
        raise MultimodalSealError("held-out ledger hash mismatch")
    if ledger.get("status") != "unopened" or ledger.get("attempts"):
        raise MultimodalSealError("held-out ledger is not pristine")
    if sha256_file(ledger_path) != seal.get("initial_heldout_access_ledger_sha256"):
        raise MultimodalSealError("held-out ledger file hash mismatch")

    development_path = root / seal["development_path"]
    heldout_path = root / seal["heldout_path"]
    if not heldout_path.is_file():
        raise MultimodalSealError("sealed held-out file is absent")
    if sha256_file(development_path) != seal.get("development_sha256"):
        raise MultimodalSealError("sealed development file hash mismatch")
    dataset = json.loads(development_path.read_text(encoding="utf-8"))
    if dataset.get("dataset_status") != "sealed":
        raise MultimodalSealError("development dataset is not sealed")
    if len(dataset.get("cases", [])) != DEVELOPMENT_CASES:
        raise MultimodalSealError("development dataset must contain 16 cases")
    if any(case.get("split") != "development" for case in dataset["cases"]):
        raise MultimodalSealError("development dataset contains another split")
    if not all(
        case.get("review", {}).get("researcher_verified") is True
        for case in dataset["cases"]
    ):
        raise MultimodalSealError("development dataset contains unverified cases")
    return dataset, seal
