"""Student validation and transaction orchestration, independent of widgets."""
from datetime import date
from app.database import get_connection
from app.errors import ValidationError, FieldValidationError
from app.models import StudentDraft
from app import students_repository as repository
from app.validation import validate_person_name, phone_error, require_id, parse_birth_date, bounded_text


def split_name(full_name: str) -> tuple[str, str]:
    first, _, last = full_name.strip().partition(" ")
    return first, last


def display_name(first_name: str | None, last_name: str | None = "") -> str:
    """Nombre de presentación común, sin marcadores para apellidos ausentes."""
    return " ".join(part.strip() for part in (first_name, last_name) if part and part.strip())


join_name = display_name


def medical_indicator(student: dict) -> str:
    """Indicador único del estado persistido, compartido por carga y autosave."""
    return "✓" if student["has_medical"] else ""


def load_students_from_db(*, today: date | None = None, search: str = "") -> list[dict]:
    """Carga estados persistidos en una consulta, sin inventar fechas de pago."""
    students = []
    today = today or date.today()
    rows = repository.list_active_student_rows(today.isoformat())

    for row in rows:
        last_payment_raw = row["last_payment_date"]
        medical_cert_raw = row["medical_cert_date"]

        try:
            last_payment_date = date.fromisoformat(last_payment_raw)
        except (ValueError, TypeError):
            last_payment_date = None

        try:
            medical_cert_date = date.fromisoformat(medical_cert_raw)
        except (ValueError, TypeError):
            medical_cert_date = today

        medical_cert_path = row["medical_cert_path"] or ""

        students.append({
            "student_id": row["student_id"],
            "first_name": row["first_name"],
            "last_name": row["last_name"] or "",
            "name": display_name(row["first_name"], row["last_name"]),
            "birth_date": row["birth_date"] or "",
            "phone": row["phone"] or "",
            "emergency_contact_name": row["emergency_contact_name"] or "",
            "emergency_contact_phone": row["emergency_contact_phone"] or "",
            "belt_rank": row["belt_rank"] or "",
            "notes": row["notes"] or "",
            "has_medical": bool(row["medical_verified"]),
            "next_activity_date": row["next_activity_date"] or "",
            "last_payment_date": last_payment_date,
            "medical_cert_date": medical_cert_date,
            "medical_cert_path": medical_cert_path,
        })

    query = search.strip().casefold()
    return [student for student in students if query in student["name"].casefold()]



def validate_student(student: StudentDraft) -> StudentDraft:
    """Normaliza una sola vez y devuelve errores por campo para cualquier interfaz."""
    clean = dict(student)
    # Los clientes antiguos con solo name conservan el texto completo, sin inferir apellidos.
    clean["first_name"] = clean.get("first_name", clean.get("name", ""))
    clean["last_name"] = clean.get("last_name", "")
    errors = {}
    for field in ("first_name", "last_name", "phone", "emergency_contact_phone", "emergency_contact_name", "birth_date", "belt_rank", "notes"):
        try:
            clean[field] = validate_student_field(field, clean.get(field, ""))
        except ValidationError as error:
            errors[field] = str(error)
    if errors:
        raise FieldValidationError(errors)
    clean["name"] = display_name(clean["first_name"], clean["last_name"])
    if "has_medical" in clean and not isinstance(clean["has_medical"], bool):
        raise FieldValidationError({"has_medical": "Estado médico inválido."})
    if clean.get("student_id") is not None:
        require_id(clean["student_id"])
    return clean


def validate_student_field(field: str, value: str) -> str:
    """Reglas compartidas entre edición en vivo y guardado definitivo."""
    if not isinstance(value, str):
        raise ValidationError("Texto inválido.")
    if field in ("phone", "emergency_contact_phone"):
        error = phone_error(value)
        if error:
            raise ValidationError(error)
        return value.strip()
    if field == "birth_date":
        return parse_birth_date(value.strip())
    limits = {"name": 200, "first_name": 200, "last_name": 200, "emergency_contact_name": 200, "belt_rank": 100, "notes": 4000}
    result = bounded_text(value, "Campo", limits[field], required=field in ("name", "first_name"))
    if field in ("name", "first_name", "last_name", "emergency_contact_name") and result and not validate_person_name(result):
        raise ValidationError("Usa letras, espacios, acentos, apóstrofes o guiones.")
    return result


def save_student_to_db(student: StudentDraft) -> int:
    """Persist by ID, atomically with an optional previously managed certificate."""
    clean = validate_student(student)
    with get_connection() as conn:
        if clean.get("student_id") is not None and "first_name" not in student and "last_name" not in student:
            previous = repository.get_student_name_parts(conn, clean["student_id"])
            # Guardados antiguos del nombre visible no deben alterar una separación ya existente.
            if previous and clean["name"] == display_name(previous["first_name"], previous["last_name"]):
                clean["first_name"], clean["last_name"] = previous["first_name"], previous["last_name"]
        student_id = repository.save_student_record(conn, clean, clean.get("student_id"))
        if clean.get("medical_cert_path"):
            from app.certificate_service import register_existing_reference
            register_existing_reference(conn, student_id, clean.get("medical_cert_date", date.today()), clean["medical_cert_path"])
        return student_id


def delete_student_from_db(student_id: int) -> None:
    """Deactivate exactly one student; preserve historical payment/attachment rows."""
    repository.deactivate_student(require_id(student_id))
