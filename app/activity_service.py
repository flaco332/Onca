"""Validated activity orchestration; single/group creation is one transaction."""
from app import activities_repository as repository, database
from app.data_access import data_operation
from app.errors import ValidationError, FieldValidationError
from decimal import Decimal
from app.students_repository import active_student_ids
from app.validation import require_id, parse_date_field, parse_amount, bounded_text, normalize_activity_status, remaining_balance, MoneyInput
from pathlib import Path


def _fields(title: str, activity_type: str, activity_date: str, location: str,
            cost: MoneyInput, paid_amount: MoneyInput, attendance_status: str, notes: str) -> dict:
    valid_status = {"registered", "pending", "confirmed", "attended", "absent", "cancelled"}
    if attendance_status not in valid_status:
        raise ValidationError("Estado de actividad inválido.")
    total, paid, _ = activity_amounts(cost, paid_amount)
    return dict(title=validate_activity_field("title", title),
                activity_type=bounded_text(activity_type, "Tipo", 100, required=True),
                activity_date=validate_activity_field("activity_date", activity_date), location=validate_activity_field("location", location),
                cost=total, paid_amount=paid,
                attendance_status=normalize_activity_status(attendance_status), notes=bounded_text(notes, "Notas"))


def activity_amounts(cost, paid_amount) -> tuple[Decimal, Decimal, Decimal]:
    """Validación financiera común para edición en vivo y cualquier guardado."""
    clean, errors = {}, {}
    for field, value in (("cost", cost), ("paid_amount", paid_amount)):
        try:
            clean[field] = parse_amount(value, allow_zero=True)
        except ValidationError as error:
            errors[field] = str(error)
    if not errors:
        try:
            balance = remaining_balance(clean["cost"], clean["paid_amount"])
        except ValidationError as error:
            errors["paid_amount"] = str(error)
    if errors:
        raise FieldValidationError(errors)
    return clean["cost"], clean["paid_amount"], balance


def validate_activity_field(field: str, value: MoneyInput) -> str | Decimal:
    """Reglas únicas para el formulario y las operaciones sin interfaz."""
    if field in ("cost", "paid_amount"):
        return parse_amount(value, allow_zero=True)
    if field == "activity_date":
        return parse_date_field(value, "activity")
    return bounded_text(value, "Título" if field == "title" else "Lugar", 200, required=field == "title")


def create_activity_for_students(student_ids: list[int], title: str, activity_type: str,
                                 activity_date: str, location: str = "", cost: MoneyInput = 0,
                                 paid_amount: MoneyInput = 0, attendance_status: str = "registered", notes: str = "") -> int:
    """Validate all IDs, then persist activity and relationships atomically."""
    if not student_ids or len(set(student_ids)) != len(student_ids):
        raise ValidationError("Selecciona alumnos distintos.")
    for student_id in student_ids:
        require_id(student_id)
    fields = _fields(title, activity_type, activity_date, location, cost, paid_amount, attendance_status, notes)
    with data_operation(Path(database.DB_PATH).parent):
        # Batch existence check rather than one query per selected student.
        with database.get_connection() as conn:
            found = active_student_ids(conn, student_ids)
            if len(found) != len(student_ids):
                raise ValidationError("Uno de los alumnos ya no está disponible.")
        return repository.create_activity_for_students(student_ids=student_ids, **fields)


def update_student_activity(student_activity_id: int, title: str, activity_type: str,
                            activity_date: str, location: str = "", cost: MoneyInput = 0,
                            paid_amount: MoneyInput = 0, attendance_status: str = "registered", notes: str = "") -> None:
    """Edit selected participation without changing other students' activity data."""
    fields = _fields(title, activity_type, activity_date, location, cost, paid_amount, attendance_status, notes)
    repository.update_student_activity(require_id(student_activity_id), **fields)


def get_activities_by_student(student_id: int):
    """Fetch relationships and metadata in one joined query."""
    activities = [dict(row) for row in repository.get_activities_by_student(require_id(student_id))]
    for activity in activities:
        for field in ("cost", "paid_amount"):
            activity[field] = Decimal(str(activity[field] if activity[field] is not None else 0))
    return activities


def delete_student_activity(student_activity_id: int) -> None:
    """Remove one participation; retain any activity shared by others."""
    repository.delete_student_activity(require_id(student_activity_id))
