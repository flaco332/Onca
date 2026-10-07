"""Typed data crossing the UI/service boundary; no widget or SQL dependencies."""
from datetime import date
from typing import NotRequired, TypedDict


class StudentDraft(TypedDict):
    first_name: NotRequired[str]
    last_name: NotRequired[str]
    name: NotRequired[str]
    student_id: NotRequired[int | None]
    phone: NotRequired[str]
    birth_date: NotRequired[str]
    emergency_contact_name: NotRequired[str]
    emergency_contact_phone: NotRequired[str]
    belt_rank: NotRequired[str]
    notes: NotRequired[str]
    has_medical: NotRequired[bool]
    last_payment_date: NotRequired[date]
    medical_cert_date: NotRequired[date]
    medical_cert_path: NotRequired[str]
