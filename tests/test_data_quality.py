"""Regresiones de calidad de datos con ejemplos completamente sintéticos."""
from datetime import date
import unittest

from app.errors import FieldValidationError, ValidationError
from app.student_service import validate_student
from app.validation import validate_phone, phone_error, parse_birth_date
from app.student_options import BELT_RANKS
from app.logic import days_until_payment, pending_or_overdue_students
from test_hardening import IsolatedDatabase
from app import database, student_service, payment_service, activity_service, certificate_service
from app.date_picker import birth_date_from_parts


class PhoneTests(unittest.TestCase):
    def test_mexican(self):
        self.assertTrue(validate_phone("55 0000 0000"))

    def test_country_code(self):
        self.assertTrue(validate_phone("+52 55 0000 0000"))

    def test_spaces(self):
        self.assertTrue(validate_phone(" 55 0000 0000 "))

    def test_parentheses(self):
        self.assertTrue(validate_phone("(55) 0000 0000"))

    def test_hyphens(self):
        self.assertTrue(validate_phone("55-0000-0000"))

    def test_international(self):
        self.assertTrue(validate_phone("+1 (202) 555-0123"))

    def test_letters(self):
        self.assertIn("Usa solo", phone_error("55 abc0 0000"))

    def test_invalid_characters(self):
        for value in ("55/0000/0000", "５５００００００００", "5500000000\n", "5500000000@"):
            with self.subTest(value=value):
                self.assertFalse(validate_phone(value))

    def test_short(self):
        self.assertIn("pocos", phone_error("+52 12"))

    def test_long(self):
        self.assertIn("demasiados dígitos", phone_error("1234567890123456"))

    def test_invalid_format(self):
        for value in ("55+00000000", "++5500000000", "(5500000000", "((55))00000000"):
            self.assertFalse(validate_phone(value))

    def test_optional_and_both_fields(self):
        self.assertEqual(phone_error(""), "")
        result = validate_student({"name": "Alumno Prueba", "phone": "+52 55 0000 0000", "emergency_contact_phone": "+1 (202) 555-0123"})
        self.assertEqual(result["phone"], "+52 55 0000 0000")
        with self.assertRaises(FieldValidationError) as error:
            validate_student({"name": "Alumno Prueba", "phone": "abc", "emergency_contact_phone": "12"})
        self.assertEqual(set(error.exception.errors), {"phone", "emergency_contact_phone"})


class BirthDateTests(unittest.TestCase):
    def test_picker_parts(self):
        self.assertEqual(birth_date_from_parts(2000, 2, 29), "2000-02-29")
        with self.assertRaises(ValidationError):
            birth_date_from_parts(1900, 2, 29)

    def test_historical_and_leap_year(self):
        self.assertEqual(parse_birth_date("1900-01-01"), "1900-01-01")
        self.assertEqual(parse_birth_date("2000-02-29"), "2000-02-29")

    def test_today(self):
        self.assertEqual(parse_birth_date("2026-10-05", today=date(2026, 10, 5)), "2026-10-05")

    def test_future(self):
        with self.assertRaises(ValidationError):
            parse_birth_date("2026-10-06", today=date(2026, 10, 5))

    def test_invalid_and_optional(self):
        self.assertEqual(parse_birth_date(""), "")
        for value in ("20010912", "1900-02-29", "2001-13-01"):
            with self.assertRaises(ValidationError):
                parse_birth_date(value)


