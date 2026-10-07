"""Coordinate attachment validation, filesystem compensation and SQL writes."""
from datetime import date
from pathlib import Path
import sqlite3
import ntpath

from app import database
from app.backups import sha256_file
from app.certificates import copy_certificate
from app.data_access import data_operation
from app.errors import ValidationError
from app.medical_repository import save_certificate_record, remove_certificate_records, update_verification_record
from app.paths import managed_path, resolve_certificate_path
from app.validation import require_id, parse_certificate_date


def _active_student(conn: sqlite3.Connection, student_id: int) -> None:
    row = conn.execute("SELECT student_id FROM students WHERE student_id=? AND status='active'",
                       (require_id(student_id),)).fetchone()
    if row is None:
        raise ValidationError("El alumno ya no está disponible.")


def register_existing_reference(conn: sqlite3.Connection, student_id: int,
                                issue_date: date | str, reference: str) -> int:
    """Preserve absolute references only when already owned by this student ID."""
    _active_student(conn, student_id)
    issued = parse_certificate_date(issue_date.isoformat() if isinstance(issue_date, date) else issue_date)
    if ntpath.isabs(reference) or Path(reference).is_absolute():
        existing = conn.execute("SELECT certificate_id FROM medical_certificates WHERE student_id=? AND file_path=?",
                                (student_id, reference)).fetchone()
        if existing is None:
            raise ValidationError("Los certificados nuevos deben usar rutas relativas.")
        # Editing fields must preserve unavailable legacy references without
        # unexpectedly reading external files or erasing historic ownership.
        conn.execute("UPDATE medical_certificates SET issue_date=? WHERE certificate_id=?", (issued, existing[0]))
        return int(existing[0])
    root = Path(database.DB_PATH).parent
    path = managed_path(root, reference)
    if not reference.startswith("certificados/") or not path.is_file():
        raise ValidationError("El certificado administrado no está disponible.")
    return save_certificate_record(conn, student_id, issued, reference, sha256_file(path))


def attach_certificate(student_id: int, source: str, issue_date: str) -> str:
    """Copy and register under one lock; remove only the new file on DB failure."""
    require_id(student_id)
    issued = parse_certificate_date(issue_date)
    root, reference = Path(database.DB_PATH).parent, None
    with data_operation(root):
        try:
            with database.get_connection() as conn:
                _active_student(conn, student_id)
                reference = copy_certificate(source, data_root=root)
                register_existing_reference(conn, student_id, issued, reference)
            return reference
        except Exception:
            if reference is not None:
                managed_path(root, reference).unlink(missing_ok=True)
            raise


def set_medical_verification(student_id: int, verified: bool, issue_date: str = "") -> None:
    """Autosave por ID, sin guardar otros campos ni inferir verificación desde adjuntos."""
    require_id(student_id)
    if not isinstance(verified, bool):
        raise ValidationError("Estado médico inválido.")
    issued = parse_certificate_date(issue_date) if verified else ""
    with database.get_connection() as conn:
        _active_student(conn, student_id)
        update_verification_record(conn, student_id, verified, issued)


def remove_certificates(student_id: int) -> None:
    """Remove references, never delete historic files from the user's disk."""
    with database.get_connection() as conn:
        _active_student(conn, student_id)
        remove_certificate_records(conn, student_id)


def certificate_path(reference: str) -> Path:
    """Resolve a relative or legacy reference for preview/open."""
    return resolve_certificate_path(reference, Path(database.DB_PATH).parent)
