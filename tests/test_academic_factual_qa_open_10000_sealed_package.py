"""The sealed 10,000+1,000 package must verify before it can be read."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import academic_factual_qa_open_10000_sealed_package as sealed


def _write(path: Path, payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    path.write_text(serialized, encoding="utf-8")
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _case(case_id: str, course_id: str = "computer-networking") -> dict[str, object]:
    return {
        "schema_version": 1,
        "case_id": case_id,
        "cluster_id": case_id.rsplit("-", 1)[0],
        "source_family_id": "0123456789abcdef01234567",
        "course_id": course_id,
        "question": f"What does the source state about {case_id}?",
        "split": "final",
        "slice": "direct-factual",
        "author_family": "deterministic-canonical-fallback-v1",
    }


@pytest.fixture()
def sealed_root(tmp_path: Path) -> Path:
    """Build a miniature package with the real two-level hash structure."""

    root = tmp_path / "final-construction-10000"
    root.mkdir()
    hashes = {
        "public_cases": _write(
            root / "final-public-cases.json",
            {
                "schema_version": 1,
                "split": "final",
                "case_count": 2,
                "cases": [_case("academic-open-final-00001-q1"), _case("academic-open-final-00002-q1")],
            },
        ),
        "control_cases": _write(
            root / "control-public-cases.json",
            {
                "schema_version": 1,
                "split": "final-control",
                "case_count": 1,
                "cases": [_case("academic-open-final-00002-q1")],
            },
        ),
        "hidden_gold": _write(
            root / "final-hidden-gold.json",
            {"schema_version": 1, "gold": [{"case_id": "academic-open-final-00001-q1"}]},
        ),
        "control_gold": _write(
            root / "control-hidden-gold.json",
            {"schema_version": 1, "gold": [{"case_id": "academic-open-final-00002-q1"}]},
        ),
        "source_corpus": _write(
            root / "final-source-corpus.json",
            {"schema_version": 1, "sources": []},
        ),
    }
    names = {
        "public_cases": "final-public-cases.json",
        "control_cases": "control-public-cases.json",
        "hidden_gold": "final-hidden-gold.json",
        "control_gold": "control-hidden-gold.json",
        "source_corpus": "final-source-corpus.json",
    }
    construction_sha = _write(
        root / "construction-result.json",
        {
            "program_id": "course-digital-twin-evaluation-program-011",
            "stage": "final-construction-10000",
            "packages": {
                key: {"path": f"stages/final-construction-10000/{names[key]}", "sha256": value}
                for key, value in hashes.items()
            },
        },
    )
    record = tmp_path / "program-011.json"
    record.write_text(
        json.dumps(
            {
                "run_id": "course-digital-twin-evaluation-program-011",
                "ignored_artifacts": {"construction_result_sha256": construction_sha},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "record-path").write_text(str(record), encoding="utf-8")
    return root


def _resolve(sealed_root: Path) -> sealed.SealedPackageV1:
    record = Path((sealed_root.parent / "record-path").read_text(encoding="utf-8"))
    return sealed.resolve_sealed_package(root=sealed_root, record_path=record)


def test_resolve_verifies_the_chain_of_custody(sealed_root: Path) -> None:
    package = _resolve(sealed_root)

    assert package.root == sealed_root
    assert set(package.package_sha256) == {
        "public_cases",
        "control_cases",
        "hidden_gold",
        "control_gold",
        "source_corpus",
    }


def test_public_cases_parse_into_the_evaluation_contract(sealed_root: Path) -> None:
    package = _resolve(sealed_root)

    cases = package.public_cases()
    control = package.control_cases()

    assert [row.case_id for row in cases] == [
        "academic-open-final-00001-q1",
        "academic-open-final-00002-q1",
    ]
    assert [row.case_id for row in control] == ["academic-open-final-00002-q1"]
    assert {row.case_id for row in control} <= {row.case_id for row in cases}


def test_a_tampered_package_file_is_refused(sealed_root: Path) -> None:
    (sealed_root / "final-public-cases.json").write_text("{}", encoding="utf-8")

    with pytest.raises(sealed.SealedPackageError, match="package file sha256"):
        _resolve(sealed_root)


def test_a_tampered_construction_result_is_refused(sealed_root: Path) -> None:
    path = sealed_root / "construction-result.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["stage"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(sealed.SealedPackageError, match="construction result sha256"):
        _resolve(sealed_root)


def test_a_missing_root_is_refused(tmp_path: Path) -> None:
    with pytest.raises(sealed.SealedPackageError, match="sealed package root"):
        sealed.resolve_sealed_package(root=tmp_path / "absent")


def test_hidden_gold_stays_shut_until_every_ledger_is_complete(sealed_root: Path) -> None:
    package = _resolve(sealed_root)
    incomplete = sealed.CompletionReceiptV1(
        ledger_id="candidate-deterministic",
        status="running",
        response_count=1,
        expected_count=2,
    )

    with pytest.raises(sealed.SealedPackageError, match="hidden gold"):
        package.hidden_gold(receipts=[incomplete])


def test_hidden_gold_opens_once_responses_are_durable(sealed_root: Path) -> None:
    package = _resolve(sealed_root)
    receipts = [
        sealed.CompletionReceiptV1(
            ledger_id="candidate-deterministic",
            status="completed",
            response_count=2,
            expected_count=2,
        ),
        sealed.CompletionReceiptV1(
            ledger_id="control",
            status="completed",
            response_count=1,
            expected_count=1,
        ),
    ]

    gold = package.hidden_gold(receipts=receipts)
    control_gold = package.control_gold(receipts=receipts)

    assert gold["gold"][0]["case_id"] == "academic-open-final-00001-q1"
    assert control_gold["gold"][0]["case_id"] == "academic-open-final-00002-q1"


def test_a_receipt_whose_count_falls_short_is_refused(sealed_root: Path) -> None:
    package = _resolve(sealed_root)
    short = sealed.CompletionReceiptV1(
        ledger_id="candidate-deterministic",
        status="completed",
        response_count=1,
        expected_count=2,
    )

    with pytest.raises(sealed.SealedPackageError, match="hidden gold"):
        package.hidden_gold(receipts=[short])


def test_receipts_must_not_be_empty(sealed_root: Path) -> None:
    package = _resolve(sealed_root)

    with pytest.raises(sealed.SealedPackageError, match="hidden gold"):
        package.hidden_gold(receipts=[])
