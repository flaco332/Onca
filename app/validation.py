"""Shared field validation, independent of Tkinter and SQLite."""
import re
from decimal import Decimal, InvalidOperation
from datetime import date
from app.errors import ValidationError

MoneyInput = str | Decimal | int | float

_NAME_PATTERN = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü' -]+$")


def validate_person_name(value: str | None) -> bool:
    if value is None:
        return False

    cleaned = str(value).strip()
    if not cleaned:
        return False

    return len(cleaned) <= 200 and bool(_NAME_PATTERN.fullmatch(cleaned)) and any(c.isalpha() for c in cleaned)


def validate_phone(value: str | None) -> bool:
    """Valida teléfonos formateados; un valor opcional vacío no es un número."""
    return isinstance(value, str) and bool(value.strip()) and not phone_error(value)


def phone_error(value: str) -> str:
    """Cuenta dígitos, conservando el formato legible y sin imponer un país."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9 +()\-]*", value):
        return "Usa solo números, espacios, +, -, ( )"
    cleaned = value.strip()
    if not cleaned:
        return ""
    if cleaned.count("+") > 1 or ("+" in cleaned and not cleaned.startswith("+")):
        return "Usa + solamente al inicio del número."
    depth = 0
    for character in cleaned:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        if depth not in (0, 1):
            return "Revisa los paréntesis del número."
    if depth:
        return "Revisa los paréntesis del número."
    digits = sum(character in "0123456789" for character in cleaned)
    if digits < 7:
        return "El número contiene muy pocos dígitos."
    if digits > 15:
        return "El número contiene demasiados dígitos."
    # El límite adicional evita almacenar separadores ilimitados, no rechaza formatos normales.
    if len(cleaned) > 80:
        return "El número contiene demasiados separadores."
    return ""


_ACTIVITY_STATUS_LABELS = {
    "registered": "Pendiente",
    "pending": "Pendiente",
    "confirmed": "Confirmado",
    "attended": "Asistió",
    "absent": "No asistió",
    "cancelled": "Cancelado",
}


_ACTIVITY_STATUS_VALUES = [
    ("Pendiente", "registered"),
    ("Confirmado", "confirmed"),
    ("Asistió", "attended"),
    ("No asistió", "absent"),
    ("Cancelado", "cancelled"),
]


def normalize_activity_status(value: str | None) -> str:
    if value is None:
        return "registered"

    normalized = str(value).strip().lower()

    aliases = {
        "registered": "registered",
        "pending": "registered",
        "confirmed": "confirmed",
        "attended": "attended",
        "absent": "absent",
        "cancelled": "cancelled",
    }

    return aliases.get(normalized, "registered")


def activity_status_label(value: str | None) -> str:
    return _ACTIVITY_STATUS_LABELS.get(normalize_activity_status(value), "Pendiente")


def activity_status_options() -> list[tuple[str, str]]:
    return list(_ACTIVITY_STATUS_VALUES)


def require_id(value: int) -> int:
    """Accept stable positive integer identifiers, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("Identificador inválido.")
    return value


def parse_iso_date(value: str, *, optional: bool = False) -> str:
    """Require canonical YYYY-MM-DD, rejecting relaxed ISO variants."""
    if optional and not value:
        return ""
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise ValidationError("Fecha inválida. Usa YYYY-MM-DD.") from None


def parse_amount(value: MoneyInput, *, allow_zero: bool = False) -> Decimal:
    """Valida centavos exactos; floats históricos entran solo mediante su texto."""
    raw = str(value).strip()
    if len(raw) > 32 or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", raw):
        raise ValidationError("Usa un monto no negativo con hasta dos decimales.")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        raise ValidationError("El monto debe ser un número.") from None
    if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0) or amount > 1_000_000_000:
        raise ValidationError("El monto debe ser finito, positivo y dentro del límite permitido.")
    return amount.quantize(Decimal("0.01"))


def remaining_balance(cost, paid_amount) -> Decimal:
    """El saldo nunca es negativo; la participación es independiente del pago."""
    total = parse_amount(cost, allow_zero=True)
    paid = parse_amount(paid_amount, allow_zero=True)
    if paid > total:
        raise ValidationError("El monto pagado no puede ser mayor al costo total.")
    return total - paid


def format_money(value) -> str:
    """Presenta importes históricos REAL con Decimal, sin aritmética binaria."""
    amount = Decimal(str(value if value is not None else 0))
    return f"${amount:.2f}" if amount.is_finite() else "Revisar monto"


def parse_date_field(value: str, kind: str = "activity", *, optional: bool = False, today: date | None = None) -> str:
    """Reglas comunes para entrada manual, selector y servicios."""
    if kind not in {"birth", "activity", "certificate", "payment"}:
        raise ValueError("Tipo de fecha desconocido.")
    if not value and kind == "certificate" and not optional:
        raise ValidationError("Selecciona la fecha del certificado.")
    result = parse_iso_date(value, optional=optional)
    if result and kind in {"birth", "certificate"} and date.fromisoformat(result) > (today or date.today()):
        label = "nacimiento" if kind == "birth" else "certificado"
        raise ValidationError(f"La fecha de {label} no puede ser futura.")
    return result


def parse_certificate_date(value: str, *, today: date | None = None) -> str:
    return parse_date_field(value, "certificate", today=today)


def parse_birth_date(value: str, *, today: date | None = None) -> str:
    """Conserva ISO y fechas históricas; el nacimiento no puede estar en el futuro."""
    return parse_date_field(value, "birth", optional=True, today=today)


def bounded_text(value: str, label: str, maximum: int = 4000, *, required: bool = False) -> str:
    """Strip fields and enforce bounds without including field values in errors."""
    if not isinstance(value, str):
        raise ValidationError(f"{label}: texto inválido.")
    cleaned = value.strip()
    if (required and not cleaned) or len(cleaned) > maximum or "\x00" in cleaned:
        raise ValidationError(f"{label}: contenido vacío o demasiado largo.")
    return cleaned
