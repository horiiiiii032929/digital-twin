"""Archive transformations must retain provenance and exclude credentials."""

import gzip
import json
import sqlite3

from scripts import build_professor_evidence as archive


def catalog():
    connection = sqlite3.connect(":memory:")
    connection.executescript(archive.SCHEMA)
    connection.execute(
        "INSERT INTO files(file_id,original_path) VALUES ('f1','synthetic.json')"
    )
    return connection


def test_deduplication_preserves_distinct_record_locations():
    connection = catalog()
    archive.add_record(connection, "f1", "line:1", {"case_id": "a", "value": 0})
    archive.add_record(connection, "f1", "line:2", {"case_id": "a", "value": 0})
    assert connection.execute("SELECT count(*) FROM records").fetchone()[0] == 2
    assert connection.execute("SELECT count(*) FROM payloads").fetchone()[0] == 1
    assert connection.execute("SELECT count(*) FROM case_records").fetchone()[0] == 2


def test_json_index_retains_root_and_explicit_array_grain():
    connection = catalog()
    archive.ingest_json(
        connection, "f1", {"cases": [{"case_id": "a"}, {"case_id": "b"}]}
    )
    assert connection.execute(
        "SELECT locator FROM records ORDER BY locator"
    ).fetchall() == [("$",), ("$.cases[0]",), ("$.cases[1]",)]


def test_sqlite_export_excludes_authentication_and_preserves_blob(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(archive, "BUILD", tmp_path)
    source = tmp_path / "source.sqlite"
    original = sqlite3.connect(source)
    original.executescript(
        "CREATE TABLE identity_credentials(email TEXT, password_hash TEXT);"
        "CREATE TABLE responses(case_id TEXT,payload_json TEXT,binary BLOB);"
    )
    original.execute(
        "INSERT INTO identity_credentials VALUES (?,?)",
        ("private@example.test", "secret-hash"),
    )
    original.execute(
        "INSERT INTO responses VALUES (?,?,?)",
        ("case-a", '{"case_id":"case-a","answer":"saved"}', b"\x00\x01"),
    )
    original.commit()
    original.close()
    connection = catalog()
    out = tmp_path / "safe.sqlite.gz"
    archive.sqlite_export(connection, "f1", source, out)
    restored = tmp_path / "restored.sqlite"
    restored.write_bytes(gzip.decompress(out.read_bytes()))
    clean = sqlite3.connect(restored)
    assert (
        clean.execute(
            "SELECT name FROM sqlite_master WHERE name='identity_credentials'"
        ).fetchall()
        == []
    )
    assert clean.execute("SELECT binary FROM responses").fetchone()[0] == b"\x00\x01"
    assert connection.execute("SELECT row_count FROM exclusions").fetchone()[0] == 1
    response = json.loads(
        connection.execute(
            "SELECT payload_json FROM json_records WHERE locator='table:responses/payload:0'"
        ).fetchone()[0]
    )
    assert response == {"case_id": "case-a", "answer": "saved"}


def test_vault_root_is_not_traversed_from_permission_document(tmp_path):
    permission = tmp_path / "permission.md"
    permission.write_text("Canonical source: `/Users/hikaru/Documents/academia_vault`.")
    assert archive.refs(permission) == []


def test_secret_pattern_does_not_remove_high_risk_metric_names():
    assert archive.SECRET.search("high-risk-boundary-action-correctness") is None
    assert archive.SECRET.search("token: sk-" + "a" * 32) is not None
