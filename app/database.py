"""Connections, transactions and versioned initialization for local SQLite."""
import sqlite3
from pathlib import Path

from app.paths import DATA_FOLDER, DB_PATH, SCHEMA_PATH
from app.data_access import data_operation
from app.paths import managed_path


class ManagedConnection(sqlite3.Connection):
    """Commit/rollback normally, then release the database file handle."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

    def close(self) -> None:
        """Release both SQLite and the shared data-operation lock exactly once."""
        try:
            super().close()
        finally:
            operation = getattr(self, "_data_operation", None)
            if operation is not None:
                self._data_operation = None
                operation.__exit__(None, None, None)


def get_connection() -> ManagedConnection:
    """Return a thread-local connection; callers must close it or use with."""
    Path(DATA_FOLDER).mkdir(parents=True, exist_ok=True)

    operation = data_operation(Path(DB_PATH).parent)
    operation.__enter__()
    conn = None
    try:
        db_path = managed_path(Path(DB_PATH).parent, Path(DB_PATH).name)
        conn = sqlite3.connect(str(db_path), factory=ManagedConnection, timeout=5.0)
        conn._data_operation = operation
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except Exception:
        if conn is not None:
            conn.close()
        else:
            operation.__exit__(None, None, None)
        raise


def init_db() -> None:
    """Initialize/migrate after a verified backup of a pre-existing old schema."""
    Path(DATA_FOLDER).mkdir(parents=True, exist_ok=True)

    schema_path = Path(SCHEMA_PATH)

    if not schema_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo schema.sql en: {schema_path}"
        )

    from app.migrations import migrate_database, get_schema_version, CURRENT_SCHEMA_VERSION
    with get_connection() as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if tables and get_schema_version(conn) < CURRENT_SCHEMA_VERSION:
            # Snapshot DB and attachments before changing any legacy schema.
            from app.backups import create_backup
            create_backup(Path(DB_PATH).parent)
        migrate_database(conn)
