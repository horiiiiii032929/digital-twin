from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from scripts.build_academic_factual_qa_confirmation_v2 import (
    ANSWERABLE_ALLOCATION,
    BOUNDARY_SEQUENCE,
    CASES_PATH,
    CONTROLS_PATH,
    MANIFEST_PATH,
    canonical_sha256,
    validate_artifacts,
)


def _load() -> tuple[dict, dict, dict]:
    return tuple(
        json.loads(path.read_text(encoding="utf-8"))
        for path in (MANIFEST_PATH, CASES_PATH, CONTROLS_PATH)
    )  # type: ignore[return-value]


def test_committed_artifacts_validate_without_private_or_provider_state() -> None:
    manifest, dataset, controls = _load()
    validate_artifacts(manifest, dataset, controls)
    assert manifest["private_data"] is False
    assert manifest["academia_vault_used"] is False
    assert manifest["full_raw_source_artifacts_committed"] is False
    assert dataset["claim_level"] == "deterministic-source-derived-unreviewed"


def test_content_hashes_bind_every_artifact() -> None:
    for payload in _load():
        recorded = payload["content_sha256"]
        unhashed = {key: value for key, value in payload.items() if key != "content_sha256"}
        assert recorded == canonical_sha256(unhashed)


def test_source_manifest_pins_four_collections_and_unique_sections() -> None:
    manifest, _, _ = _load()
    expected_commits = {
        "operating-systems": "25cac6dfb7bca4335337ea81866899e2f61213d6",
        "computer-networking": "5d270364790500fe58283be91329365835a69d66",
        "data-structures": "9d22c44906dda2017b2ef0c762025bee644b58aa",
        "python-programming": "19cb35f68cf4c964d20e08c4647e251e8ec63743",
    }
    collections = {row["course_id"]: row for row in manifest["collections"]}
    assert set(collections) == set(expected_commits)
    for course_id, commit in expected_commits.items():
        row = collections[course_id]
        assert row["commit"] == row["local_snapshot_head"] == commit
        assert row["license_spdx"]
        assert row["license_evidence"]
        assert row["raw_snapshot_committed"] is False
    assert Counter(row["course_id"] for row in manifest["sources"]) == Counter(
        {course_id: 40 for course_id in expected_commits}
    )
    assert len({row["source_id"] for row in manifest["sources"]}) == 160
    assert len({row["source_family_id"] for row in manifest["sources"]}) == 160
    assert all(len(row["file_sha256"]) == len(row["section_sha256"]) == 64 for row in manifest["sources"])


def test_selected_source_ranges_do_not_overlap() -> None:
    manifest, _, _ = _load()
    by_file: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for source in manifest["sources"]:
        by_file[(source["course_id"], source["path"])].append(source)
    for rows in by_file.values():
        ordered = sorted(rows, key=lambda row: row["section_char_start"])
        for left, right in zip(ordered, ordered[1:]):
            assert left["section_char_end"] <= right["section_char_start"]


def test_no_local_paths_credentials_or_student_records_are_committed() -> None:
    serialized = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (MANIFEST_PATH, CASES_PATH, CONTROLS_PATH)
    )
    assert "/Users/" not in serialized
    assert "Academia Vault" not in serialized
    assert "api_key" not in serialized.lower()
    assert "student_id" not in serialized.lower()


def test_confirmation_has_exact_course_cluster_and_slice_allocation() -> None:
    _, dataset, _ = _load()
    cases = dataset["cases"]
    answerable = [row for row in cases if row["expected_action"] == "answer"]
    boundary = [row for row in cases if row["expected_action"] != "answer"]
    assert len(cases) == 200
    assert len(answerable) == len(boundary) == 100
    assert Counter(row["course_id"] for row in answerable) == Counter(
        {course_id: 25 for course_id in ANSWERABLE_ALLOCATION}
    )
    assert Counter(row["slice"] for row in answerable) == Counter(
        {
            slice_name: sum(allocation[slice_name] for allocation in ANSWERABLE_ALLOCATION.values())
            for slice_name in next(iter(ANSWERABLE_ALLOCATION.values()))
        }
    )
    assert Counter(row["slice"] for row in boundary) == Counter(BOUNDARY_SEQUENCE)
    assert Counter(row["cluster_id"] for row in cases) == Counter(
        {f"afqc002-cluster-{index:03d}": 2 for index in range(1, 101)}
    )


