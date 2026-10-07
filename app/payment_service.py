"""Payment field validation and stable-ID operations, without UI dependencies."""
from app import database, payments_repository as repository
from app.data_access import data_operation
from app.errors import ValidationError
from app.students_repository import get_student_by_id
from app.validation import require_id, parse_date_field, parse_iso_date, parse_amount, bounded_text, MoneyInput
from pathlib import Path
from decimal import Decimal


def _fields(amount: MoneyInput, payment_date: str, payment_month: str, method: str, notes: str) -> tuple:
    issued = parse_date_field(payment_date, "payment")
    try:
        parse_iso_date(payment_month + "-01")
    except ValidationError:
        raise ValidationError("Mes de pago inválido. Usa YYYY-MM.") from None
    return parse_amount(amount), issued, payment_month, bounded_text(method, "Método", 100), bounded_text(notes, "Notas")


def add_payment(student_id: int, amount: MoneyInput, payment_date: str, payment_month: str,
                method: str = "", notes: str = "") -> int:
    """Create a payment for one active student, with no name matching."""
    require_id(student_id)
    fields = _fields(amount, payment_date, payment_month, method, notes)
    with data_operation(Path(database.DB_PATH).parent):
        row = get_student_by_id(student_id)
        if row is None or row["status"] != "active":
            raise ValidationError("El alumno ya no está disponible.")
        return repository.add_payment(student_id, *fields)


def update_payment(payment_id: int, amount: MoneyInput, payment_date: str, payment_month: str,
                   method: str = "", notes: str = "") -> None:
    """Update exactly one payment ID after central validation."""
    repository.update_payment(require_id(payment_id), *_fields(amount, payment_date, payment_month, method, notes))


def delete_payment(payment_id: int) -> None:
    """Delete exactly one payment ID; report stale selection."""
    repository.delete_payment(require_id(payment_id))


def get_payments_by_student(student_id: int):
    """List one student's ordered history using the composite index."""
    payments = [dict(row) for row in repository.get_payments_by_student(require_id(student_id))]
    for payment in payments:
        payment["amount"] = Decimal(str(payment["amount"]))
    return payments