class StudentStateTests(IsolatedDatabase):
    def row(self):
        return student_service.load_students_from_db(today=date(2026, 10, 5))[0]

    def test_belt_options_are_independent(self):
        self.assertEqual(len(BELT_RANKS), 15)
        self.assertEqual(len(set(BELT_RANKS)), 15)
        for value in ("Marrón", "Marrón avanzada", "Roja", "Roja avanzada"):
            self.assertIn(value, BELT_RANKS)
        self.assertNotIn("MarrónMarrón avanzadaRoja", BELT_RANKS)

    def test_new_student_has_no_payment(self):
        self.assertIsNone(self.row()["last_payment_date"])
        self.assertIsNone(days_until_payment(None))
        self.assertEqual(pending_or_overdue_students([self.row()]), [])

    def test_recorded_payment_date(self):
        payment_service.add_payment(self.student, 1, "2026-10-03", "2026-10")
        self.assertEqual(self.row()["last_payment_date"], date(2026, 10, 3))
        self.assertEqual(days_until_payment(date.today()), 30)

    def test_date_in_form_does_not_create_payment(self):
        student_service.save_student_to_db({"student_id": self.student, "name": "Alumno Prueba", "last_payment_date": date(2026, 10, 3)})
        self.assertIsNone(self.row()["last_payment_date"])

    def test_incomplete_legacy_payment(self):
        with database.get_connection() as conn:
            conn.execute("INSERT INTO payments(student_id,amount,payment_date,payment_month) VALUES (?,1,'','')", (self.student,))
        self.assertIsNone(self.row()["last_payment_date"])

    def test_attachment_does_not_verify(self):
        self.attach()
        self.assertFalse(self.row()["has_medical"])

    def test_verification_persists_and_is_independent(self):
        student_service.save_student_to_db({"student_id": self.student, "name": "Alumno Prueba", "has_medical": True})
        self.assertTrue(self.row()["has_medical"])
        student_service.save_student_to_db({"student_id": self.student, "name": "Alumno Editado"})
        self.assertTrue(self.row()["has_medical"])
        student_service.save_student_to_db({"student_id": self.student, "name": "Alumno Prueba", "has_medical": False})
        self.assertFalse(self.row()["has_medical"])

    def test_remove_certificate_resets_verification(self):
        self.attach()
        student_service.save_student_to_db({"student_id": self.student, "name": "Alumno Prueba", "has_medical": True})
        certificate_service.remove_certificates(self.student)
        self.assertFalse(self.row()["has_medical"])

    def test_medical_boolean_constraint(self):
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError), database.get_connection() as conn:
            conn.execute("UPDATE students SET medical_verified=2 WHERE student_id=?", (self.student,))

    def test_backup_restore_preserves_medical_verification(self):
        from contextlib import closing
        import sqlite3
        from app.backups import create_backup, restore_backup
        student_service.save_student_to_db({"student_id": self.student, "name": "Alumno Prueba", "has_medical": True})
        backup = create_backup(self.root)
        restored = self.base / "restored"
        restore_backup(backup, self.root, restored)
        with closing(sqlite3.connect(restored / "onca.db")) as conn:
            self.assertEqual(conn.execute("SELECT medical_verified FROM students WHERE student_id=?", (self.student,)).fetchone()[0], 1)

    def test_no_upcoming_activity(self):
        self.assertEqual(self.row()["next_activity_date"], "")

    def test_nearest_upcoming_not_cancelled(self):
        for day, status in (("2026-10-01", "registered"), ("2026-10-06", "cancelled"), ("2026-10-07", "absent"), ("2026-10-09", "confirmed"), ("2026-10-12", "registered")):
            activity_service.create_activity_for_students([self.student], "Actividad Demo", "Otro", day, attendance_status=status)
        self.assertEqual(self.row()["next_activity_date"], "2026-10-09")

    def test_today_activity_and_other_student(self):
        other = student_service.save_student_to_db({"name": "Alumno Otro"})
        activity_service.create_activity_for_students([other], "Actividad Demo", "Otro", "2026-10-05")
        rows = {r["student_id"]: r for r in student_service.load_students_from_db(today=date(2026, 10, 5))}
        self.assertEqual(rows[self.student]["next_activity_date"], "")
        self.assertEqual(rows[other]["next_activity_date"], "2026-10-05")

    def test_listing_uses_one_select(self):
        from unittest.mock import patch
        connection = database.get_connection()
        statements = []
        connection.set_trace_callback(statements.append)
        with patch("app.students_repository.get_connection", return_value=connection):
            student_service.load_students_from_db(today=date(2026, 10, 5))
        self.assertEqual(sum(s.lstrip().upper().startswith("SELECT") for s in statements), 1)
