"""Certificate SQL shared by transactional service operations."""
import sqlite3
from app.database import get_connection


def save_certificate_record(conn: sqlite3.Connection, student_id: int, issue_date: str,
                            file_path: str, file_hash: str = "", notes: str = "") -> int:
    """Upsert by student ID and exact reference in the caller transaction."""
    row = conn.execute("SELECT certificate_id FROM medical_certificates WHERE student_id=? AND file_path=? LIMIT 1",
                       (student_id, file_path)).fetchone()
    if row is None and file_path:
        # El primer adjunto completa metadatos sin archivo, evitando ocultarlo por una fecha antigua.
        row = conn.execute("SELECT certificate_id FROM medical_certificates WHERE student_id=? AND file_path='' ORDER BY issue_date DESC,certificate_id DESC LIMIT 1", (student_id,)).fetchone()
    if row:
        conn.execute("UPDATE medical_certificates SET issue_date=?, file_path=?, file_hash=?, notes=? WHERE certificate_id=?",
                     (issue_date, file_path, file_hash, notes, row[0]))
        return int(row[0])
    cursor = conn.execute("INSERT INTO medical_certificates (student_id, issue_date, file_path, file_hash, notes) VALUES (?, ?, ?, ?, ?)",
                          (student_id, issue_date, file_path, file_hash, notes))
    return int(cursor.lastrowid)


def save_medical_certificate(student_id: int, issue_date: str, file_path: str = "", notes: str = "") -> int:
    """Compatibility SQL entry; UI uses the validated certificate service."""
    with get_connection() as conn:
        return save_certificate_record(conn, student_id, issue_date, file_path, notes=notes)


def remove_certificate_records(conn: sqlite3.Connection, student_id: int) -> None:
    """Unlink certificate rows, retaining physical files for recovery."""
    conn.execute("DELETE FROM medical_certificates WHERE student_id=?", (student_id,))
    conn.execute("UPDATE students SET medical_verified=0 WHERE student_id=?", (student_id,))


def update_verification_record(conn: sqlite3.Connection, student_id: int, verified: bool, issue_date: str = "") -> None:
    """Guarda estado y fecha explícita juntos; una fecha sin archivo es solo metadato."""
    conn.execute("UPDATE students SET medical_verified=?, updated_at=CURRENT_TIMESTAMP WHERE student_id=?", (int(verified), student_id))
    if verified:
        latest = conn.execute("SELECT certificate_id FROM medical_certificates WHERE student_id=? ORDER BY issue_date DESC,certificate_id DESC LIMIT 1", (student_id,)).fetchone()
        if latest:
            conn.execute("UPDATE medical_certificates SET issue_date=? WHERE certificate_id=?", (issue_date, latest[0]))
        else:
            save_certificate_record(conn, student_id, issue_date, "")
