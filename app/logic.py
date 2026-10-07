from datetime import date


PAYMENT_PERIOD_DAYS = 30


def days_until_payment(last_payment_date: date | None) -> int | None:
    """Un pago inexistente o incompleto no genera vencimiento artificial."""
    if last_payment_date is None:
        return None
    diff = (date.today() - last_payment_date).days
    return PAYMENT_PERIOD_DAYS - diff


def due_in_n_days(students, n_days=3):
    due = []

    for student in students:
        remaining = days_until_payment(student["last_payment_date"])

        if remaining is not None and 0 <= remaining <= n_days:
            due.append((student, remaining))

    return sorted(due, key=lambda item: item[1])


def pending_or_overdue_students(students, warn_days=3):
    pending = []

    for student in students:
        remaining = days_until_payment(student["last_payment_date"])

        if remaining is not None and remaining <= warn_days:
            pending.append((student, remaining))

    return sorted(pending, key=lambda item: item[1])


def append_reminder_log(log_path, due_students):
    """Legacy call compatibility: record only a fixed event, never personal values."""
    if due_students:
        from app.logging_config import log_event
        log_event("payment_reminder")
