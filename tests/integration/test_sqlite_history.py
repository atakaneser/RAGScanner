import sqlite3
import stat
from pathlib import Path

import pytest
from ragscanner.storage import SQLiteScanHistoryRepository
from ragscanner.storage.database import StorageError
from sqlalchemy import text


def test_fresh_database_migrates_uses_wal_and_restrictive_permissions(tmp_path: Path) -> None:
    path = tmp_path / "private" / "history.sqlite3"

    repository = SQLiteScanHistoryRepository(path)
    try:
        with repository.engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
            foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
        assert revision == "0006_source_profile_kinds"
        assert journal_mode == "wal"
        assert foreign_keys == 1
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    finally:
        repository.close()


def test_existing_unversioned_database_is_backed_up_before_migration(tmp_path: Path) -> None:
    path = tmp_path / "history.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE legacy_marker (value TEXT)")
        connection.execute("INSERT INTO legacy_marker VALUES ('preserve-me')")

    repository = SQLiteScanHistoryRepository(path)
    repository.close()

    backups = list(tmp_path.glob("history.sqlite3.backup-*"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("SELECT value FROM legacy_marker").fetchone() == ("preserve-me",)


def test_corrupt_database_fails_without_exposing_database_details(tmp_path: Path) -> None:
    path = tmp_path / "history.sqlite3"
    path.write_bytes(b"not-a-sqlite-database")

    with pytest.raises(StorageError, match="local history database migration failed") as captured:
        SQLiteScanHistoryRepository(path)

    assert "not-a-sqlite-database" not in str(captured.value)


def test_repository_saves_lists_reads_and_deletes_immutable_reports(
    tmp_path: Path, report, finding
) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteScanHistoryRepository(tmp_path / "history.sqlite3")
    first = report("scan-1", findings=[finding("a")])
    second = report("scan-2", findings=[finding("b")], overall=70.0)
    try:
        first_history_id = repository.save(first)
        assert repository.save(first) == first_history_id
        second_history_id = repository.save(second)
        assert second_history_id != first_history_id

        page = repository.list(limit=1)
        assert page.total == 2
        assert len(page.items) == 1
        assert page.items[0].display_id == "RAGREP-0002"
        assert page.items[0].finding_count == 1
        assert repository.get(first_history_id) == first
        assert repository.get("missing") is None
        assert repository.delete(first_history_id)
        assert not repository.delete(first_history_id)
        assert repository.list().total == 1
    finally:
        repository.close()


def test_repeated_core_scan_identity_creates_distinct_execution_history(
    tmp_path: Path, report, finding
) -> None:  # type: ignore[no-untyped-def]
    repository = SQLiteScanHistoryRepository(tmp_path / "history.sqlite3")
    try:
        first = repository.save(report("scan-1", findings=[finding("a")]))
        second = repository.save(report("scan-1", findings=[finding("b")]))
        assert first != second
        assert repository.list().total == 2
        with repository.engine.connect() as connection:
            count = connection.execute(
                text("SELECT COUNT(*) FROM finding_occurrences")
            ).scalar_one()
        assert count == 2
    finally:
        repository.close()


def test_database_does_not_store_secret_like_configuration_values(tmp_path: Path, report) -> None:  # type: ignore[no-untyped-def]
    safe = report("scan-1").model_copy(
        update={"configuration": {"api_key": "[REDACTED]", "mode": "offline"}}
    )
    unsafe = report("scan-2").model_copy(
        update={"configuration": {"api_key": "sk-synthetic-secret-value"}}
    )
    repository = SQLiteScanHistoryRepository(tmp_path / "history.sqlite3")
    try:
        repository.save(safe)
        with pytest.raises(StorageError, match="credential-like"):
            repository.save(unsafe)
    finally:
        repository.close()

    database_bytes = (tmp_path / "history.sqlite3").read_bytes()
    assert b"sk-synthetic-secret-value" not in database_bytes
    assert b"[REDACTED]" in database_bytes
