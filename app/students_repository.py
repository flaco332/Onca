"""Student SQL operations. Identity is always student_id, never the name."""
import sqlite3
from app.database import get_connection


def add_student(
    first_name: str,
    last_name: str,
    birth_date: str = "",
    phone: str = "",
    emergency_contact_name: str = "",
    emergency_contact_phone: str = "",
    belt_rank: str = "",
    notes: str = ""
):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO students (
                first_name,
                last_name,
                birth_date,
                phone,
                emergency_contact_name,
                emergency_contact_phone,
                belt_rank,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                birth_date,
                phone,
                emergency_contact_name,
                emergency_contact_phone,
                belt_rank,
                notes,
            )
        )

        return cursor.lastrowid


def get_students():
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                student_id,
                first_name,
                last_name,
                birth_date,
                phone,
                emergency_contact_name,
                emergency_contact_phone,
                belt_rank,
                status,
                notes,
                created_at,
                updated_at
            FROM students
            ORDER BY last_name, first_name
            """
        )

        return cursor.fetchall()


def get_student_by_id(student_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                student_id,
                first_name,
                last_name,
                birth_date,
                phone,
                emergency_contact_name,
                emergency_contact_phone,
                belt_rank,
                status,
                notes,
                created_at,
                updated_at
            FROM students
            WHERE student_id = ?
            """,
            (student_id,)
        )

        return cursor.fetchone()

def list_active_student_rows(today: str) -> list[sqlite3.Row]:
    """Proyecta alumnos y estados juntos; la actividad se agrupa sin consultas por fila."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                s.student_id,
                s.first_name,
                s.last_name,
                s.birth_date,
                s.phone,
                s.emergency_contact_name,
                s.emergency_contact_phone,
                s.belt_rank,
                s.status,
                s.notes,
                s.medical_verified,
                upcoming.next_activity_date,

                (
                    SELECT p.payment_date
                    FROM payments p
                    WHERE p.student_id = s.student_id
                    ORDER BY p.payment_date DESC, p.payment_id DESC
                    LIMIT 1
                ) AS last_payment_date,

                (
                    SELECT mc.issue_date
                    FROM medical_certificates mc
                    WHERE mc.student_id = s.student_id
                    ORDER BY mc.issue_date DESC, mc.certificate_id DESC
                    LIMIT 1
                ) AS medical_cert_date,

                (
                    SELECT mc.file_path
                    FROM medical_certificates mc
                    WHERE mc.student_id = s.student_id
                    ORDER BY mc.issue_date DESC, mc.certificate_id DESC
                    LIMIT 1
                ) AS medical_cert_path

            FROM students s
            LEFT JOIN (
                SELECT sa.student_id, MIN(ea.activity_date) AS next_activity_date
                FROM student_activities sa
                JOIN extra_activities ea ON ea.activity_id = sa.activity_id
                WHERE ea.activity_date >= ?
                  AND date(ea.activity_date, '+0 days') = ea.activity_date
                  AND sa.attendance_status IN ('registered', 'pending', 'confirmed')
                GROUP BY sa.student_id
            ) upcoming ON upcoming.student_id = s.student_id
            WHERE s.status = 'active'
            ORDER BY s.last_name, s.first_name
            """, (today,)
        )

        return cursor.fetchall()



def get_student_name_parts(conn: sqlite3.Connection, student_id: int) -> sqlite3.Row | None:
    """Lee la separación existente dentro de la transacción de guardado."""
    return conn.execute("SELECT first_name,last_name FROM students WHERE student_id=?", (student_id,)).fetchone()


def save_student_record(conn: sqlite3.Connection, student: dict, student_id: int | None) -> int:
    """Insert or update within the caller transaction; homonyms are independent."""
    first_name = student["first_name"]
    last_name = student["last_name"]
    birth_date = student.get("birth_date", "")
    phone = student.get("phone", "")
    emergency_contact_name = student.get("emergency_contact_name", "")
    emergency_contact_phone = student.get("emergency_contact_phone", "")
    belt_rank = student.get("belt_rank", "")
    notes = student.get("notes", "")
    if student_id is None:
        cursor = conn.execute(
            """
            INSERT INTO students (
                first_name,
                last_name,
                birth_date,
                phone,
                emergency_contact_name,
                emergency_contact_phone,
                belt_rank,
                notes, medical_verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                birth_date,
                phone,
                emergency_contact_name,
                emergency_contact_phone,
                belt_rank,
                notes,
                int(student.get("has_medical", False)),
            )
        )

        student_id = cursor.lastrowid

    else:
        cursor = conn.execute(
            """
            UPDATE students
            SET
                first_name = ?,
                last_name = ?,
                birth_date = ?,
                phone = ?,
                emergency_contact_name = ?,
                emergency_contact_phone = ?,
                belt_rank = ?,
                notes = ?,
                medical_verified = COALESCE(?, medical_verified),
                updated_at = CURRENT_TIMESTAMP
            WHERE student_id = ? AND status = 'active'
            """,
            (
                first_name,
                last_name,
                birth_date,
                phone,
                emergency_contact_name,
                emergency_contact_phone,
                belt_rank,
                notes,
                int(student["has_medical"]) if "has_medical" in student else None,
                student_id,
            )
        )

        if cursor.rowcount != 1:
            from app.errors import ValidationError
            raise ValidationError("El alumno ya no está disponible.")
    return int(student_id)


def deactivate_student(student_id: int) -> None:
    """Preserve associated history when an active student is removed."""
    with get_connection() as conn:
        cursor = conn.execute("UPDATE students SET status='inactive', updated_at=CURRENT_TIMESTAMP WHERE student_id=? AND status='active'", (student_id,))
        if cursor.rowcount != 1:
            from app.errors import ValidationError
            raise ValidationError("El alumno ya no está disponible.")


def active_student_ids(conn: sqlite3.Connection, student_ids: list[int]) -> set[int]:
    """Validate a selection in one SQL round-trip, using bounded IN batches."""
    result = set()
    for offset in range(0, len(student_ids), 500):
        chunk = student_ids[offset:offset + 500]
        placeholders = ",".join("?" for _ in chunk)
        result.update(row[0] for row in conn.execute(
            f"SELECT student_id FROM students WHERE status='active' AND student_id IN ({placeholders})", chunk))
    return result
