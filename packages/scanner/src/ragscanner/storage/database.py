"""Secure SQLite engine and versioned Alembic migration helpers."""

import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event

_MIGRATION_LOCK = threading.Lock()


class StorageError(RuntimeError):
    """Safe persistence failure without database internals or report content."""


def _alembic_config(database_path: Path) -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    return config


def _backup(database_path: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = database_path.with_name(f"{database_path.name}.backup-{stamp}")
    with sqlite3.connect(database_path) as source, sqlite3.connect(backup_path) as target:
        source.backup(target)
    backup_path.chmod(0o600)
    return backup_path


def upgrade_database(database_path: Path) -> Path | None:
    """Upgrade to the packaged head, backing up an existing older database first."""
    path = database_path.expanduser().resolve()
    parent_was_created = not path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    if parent_was_created:
        path.parent.chmod(0o700)
    try:
        # Alembic's environment proxy is process-global and is not thread-safe.
        # Serializing local initialization also prevents duplicate backups.
        with _MIGRATION_LOCK:
            config = _alembic_config(path)
            head = ScriptDirectory.from_config(config).get_current_head()
            backup_path: Path | None = None
            if path.exists() and path.stat().st_size:
                probe = create_engine(f"sqlite:///{path}")
                try:
                    with probe.connect() as connection:
                        current = MigrationContext.configure(connection).get_current_revision()
                finally:
                    probe.dispose()
                if current != head:
                    backup_path = _backup(path)
            command.upgrade(config, "head")
            path.chmod(0o600)
    except Exception as error:
        raise StorageError("The local history database migration failed.") from error
    return backup_path


def create_sqlite_engine(database_path: Path) -> Engine:
    path = database_path.expanduser().resolve()
    upgrade_database(path)
    engine = create_engine(f"sqlite:///{path}", future=True)

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection: sqlite3.Connection, _record: object) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    os.chmod(path, 0o600)
    return engine