def test_answerable_truth_is_exact_source_linked_and_boundary_lineage_is_empty() -> None:
    manifest, dataset, _ = _load()
    sources = {row["source_id"]: row for row in manifest["sources"]}
    for case in dataset["cases"]:
        if case["expected_action"] == "answer":
            assert case["label_provenance"] == "deterministic-exact-source-excerpt"
            assert case["required_source_ids"]
            assert case["evidence"]
            assert case["atomic_claims"]
            assert set(case["required_source_ids"]) == {
                evidence["source_id"] for evidence in case["evidence"]
            }
            for evidence in case["evidence"]:
                assert sources[evidence["source_id"]]["purpose"] == "confirmation"
                assert hashlib.sha256(evidence["quote"].encode()).hexdigest() == evidence["quote_sha256"]
                assert len(evidence["quote"]) >= 80
            assert case["canonical_answer"] == " ".join(
                evidence["quote"] for evidence in case["evidence"]
            )
        else:
            assert case["label_provenance"] == "deterministic-boundary-transform"
            assert case["required_source_ids"] == []
            assert case["evidence"] == []
            assert case["atomic_claims"] == []
            assert case["boundary_transform"]["lineage_forced_empty"] is True


def test_multimodal_cases_are_bound_to_matching_source_metadata() -> None:
    manifest, dataset, _ = _load()
    sources = {row["source_id"]: row for row in manifest["sources"]}
    for case in dataset["cases"]:
        if case["slice"] in {"code", "table", "diagram", "equation"}:
            assert case["expected_action"] == "answer"
            assert all(
                case["slice"] in sources[source_id]["modalities"]
                for source_id in case["required_source_ids"]
            )
    diagram_sources = [
        sources[case["required_source_ids"][0]]
        for case in dataset["cases"]
        if case["slice"] == "diagram"
    ]
    assert any(source["dependent_assets"] for source in diagram_sources)
    assert all(
        len(asset["sha256"]) == 64
        for source in manifest["sources"]
        for asset in source["dependent_assets"]
    )
    asset_hashes = [
        asset["sha256"]
        for source in manifest["sources"]
        for asset in source["dependent_assets"]
    ]
    assert len(asset_hashes) == len(set(asset_hashes))
    assert sum(bool(source["dependent_assets"]) for source in diagram_sources) == 9


def test_questions_are_exactly_unique_after_normalization() -> None:
    _, dataset, _ = _load()
    normalized = [
        " ".join(re.findall(r"[a-z0-9]+", row["question"].lower()))
        for row in dataset["cases"]
    ]
    assert len(normalized) == len(set(normalized)) == 200


def test_calibration_controls_are_disjoint_balanced_and_planted() -> None:
    manifest, dataset, calibration = _load()
    confirmation_sources = {
        source_id for case in dataset["cases"] for source_id in case["required_source_ids"]
    }
    control_sources = {row["source_id"] for row in calibration["controls"]}
    assert not confirmation_sources & control_sources
    assert Counter(row["is_clean"] for row in calibration["controls"]) == Counter(
        {True: 20, False: 20}
    )
    assert Counter(
        row["planted_mutation"]
        for row in calibration["controls"]
        if not row["is_clean"]
    ) == Counter(
        {"action": 4, "claim": 4, "citation": 4, "ambiguity": 4, "boundary": 4}
    )
    source_map = {row["source_id"]: row for row in manifest["sources"]}
    assert all(source_map[source_id]["purpose"] == "calibration" for source_id in control_sources)
    assert all(row["label_provenance"] == "deterministic-planted-control" for row in calibration["controls"])
