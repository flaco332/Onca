"""Fechas, finanzas exactas y verificación con bases sintéticas temporales."""
from datetime import date
from decimal import Decimal
import sqlite3
import unittest

from app import activity_service, certificate_service, database, payment_service, student_service
from app.date_picker import date_from_parts
from app.errors import ValidationError, FieldValidationError
from app.validation import parse_date_field, parse_certificate_date, parse_amount, remaining_balance
from test_hardening import IsolatedDatabase


class DateRuleTests(unittest.TestCase):
    def test_canonical_iso(self):
        self.assertEqual(parse_date_field("2000-02-29"), "2000-02-29")

    def test_invalid_dates_and_format(self):
        for value in ("20000229", "2000-2-29", "1900-02-29", "2001-02-29", "2000-13-01"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_date_field(value)

    def test_birth_future(self):
        with self.assertRaises(ValidationError):
            parse_date_field("2026-10-07", "birth", today=date(2026, 10, 6))

    def test_certificate_future(self):
        with self.assertRaises(ValidationError):
            parse_certificate_date("2026-10-07", today=date(2026, 10, 6))
        self.assertEqual(parse_certificate_date("2026-10-06", today=date(2026, 10, 6)), "2026-10-06")

    def test_activity_and_payment_allow_future(self):
        for kind in ("activity", "payment"):
            self.assertEqual(parse_date_field("2035-10-07", kind), "2035-10-07")

    def test_leap_year_from_parts(self):
        self.assertEqual(date_from_parts(2000, 2, 29), "2000-02-29")
        with self.assertRaises(ValidationError):
            date_from_parts(1900, 2, 29)

    def test_empty_by_context(self):
        self.assertEqual(parse_date_field("", "birth", optional=True), "")
        for kind in ("activity", "certificate", "payment"):
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                parse_date_field("", kind)


class MoneyTests(unittest.TestCase):
    def test_partial_balance(self):
        self.assertEqual(remaining_balance("1200", "400"), Decimal("800.00"))

    def test_paid_in_full(self):
        self.assertEqual(remaining_balance("1200", "1200"), Decimal("0.00"))

    def test_overpaid(self):
        with self.assertRaisesRegex(ValidationError, "El monto pagado no puede ser mayor al costo total"):
            remaining_balance("1200", "1400")

    def test_negative_cost(self):
        with self.assertRaises(ValidationError):
            remaining_balance("-20", "0")

    def test_negative_paid(self):
        with self.assertRaises(ValidationError):
            remaining_balance("1200", "-20")

    def test_invalid_numbers(self):
        for value in ("abc", "--20", "NaN", "Infinity", "-Infinity", "1e3", "1000000000.01", "12.999", "12.000", "", " "):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_amount(value, allow_zero=True)

    def test_decimal_precision(self):
        self.assertEqual(remaining_balance("0.30", "0.10"), Decimal("0.20"))
        self.assertEqual(remaining_balance(Decimal("1200.50"), Decimal("400.25")), Decimal("800.25"))
        self.assertIsInstance(parse_amount("1200.50"), Decimal)

    def test_zero_by_context(self):
        self.assertEqual(remaining_balance("0", "0"), Decimal("0.00"))
        with self.assertRaises(ValidationError):
            parse_amount("0")


class FinancialPersistenceTests(IsolatedDatabase):
    def test_exact_service_values_round_trip(self):
        activity_service.create_activity_for_students([self.student], "Demo", "Otro", "2026-10-06", cost="0.30", paid_amount="0.10")
        row = activity_service.get_activities_by_student(self.student)[0]
        self.assertEqual(remaining_balance(row["cost"], row["paid_amount"]), Decimal("0.20"))
        payment_id = payment_service.add_payment(self.student, "1200.50", "2026-10-06", "2026-10")
        payment_service.update_payment(payment_id, Decimal("400.25"), "2026-10-06", "2026-10")
        self.assertEqual(parse_amount(payment_service.get_payments_by_student(self.student)[0]["amount"]), Decimal("400.25"))

    def test_overpayment_blocks_create_and_edit(self):
        with self.assertRaises(FieldValidationError):
            activity_service.create_activity_for_students([self.student], "Demo", "Otro", "2026-10-06", cost=1200, paid_amount=1400)
        self.assertEqual(self.scalar("SELECT count(*) FROM extra_activities"), 0)
        activity_service.create_activity_for_students([self.student], "Demo", "Otro", "2026-10-06", cost=1200, paid_amount=400)
        row = activity_service.get_activities_by_student(self.student)[0]
        with self.assertRaises(FieldValidationError):
            activity_service.update_student_activity(row["student_activity_id"], "Cambio", "Otro", "2026-10-06", cost=1200, paid_amount=1400)
        self.assertEqual(activity_service.get_activities_by_student(self.student)[0]["title"], "Demo")

    def test_optional_location_still_offline(self):
        activity_service.create_activity_for_students([self.student], "Demo", "Otro", "2026-10-06", location="", cost=0, paid_amount=0)
        self.assertEqual(activity_service.get_activities_by_student(self.student)[0]["location"], "")


class MedicalAutosaveTests(IsolatedDatabase):
    def test_verify_and_unverify_with_explicit_date(self):
        certificate_service.set_medical_verification(self.student, True, "2026-10-01")
        row = student_service.load_students_from_db()[0]
        self.assertTrue(row["has_medical"])
        self.assertEqual(row["medical_cert_date"], date(2026, 10, 1))
        self.assertEqual(row["medical_cert_path"], "")
        certificate_service.set_medical_verification(self.student, False)
        self.assertFalse(student_service.load_students_from_db()[0]["has_medical"])

    def test_repeated_verification_keeps_one_metadata_record(self):
        for day in ("2026-10-01", "2026-10-02"):
            certificate_service.set_medical_verification(self.student, True, day)
        self.assertEqual(self.scalar("SELECT count(*) FROM medical_certificates"), 1)
        self.assertEqual(self.scalar("SELECT issue_date FROM medical_certificates"), "2026-10-02")

    def test_invalid_and_empty_date_do_not_verify(self):
        for value in ("", "2026-02-30", "2999-01-01"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                certificate_service.set_medical_verification(self.student, True, value)
        self.assertFalse(student_service.load_students_from_db()[0]["has_medical"])

    def test_failure_rolls_back_state_and_date(self):
        with database.get_connection() as conn:
            conn.execute("CREATE TRIGGER reject_date BEFORE INSERT ON medical_certificates BEGIN SELECT RAISE(ABORT,'synthetic_failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            certificate_service.set_medical_verification(self.student, True, "2026-10-01")
        self.assertFalse(student_service.load_students_from_db()[0]["has_medical"])
        self.assertEqual(self.scalar("SELECT count(*) FROM medical_certificates"), 0)

    def test_existing_attachment_preserved(self):
        reference = self.attach()
        certificate_service.set_medical_verification(self.student, True, "2026-10-01")
        self.assertEqual(self.scalar("SELECT count(*) FROM medical_certificates"), 1)
        row = student_service.load_students_from_db()[0]
        self.assertEqual(row["medical_cert_path"], reference)
        self.assertEqual(row["medical_cert_date"], date(2026, 10, 1))

    def test_attachment_after_verification_reuses_metadata(self):
        certificate_service.set_medical_verification(self.student, True, "2026-10-05")
        reference = self.attach()
        self.assertEqual(self.scalar("SELECT count(*) FROM medical_certificates"), 1)
        row = student_service.load_students_from_db()[0]
        self.assertTrue(row["has_medical"])
        self.assertEqual(row["medical_cert_path"], reference)
        self.assertEqual(row["medical_cert_date"], date(2026, 1, 1))

    def test_backup_restore_of_date_without_attachment(self):
        from contextlib import closing
        from app.backups import create_backup, restore_backup
        certificate_service.set_medical_verification(self.student, True, "2026-10-01")
        backup = create_backup(self.root)
        restored = self.base / "restored"
        restore_backup(backup, self.root, restored)
        with closing(sqlite3.connect(restored / "onca.db")) as conn:
            self.assertEqual(conn.execute("SELECT medical_verified FROM students").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT issue_date,file_path FROM medical_certificates").fetchone(), ("2026-10-01", ""))

    def test_inactive_student_and_invalid_state(self):
        with self.assertRaises(ValidationError):
            certificate_service.set_medical_verification(self.student, 1, "2026-10-01")
        student_service.delete_student_from_db(self.student)
        with self.assertRaises(ValidationError):
            certificate_service.set_medical_verification(self.student, True, "2026-10-01")

    def test_attachment_rejects_future_date(self):
        with self.assertRaises(ValidationError):
            certificate_service.attach_certificate(self.student, str(self.pdf), "2999-01-01")
