#!/usr/bin/env python3
"""Resolve the sealed Program 011 10,000+1,000 package without trusting the disk.

The package is ignored output. It therefore cannot be anchored by the working
tree. It is anchored instead by a two-level hash chain that starts inside git:

    research/05_evaluation/records/course-digital-twin-evaluation-program-011.json
      -> ignored_artifacts.construction_result_sha256
        -> construction-result.json
          -> packages[*].sha256
            -> the five sealed files

Nothing here writes to the package root, so the resolver is safe to point at a
directory owned by another worktree.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationCaseV1,
)


SEALED_ROOT_ENVIRONMENT_VARIABLE = "SEALED_PACKAGE_ROOT"
PROGRAM_011_RECORD = (
    ROOT
    / "research/05_evaluation/records/course-digital-twin-evaluation-program-011.json"
)
CONSTRUCTION_RESULT_NAME = "construction-result.json"
PACKAGE_NAMES = {
    "public_cases": "final-public-cases.json",
    "control_cases": "control-public-cases.json",
    "hidden_gold": "final-hidden-gold.json",
    "control_gold": "control-hidden-gold.json",
    "source_corpus": "final-source-corpus.json",
}
EXPECTED_PUBLIC_CASE_COUNT = 10_000
EXPECTED_CONTROL_CASE_COUNT = 1_000


class SealedPackageError(RuntimeError):
    """Raised when the sealed package cannot be proven to be the frozen one."""


@dataclass(frozen=True)
class CompletionReceiptV1:
    """Evidence that one response ledger reached a durable, complete state."""

    ledger_id: str
    status: str
    response_count: int
    expected_count: int

    @property
    def durable(self) -> bool:
        return (
            self.status == "completed"
            and self.expected_count > 0
            and self.response_count == self.expected_count
        )


def completion_receipt(
    ledger_id: str,
    snapshot: Mapping[str, Any],
    *,
    expected_count: int,
) -> CompletionReceiptV1:
    """Build a receipt from a ResponseLedgerV1 snapshot."""

    return CompletionReceiptV1(
        ledger_id=ledger_id,
        status=str(snapshot.get("status", "")),
        response_count=int(snapshot.get("response_count", 0)),
        expected_count=expected_count,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class SealedPackageV1:
    """A verified, read-only view of the frozen 10,000+1,000 package."""

    root: Path
    construction_sha256: str
    package_sha256: Mapping[str, str]

    def _path(self, name: str) -> Path:
        return self.root / PACKAGE_NAMES[name]

    def _load(self, name: str) -> dict[str, Any]:
        return json.loads(self._path(name).read_text(encoding="utf-8"))

    def _cases(self, name: str, *, expected_count: int | None) -> list[EvaluationCaseV1]:
        payload = self._load(name)
        rows = payload.get("cases")
        if not isinstance(rows, list) or not rows:
            raise SealedPackageError(f"{name} contains no cases")
        declared = payload.get("case_count")
        if declared is not None and int(declared) != len(rows):
            raise SealedPackageError(f"{name} case_count disagrees with its cases")
        if expected_count is not None and len(rows) != expected_count:
            raise SealedPackageError(
                f"{name} holds {len(rows)} cases, expected {expected_count}"
            )
        cases = [EvaluationCaseV1.model_validate(row) for row in rows]
        identifiers = {row.case_id for row in cases}
        if len(identifiers) != len(cases):
            raise SealedPackageError(f"{name} contains duplicate case IDs")
        return cases

    def public_cases(self, *, strict_count: bool = False) -> list[EvaluationCaseV1]:
        """Return the 10,000 candidate cases. Course ID and question only."""

        return self._cases(
            "public_cases",
            expected_count=EXPECTED_PUBLIC_CASE_COUNT if strict_count else None,
        )

    def control_cases(self, *, strict_count: bool = False) -> list[EvaluationCaseV1]:
        """Return the frozen 1,000 paired control cases."""

        return self._cases(
            "control_cases",
            expected_count=EXPECTED_CONTROL_CASE_COUNT if strict_count else None,
        )

    def declared_content_sha256(self, name: str) -> str:
        """Return the package's own declared content hash.

        The registered scorer binds a response ledger to this value, not to a
        hash recomputed over the parsed cases, so a ledger must be created with
        it or the run cannot be scored.
        """

        value = self._load(name).get("content_sha256")
        if not isinstance(value, str) or not value:
            raise SealedPackageError(f"{name} declares no content_sha256")
        return value

    def source_corpus(self) -> dict[str, Any]:
        """Return the public source corpus. This carries no gold."""

        return self._load("source_corpus")

    def _open_gold(self, name: str, receipts: Sequence[CompletionReceiptV1]) -> dict[str, Any]:
        if not receipts:
            raise SealedPackageError(
                "hidden gold requires at least one completion receipt"
            )
        pending = [row.ledger_id for row in receipts if not row.durable]
        if pending:
            raise SealedPackageError(
                "hidden gold stays sealed until every response is durable; "
                f"not durable: {', '.join(sorted(pending))}"
            )
        return self._load(name)

    def hidden_gold(self, *, receipts: Sequence[CompletionReceiptV1]) -> dict[str, Any]:
        """Open the candidate gold. Only legal after all responses are durable."""

        return self._open_gold("hidden_gold", receipts)

    def control_gold(self, *, receipts: Sequence[CompletionReceiptV1]) -> dict[str, Any]:
        """Open the control gold. Only legal after all responses are durable."""

        return self._open_gold("control_gold", receipts)

    def provenance(self) -> dict[str, Any]:
        """Return the hashes a result record must carry for this package."""

        return {
            "sealed_package_root": str(self.root),
            "construction_result_sha256": self.construction_sha256,
            "package_sha256": dict(sorted(self.package_sha256.items())),
        }


def default_sealed_root() -> Path | None:
    value = os.getenv(SEALED_ROOT_ENVIRONMENT_VARIABLE)
    return Path(value).expanduser().resolve() if value else None


def resolve_sealed_package(
    *,
    root: Path | None = None,
    record_path: Path | None = None,
) -> SealedPackageV1:
    """Verify and return the sealed package, or refuse to hand anything back."""

    resolved = root if root is not None else default_sealed_root()
    if resolved is None:
        raise SealedPackageError(
            "sealed package root is unset; export "
            f"{SEALED_ROOT_ENVIRONMENT_VARIABLE} to the Program 011 "
            "final-construction-10000 directory"
        )
    resolved = Path(resolved)
    if not resolved.is_dir():
        raise SealedPackageError(f"sealed package root is not a directory: {resolved}")

    record_file = record_path or PROGRAM_011_RECORD
    if not record_file.is_file():
        raise SealedPackageError(f"committed program record is missing: {record_file}")
    record = json.loads(record_file.read_text(encoding="utf-8"))
    expected_construction = str(
        record.get("ignored_artifacts", {}).get("construction_result_sha256", "")
    )
    if not expected_construction:
        raise SealedPackageError(
            "committed program record carries no construction_result_sha256"
        )

    construction_path = resolved / CONSTRUCTION_RESULT_NAME
    if not construction_path.is_file():
        raise SealedPackageError(
            f"sealed package root has no {CONSTRUCTION_RESULT_NAME}: {resolved}"
        )
    construction_sha = _sha256(construction_path)
    if construction_sha != expected_construction:
        raise SealedPackageError(
            "construction result sha256 does not match the committed record: "
            f"{construction_sha} != {expected_construction}"
        )

    construction = json.loads(construction_path.read_text(encoding="utf-8"))
    declared = construction.get("packages")
    if not isinstance(declared, dict):
        raise SealedPackageError("construction result declares no packages")
    missing = set(PACKAGE_NAMES) - set(declared)
    if missing:
        raise SealedPackageError(
            f"construction result is missing packages: {', '.join(sorted(missing))}"
        )

    verified: dict[str, str] = {}
    for name, filename in sorted(PACKAGE_NAMES.items()):
        expected = str(declared[name].get("sha256", ""))
        path = resolved / filename
        if not path.is_file():
            raise SealedPackageError(f"sealed package file is missing: {path}")
        actual = _sha256(path)
        if actual != expected:
            raise SealedPackageError(
                f"package file sha256 does not match the construction result for "
                f"{name}: {actual} != {expected}"
            )
        verified[name] = actual

    return SealedPackageV1(
        root=resolved,
        construction_sha256=construction_sha,
        package_sha256=verified,
    )


def _summarize(package: SealedPackageV1) -> dict[str, Any]:
    candidate = package.public_cases()
    control = package.control_cases()
    control_ids = {row.case_id for row in control}
    candidate_ids = {row.case_id for row in candidate}
    return {
        **package.provenance(),
        "public_case_count": len(candidate),
        "control_case_count": len(control),
        "control_is_paired_subset": control_ids <= candidate_ids,
        "course_ids": sorted({row.course_id for row in candidate}),
        "hidden_gold_opened": False,
    }


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    package = resolve_sealed_package(root=arguments.root)
    print(json.dumps(_summarize(package), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
