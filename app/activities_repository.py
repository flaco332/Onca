"""Activity and participation SQL, including atomic group writes."""
from app.database import get_connection
from app.validation import normalize_activity_status, MoneyInput


def create_activity(
    title: str,
    activity_type: str,
    activity_date: str,
    location: str = "",
    cost: MoneyInput = 0,
    notes: str = ""
):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO extra_activities (
                title,
                activity_type,
                activity_date,
                location,
                cost,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                activity_type,
                activity_date,
                location,
                str(cost),
                notes
            )
        )

        return cursor.lastrowid


def add_student_to_activity(
    student_id: int,
    activity_id: int,
    paid_amount: MoneyInput = 0,
    attendance_status: str = "registered",
    notes: str = ""
):
    normalized_status = normalize_activity_status(attendance_status)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO student_activities (
                student_id,
                activity_id,
                paid_amount,
                attendance_status,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                student_id,
                activity_id,
                str(paid_amount),
                normalized_status,
                notes
            )
        )

        return cursor.lastrowid


def create_activity_for_students(
    student_ids: list[int],
    title: str,
    activity_type: str,
    activity_date: str,
    location: str = "",
    cost: MoneyInput = 0,
    paid_amount: MoneyInput = 0,
    attendance_status: str = "registered",
    notes: str = ""
):
    if not student_ids:
        raise ValueError("Selecciona al menos un alumno.")

    normalized_status = normalize_activity_status(attendance_status)

    with get_connection() as conn:
        conn.execute("BEGIN")

        try:
            cursor = conn.execute(
                """
                INSERT INTO extra_activities (
                    title,
                    activity_type,
                    activity_date,
                    location,
                    cost,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    activity_type,
                    activity_date,
                    location,
                    str(cost),
                    notes,
                )
            )

            activity_id = cursor.lastrowid

            for student_id in student_ids:
                conn.execute(
                    """
                    INSERT INTO student_activities (
                        student_id,
                        activity_id,
                        paid_amount,
                        attendance_status,
                        notes
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        activity_id,
                        str(paid_amount),
                        normalized_status,
                        notes,
                    )
                )

            conn.commit()
            return activity_id
        except Exception:
            conn.rollback()
            raise


def get_activities_by_student(student_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                sa.student_activity_id,
                sa.student_id,
                sa.activity_id,
                sa.paid_amount,
                sa.attendance_status,
                sa.notes AS student_activity_notes,
                sa.created_at,

                ea.title,
                ea.activity_type,
                ea.activity_date,
                ea.location,
                ea.cost,
                ea.notes AS activity_notes

            FROM student_activities sa
            INNER JOIN extra_activities ea
                ON sa.activity_id = ea.activity_id
            WHERE sa.student_id = ?
            ORDER BY ea.activity_date DESC, sa.student_activity_id DESC
            """,
            (student_id,)
        )

        return cursor.fetchall()


def update_student_activity(
    student_activity_id: int,
    title: str,
    activity_type: str,
    activity_date: str,
    location: str = "",
    cost: MoneyInput = 0,
    paid_amount: MoneyInput = 0,
    attendance_status: str = "registered",
    notes: str = ""
):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT activity_id
            FROM student_activities
            WHERE student_activity_id = ?
            """,
            (student_activity_id,)
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError("No se encontró la actividad del alumno.")

        activity_id = row["activity_id"]
        shared = conn.execute("SELECT count(*) FROM student_activities WHERE activity_id=?", (activity_id,)).fetchone()[0] > 1
        if shared:
            # Copy-on-write: individual edits must not alter another student's
            # title, cost or dates in a shared group activity.
            cursor = conn.execute("INSERT INTO extra_activities (title, activity_type, activity_date, location, cost, notes) VALUES (?, ?, ?, ?, ?, ?)",
                                  (title, activity_type, activity_date, location, str(cost), notes))
            activity_id = cursor.lastrowid
            conn.execute("UPDATE student_activities SET activity_id=? WHERE student_activity_id=?", (activity_id, student_activity_id))

        conn.execute(
            """
            UPDATE extra_activities
            SET
                title = ?,
                activity_type = ?,
                activity_date = ?,
                location = ?,
                cost = ?,
                notes = ?
            WHERE activity_id = ?
            """,
            (
                title,
                activity_type,
                activity_date,
                location,
                str(cost),
                notes,
                activity_id
            )
        )

        conn.execute(
            """
            UPDATE student_activities
            SET
                paid_amount = ?,
                attendance_status = ?,
                notes = ?
            WHERE student_activity_id = ?
            """,
            (
                str(paid_amount),
                attendance_status,
                notes,
                student_activity_id
            )
        )


def delete_student_activity(student_activity_id: int) -> None:
    """Delete one relationship and clean an unreferenced activity atomically."""
    with get_connection() as conn:
        row = conn.execute("SELECT activity_id FROM student_activities WHERE student_activity_id=?", (student_activity_id,)).fetchone()
        if row is None:
            from app.errors import ValidationError
            raise ValidationError("La actividad ya no está disponible.")
        conn.execute("DELETE FROM student_activities WHERE student_activity_id=?", (student_activity_id,))
        conn.execute("DELETE FROM extra_activities WHERE activity_id=? AND NOT EXISTS (SELECT 1 FROM student_activities WHERE activity_id=?)", (row[0], row[0]))
