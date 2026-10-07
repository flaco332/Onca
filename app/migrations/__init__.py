"""Ordered, atomic SQLite migrations using PRAGMA user_version.

Version 1 adopts the original schema after checking its columns and foreign
keys. Version 2 adds only measured query indexes and write-time guards. Legacy
rows are not rewritten, deleted or forced to satisfy new-field validation.
La versión 3 persiste la verificación médica explícita; no la infiere de archivos.
La versión 4 conserva nombres separados y adopta name antiguo sin heurísticas.
"""
from collections.abc import Callable
from pathlib import Path
import sqlite3

from app.errors import DatabaseError
from app.logging_config import log_event
from app.paths import SCHEMA_PATH

CURRENT_SCHEMA_VERSION = 4
Migration = Callable[[sqlite3.Connection], None]


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read the durable SQLite schema version."""
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _statements(sql: str) -> list[str]:
    statements, pending = [], ""
    for line in sql.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statements.append(pending)
            pending = ""
    if pending.strip():
        raise DatabaseError("Incomplete migration script")
    return statements


def validate_schema(conn: sqlite3.Connection) -> None:
    """Reject incompatible existing tables instead of claiming migration success."""
    expected = sqlite3.connect(":memory:")
    try:
        expected.executescript(Path(SCHEMA_PATH).read_text(encoding="utf-8"))
        tables = [r[0] for r in expected.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name!='sqlite_sequence'")]
        for table in tables:
            # Table names originate exclusively from the bundled schema.
            wanted = {r[1]: (r[2], r[3], r[5]) for r in expected.execute(f'PRAGMA table_info("{table}")')}
            actual = {r[1]: (r[2], r[3], r[5]) for r in conn.execute(f'PRAGMA table_info("{table}")')}
            if table == "students" and get_schema_version(conn) < 4 and _has_legacy_name(conn):
                # Permite verificar el respaldo anterior a convertir el nombre único.
                actual["first_name"] = actual["name"]
                actual["last_name"] = wanted["last_name"]
            if any(actual.get(k) != v for k, v in wanted.items()):
                raise DatabaseError("Schema incompatible; a specific migration is required")
            wanted_fk = {tuple(r)[2:] for r in expected.execute(f'PRAGMA foreign_key_list("{table}")')}
            actual_fk = {tuple(r)[2:] for r in conn.execute(f'PRAGMA foreign_key_list("{table}")')}
            if not wanted_fk.issubset(actual_fk):
                raise DatabaseError("Required foreign keys missing")
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise DatabaseError("Foreign key integrity check failed")
        if get_schema_version(conn) >= 3:
            columns = {r[1]: (r[2], r[3]) for r in conn.execute('PRAGMA table_info("students")')}
            if columns.get("medical_verified") != ("INTEGER", 1):
                raise DatabaseError("Medical verification schema incompatible")
    finally:
        expected.close()


def _baseline(conn: sqlite3.Connection) -> None:
    for statement in _statements(Path(SCHEMA_PATH).read_text(encoding="utf-8")):
        conn.execute(statement)
    validate_schema(conn)


def _query_indexes(conn: sqlite3.Connection) -> None:
    sql = (Path(__file__).parent / "002_integrity_and_indexes.sql").read_text(encoding="utf-8")
    for statement in _statements(sql):
        conn.execute(statement)


def _medical_verification(conn: sqlite3.Connection) -> None:
    """Añade un estado explícito sin inferirlo ni reescribir adjuntos existentes."""
    sql = (Path(__file__).parent / "003_medical_verification.sql").read_text(encoding="utf-8")
    for statement in _statements(sql):
        conn.execute(statement)


def _has_legacy_name(conn: sqlite3.Connection) -> bool:
    columns = {r[1] for r in conn.execute('PRAGMA table_info("students")')}
    return "name" in columns and not columns.intersection({"first_name", "last_name"})


def _student_names(conn: sqlite3.Connection) -> None:
    """Conserva separaciones existentes; name antiguo pasa íntegro a first_name."""
    if _has_legacy_name(conn):
        sql = (Path(__file__).parent / "004_student_names.sql").read_text(encoding="utf-8")
        for statement in _statements(sql):
            conn.execute(statement)


MIGRATIONS: dict[int, Migration] = {1: _baseline, 2: _query_indexes, 3: _medical_verification, 4: _student_names}


def apply_migration(conn: sqlite3.Connection, version: int,
                    migration: Migration | None = None) -> None:
    """Apply one next migration in a savepoint, including its version marker."""
    if version != get_schema_version(conn) + 1:
        raise DatabaseError("Migrations must be consecutive")
    callback = migration or MIGRATIONS.get(version)
    if callback is None:
        raise DatabaseError("Migration unavailable")
    conn.execute("SAVEPOINT onca_migration")
    try:
        callback(conn)
        conn.execute(f"PRAGMA user_version = {int(version)}")
        conn.execute("RELEASE onca_migration")
    except Exception:
        conn.execute("ROLLBACK TO onca_migration")
        conn.execute("RELEASE onca_migration")
        raise


def migrate_database(conn: sqlite3.Connection) -> None:
    """Upgrade all pending versions atomically; refuse newer unknown schemas."""
    version = get_schema_version(conn)
    if version > CURRENT_SCHEMA_VERSION:
        raise DatabaseError("Database created by a newer application")
    log_event("database_migration_started")
    conn.execute("SAVEPOINT onca_upgrade")
    try:
        if version < 4:
            # La adopción precede los índices v1/v2 y comparte el rollback del upgrade.
            _student_names(conn)
        for next_version in range(version + 1, CURRENT_SCHEMA_VERSION + 1):
            apply_migration(conn, next_version)
        validate_schema(conn)
        conn.execute("RELEASE onca_upgrade")
        log_event("database_migration_completed")
    except Exception as error:
        conn.execute("ROLLBACK TO onca_upgrade")
        conn.execute("RELEASE onca_upgrade")
        log_event("database_migration_failed", error)
        if isinstance(error, sqlite3.Error):
            raise DatabaseError("No fue posible actualizar la estructura de datos.") from error
        raise
