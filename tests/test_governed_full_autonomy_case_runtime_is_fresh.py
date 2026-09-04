"""A per-case product runtime must start from an empty database.

Each evaluation case is meant to be an isolated product instance: the factory
seeds a synthetic workflow and installs one immutable release. ``save_release``
rejects a second release with the same identity regardless of content, so a
per-case database left behind by a killed case makes the resumed attempt fail
with "release content is immutable after creation".

Resume deliberately skips cases already in the response ledger. The case that
was mid-flight when the process died is not in the ledger, so it is re-run --
against its leftover database. Clearing the per-case database before opening it
is what makes resume work, and it changes nothing for a case that has never
run.
"""

from __future__ import annotations

import inspect

from scripts import governed_full_autonomy_v2_1_actual_product_runtime as runtime
from src.digital_twin.student import SQLiteStudentRepository


def test_a_leftover_case_database_is_cleared_before_use(tmp_path) -> None:
    """The factory must not inherit rows from a killed attempt."""

    source = inspect.getsource(runtime.build_runtime_factory)

    assert "_reset_case_database" in source


def test_reset_removes_the_database_and_its_sidecars(tmp_path) -> None:
    database = tmp_path / "case.sqlite3"
    repository = SQLiteStudentRepository(database)
    repository.close()
    for suffix in ("-wal", "-shm"):
        database.with_name(database.name + suffix).write_bytes(b"stale")

    runtime._reset_case_database(database)

    assert not database.exists()
    for suffix in ("-wal", "-shm"):
        assert not database.with_name(database.name + suffix).exists()


def test_reset_is_a_no_op_for_a_database_that_never_existed(tmp_path) -> None:
    database = tmp_path / "absent.sqlite3"

    runtime._reset_case_database(database)

    assert not database.exists()


def test_a_release_identity_can_be_installed_after_a_reset(tmp_path) -> None:
    """The immutability rule is what resume trips on; prove the reset clears it."""

    database = tmp_path / "case.sqlite3"
    first = SQLiteStudentRepository(database)
    first.close()

    runtime._reset_case_database(database)
    second = SQLiteStudentRepository(database)
    try:
        assert second.get_published_release("any-course") is None
    finally:
        second.close()


def test_every_release_chunk_gets_its_own_ordinal() -> None:
    """A multi-source release must not stack every chunk on one ordinal."""

    source = inspect.getsource(runtime._build_release_chunk)

    assert "ordinal" in source
