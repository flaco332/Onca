"""Parameterized payment SQL; transactional context owns commit/rollback."""
from app.database import get_connection
from app.validation import MoneyInput


def add_payment(
    student_id: int,
    amount: MoneyInput,
    payment_date: str,
    payment_month: str,
    method: str = "",
    notes: str = ""
):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO payments (
                student_id,
                amount,
                payment_date,
                payment_month,
                method,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                str(amount),
                payment_date,
                payment_month,
                method,
                notes
            )
        )

        return cursor.lastrowid


def get_payments_by_student(student_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT
                payment_id,
                student_id,
                amount,
                payment_date,
                payment_month,
                method,
                notes,
                created_at
            FROM payments
            WHERE student_id = ?
            ORDER BY payment_date DESC, payment_id DESC
            """,
            (student_id,)
        )

        return cursor.fetchall()


def update_payment(
    payment_id: int,
    amount: MoneyInput,
    payment_date: str,
    payment_month: str,
    method: str = "",
    notes: str = ""
):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE payments
            SET
                amount = ?,
                payment_date = ?,
                payment_month = ?,
                method = ?,
                notes = ?
            WHERE payment_id = ?
            """,
            (
                str(amount),
                payment_date,
                payment_month,
                method,
                notes,
                payment_id
            )
        )
        if cursor.rowcount != 1:
            from app.errors import ValidationError
            raise ValidationError("El pago ya no está disponible.")


def delete_payment(payment_id: int):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM payments
            WHERE payment_id = ?
            """,
            (payment_id,)
        )
        if cursor.rowcount != 1:
            from app.errors import ValidationError
            raise ValidationError("El pago ya no está disponible.")
