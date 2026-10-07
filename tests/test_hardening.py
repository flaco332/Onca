"""Functional and failure-injection tests; every record/file is synthetic."""
from contextlib import closing
import json
import logging
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app import database, migrations, student_service as students
from app import payment_service as payments, activity_service as activities
from app import certificate_service as certificates
from app import activities_repository
from app.backups import create_backup, restore_backup, validate_backup, ensure_daily_backup, sha256_file
from app.errors import BackupError, DatabaseError, ValidationError, FileOperationError
from app.logging_config import configure_logging, log_event
from app.paths import managed_path


class IsolatedDatabase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="onca-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "current"
        self.root.mkdir()
        for key, value in (("DATA_FOLDER", str(self.root)), ("DB_PATH", str(self.root / "onca.db"))):
            mocked = patch.object(database, key, value)
            mocked.start()
            self.addCleanup(mocked.stop)
        database.init_db()
        self.student = students.save_student_to_db({"name": "Alumno Prueba Uno"})
        self.pdf = self.base / "synthetic.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\n% Synthetic attachment for tests only\n%%EOF\n")

    def scalar(self, query, parameters=()):
        with database.get_connection() as conn:
            return conn.execute(query, parameters).fetchone()[0]

    def attach(self):
        return certificates.attach_certificate(self.student, str(self.pdf), "2026-01-01")


class StudentTests(IsolatedDatabase):
    def test_create_and_lookup_by_id(self):
        self.assertEqual(self.scalar("SELECT first_name FROM students WHERE student_id=?", (self.student,)), "Alumno Prueba Uno")
        self.assertEqual(students.load_students_from_db()[0]["student_id"], self.student)

    def test_edit_preserves_id(self):
        result = students.save_student_to_db({"student_id": self.student, "name": "Alumno Prueba Editado"})
        self.assertEqual(result, self.student)
        self.assertEqual(self.scalar("SELECT count(*) FROM students"), 1)

    def test_homonyms_never_merge(self):
        # Fictitious identities requested to exercise homonyms, not real people.
        first = students.save_student_to_db({"name": "Alumno Homónimo Prueba"})
        second = students.save_student_to_db({"name": "Alumno Homónimo Prueba"})
        self.assertNotEqual(first, second)
        students.save_student_to_db({"student_id": second, "name": "Alumno Prueba Segundo"})
        self.assertEqual(self.scalar("SELECT first_name FROM students WHERE student_id=?", (first,)), "Alumno Homónimo Prueba")
        payments.add_payment(first, 1, "2026-01-01", "2026-01")
        self.assertEqual(payments.get_payments_by_student(second), [])
        certificates.attach_certificate(second, str(self.pdf), "2026-01-01")
        self.assertEqual(self.scalar("SELECT count(*) FROM medical_certificates WHERE student_id=?", (first,)), 0)

    def test_deactivate_preserves_history(self):
        payments.add_payment(self.student, 1, "2026-01-01", "2026-01")
        students.delete_student_from_db(self.student)
        self.assertEqual(students.load_students_from_db(), [])
        self.assertEqual(len(payments.get_payments_by_student(self.student)), 1)

    def test_missing_id_edit_refused(self):
        with self.assertRaises(ValidationError):
            students.save_student_to_db({"student_id": 999999, "name": "Alumno Prueba"})

    def test_invalid_fields_refused(self):
        for field, value in (("name", ""), ("phone", "no-phone"), ("birth_date", "2026-02-30"), ("student_id", True)):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                students.save_student_to_db({"name": "Alumno Prueba", field: value})

    def test_student_and_reference_rollback_together(self):
        before = self.scalar("SELECT count(*) FROM students")
        with self.assertRaises(ValidationError):
            students.save_student_to_db({"name": "Alumno Prueba", "medical_cert_path": "certificados/missing.pdf"})
        self.assertEqual(self.scalar("SELECT count(*) FROM students"), before)


class PaymentTests(IsolatedDatabase):
    def test_create_edit_delete(self):
        ident = payments.add_payment(self.student, 1, "2026-01-01", "2026-01")
        payments.update_payment(ident, 2, "2026-02-01", "2026-02")
        self.assertEqual(payments.get_payments_by_student(self.student)[0]["amount"], 2)
        payments.delete_payment(ident)
        self.assertEqual(payments.get_payments_by_student(self.student), [])

    def test_nonfinite_negative_or_zero_amounts_refused(self):
        for value in (float("nan"), float("inf"), -1, 0, 1e10):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                payments.add_payment(self.student, value, "2026-01-01", "2026-01")

    def test_invalid_month_refused(self):
        with self.assertRaises(ValidationError):
            payments.add_payment(self.student, 1, "2026-01-01", "2026-13")

    def test_inactive_student_refused(self):
        students.delete_student_from_db(self.student)
        with self.assertRaises(ValidationError):
            payments.add_payment(self.student, 1, "2026-01-01", "2026-01")

    def test_missing_payment_refused(self):
        with self.assertRaises(ValidationError):
            payments.delete_payment(999999)


class ActivityTests(IsolatedDatabase):
    def test_group_creation_and_relationships(self):
        other = students.save_student_to_db({"name": "Alumno Prueba Dos"})
        activities.create_activity_for_students([self.student, other], "Demo", "Otro", "2026-01-01")
        self.assertEqual(len(activities.get_activities_by_student(other)), 1)
        self.assertEqual(self.scalar("SELECT count(*) FROM extra_activities"), 1)

    def test_individual_group_edit_does_not_change_others(self):
        other = students.save_student_to_db({"name": "Alumno Prueba Dos"})
        activities.create_activity_for_students([self.student, other], "Original", "Otro", "2026-01-01")
        row = activities.get_activities_by_student(self.student)[0]
        activities.update_student_activity(row["student_activity_id"], "Editado", "Otro", "2026-01-02")
        self.assertEqual(activities.get_activities_by_student(other)[0]["title"], "Original")
        self.assertEqual(activities.get_activities_by_student(self.student)[0]["title"], "Editado")

    def test_deletion_cleans_only_orphan_activity(self):
        activities.create_activity_for_students([self.student], "Demo", "Otro", "2026-01-01")
        row = activities.get_activities_by_student(self.student)[0]
        activities.delete_student_activity(row["student_activity_id"])
        self.assertEqual(self.scalar("SELECT count(*) FROM extra_activities"), 0)

    def test_invalid_group_atomic(self):
        with self.assertRaises(ValidationError):
            activities.create_activity_for_students([self.student, 999999], "Demo", "Otro", "2026-01-01")
        self.assertEqual(self.scalar("SELECT count(*) FROM extra_activities"), 0)

    def test_repository_intermediate_failure_rolls_back(self):
        with self.assertRaises(sqlite3.IntegrityError):
            activities_repository.create_activity_for_students([self.student, 999999], "Demo", "Otro", "2026-01-01")
        self.assertEqual(self.scalar("SELECT count(*) FROM extra_activities"), 0)
        self.assertEqual(self.scalar("SELECT count(*) FROM student_activities"), 0)

    def test_shared_edit_failure_rolls_back_copy(self):
        other = students.save_student_to_db({"name": "Alumno Prueba Dos"})
        activities.create_activity_for_students([self.student, other], "Original", "Otro", "2026-01-01")
        row = activities.get_activities_by_student(self.student)[0]
        with self.assertRaises(sqlite3.IntegrityError):
            activities_repository.update_student_activity(row["student_activity_id"], "Changed", "Otro", "2026-01-01", paid_amount=-1)
        self.assertEqual(self.scalar("SELECT count(*) FROM extra_activities"), 1)
        self.assertEqual(activities.get_activities_by_student(self.student)[0]["title"], "Original")

    def test_duplicate_participation_refused(self):
        ident = activities.create_activity_for_students([self.student], "Demo", "Otro", "2026-01-01")
        with self.assertRaises(sqlite3.IntegrityError):
            activities_repository.add_student_to_activity(self.student, ident)


class CertificateTests(IsolatedDatabase):
    def test_attach_uses_relative_opaque_name(self):
        reference = self.attach()
        self.assertTrue(reference.startswith("certificados/"))
        self.assertFalse(Path(reference).is_absolute())
        self.assertNotIn("Alumno", reference)
        self.assertTrue(certificates.certificate_path(reference).is_file())

    def test_missing_file_refused(self):
        with self.assertRaises((ValidationError, FileOperationError)):
            certificates.attach_certificate(self.student, str(self.base / "missing.pdf"), "2026-01-01")
        self.assertEqual(self.scalar("SELECT count(*) FROM medical_certificates"), 0)

    def test_false_extension_refused(self):
        self.pdf.write_bytes(b"This is not a PDF")
        with self.assertRaises(ValidationError):
            self.attach()

    def test_database_failure_removes_only_new_file(self):
        original = self.attach()
        with patch("app.certificate_service.register_existing_reference", side_effect=sqlite3.OperationalError("synthetic")):
            with self.assertRaises(sqlite3.OperationalError):
                self.attach()
        self.assertEqual(list((self.root / "certificados").rglob("*.pdf")), [managed_path(self.root, original)])

    def test_remove_keeps_physical_file(self):
        reference = self.attach()
        certificates.remove_certificates(self.student)
        self.assertEqual(self.scalar("SELECT count(*) FROM medical_certificates"), 0)
        self.assertTrue(managed_path(self.root, reference).is_file())

    def test_managed_paths_reject_escape_and_windows_special_names(self):
        for value in ("../outside", "certificados/../../outside", "certificados\\..\\outside", "/absolute", "certificados/CON.pdf", "certificados/name. ", "certificados//file", "certificados/a:b"):
            with self.subTest(value=value), self.assertRaises((ValueError, ValidationError)):
                managed_path(self.root, value)

    def test_legacy_absolute_can_be_preserved_but_not_registered_new(self):
        with database.get_connection() as conn:
            conn.execute("INSERT INTO medical_certificates(student_id,file_path) VALUES (?,?)", (self.student, str(self.pdf)))
        students.save_student_to_db({"student_id": self.student, "name": "Alumno Prueba", "medical_cert_path": str(self.pdf)})
        other = students.save_student_to_db({"name": "Alumno Prueba Dos"})
        with self.assertRaises(ValidationError):
            students.save_student_to_db({"student_id": other, "name": "Alumno Prueba Dos", "medical_cert_path": str(self.pdf)})


class BackupTests(IsolatedDatabase):
    def test_create_validate_complete_with_unreferenced_files(self):
        reference = self.attach()
        extra = self.root / "certificados" / "unreferenced.pdf"
        extra.write_bytes(self.pdf.read_bytes())
        result = create_backup(self.root)
        manifest = validate_backup(result)
        self.assertEqual(len(manifest["files"]), 3)
        self.assertEqual(manifest["schema_version"], migrations.CURRENT_SCHEMA_VERSION)
        self.assertEqual(self.scalar("SELECT file_path FROM medical_certificates"), reference)

    def test_corrupt_checksum_refused(self):
        result = create_backup(self.root)
        with (result / "onca.db").open("ab") as handle:
            handle.write(b"corrupt")
        with self.assertRaises(BackupError):
            validate_backup(result)

    def test_invalid_database_even_with_matching_checksum_refused(self):
        result = create_backup(self.root)
        (result / "onca.db").write_bytes(b"not sqlite")
        manifest = json.loads((result / "manifest.json").read_text())
        manifest["files"]["onca.db"] = sha256_file(result / "onca.db")
        (result / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(BackupError):
            validate_backup(result)

    def test_extra_file_refused(self):
        result = create_backup(self.root)
        (result / "unexpected.txt").write_text("synthetic")
        with self.assertRaises(BackupError):
            validate_backup(result)

    def test_malformed_manifest_refused(self):
        result = create_backup(self.root)
        (result / "manifest.json").write_text("[]")
        with self.assertRaises(BackupError):
            validate_backup(result)

    def test_manifest_traversal_refused(self):
        result = create_backup(self.root)
        manifest = json.loads((result / "manifest.json").read_text())
        manifest["files"]["certificados/../../outside"] = "0" * 64
        (result / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(BackupError):
            validate_backup(result)

    def test_missing_attachment_prevents_incomplete_backup(self):
        ref = self.attach()
        managed_path(self.root, ref).unlink()
        with self.assertRaises(BackupError):
            create_backup(self.root)
        self.assertEqual(list((self.root / "backups").iterdir()), [])

    def test_legacy_reference_normalized_only_in_backup(self):
        with database.get_connection() as conn:
            conn.execute("INSERT INTO medical_certificates(student_id,file_path) VALUES (?,?)", (self.student, str(self.pdf)))
        result = create_backup(self.root)
        validate_backup(result)
        self.assertEqual(self.scalar("SELECT file_path FROM medical_certificates"), str(self.pdf))
        with closing(sqlite3.connect(result / "onca.db")) as conn:
            self.assertTrue(conn.execute("SELECT file_path FROM medical_certificates").fetchone()[0].startswith("certificados/"))

    def test_restore_into_new_directory_and_preserve_current(self):
        self.attach()
        result = create_backup(self.root)
        before = sha256_file(self.root / "onca.db")
        target = restore_backup(result, self.root, self.base / "restored")
        self.assertEqual(sha256_file(self.root / "onca.db"), before)
        self.assertEqual(len(list((self.root / "backups").iterdir())), 2)
        with closing(sqlite3.connect(target / "onca.db")) as conn:
            reference = conn.execute("SELECT file_path FROM medical_certificates").fetchone()[0]
            self.assertTrue(managed_path(target, reference).is_file())
        self.assertFalse((target / "manifest.json").exists())

    def test_restore_refuses_existing_and_nested_destination(self):
        result = create_backup(self.root)
        for destination in (self.root, self.root / "nested", result / "nested"):
            with self.subTest(destination=destination), self.assertRaises(BackupError):
                restore_backup(result, self.root, destination)

    def test_restore_migration_failure_preserves_current_and_backup(self):
        result = create_backup(self.root)
        before = sha256_file(self.root / "onca.db")
        with patch("app.migrations.migrate_database", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(BackupError):
                restore_backup(result, self.root, self.base / "restored")
        self.assertEqual(sha256_file(self.root / "onca.db"), before)
        self.assertFalse((self.base / "restored").exists())
        self.assertEqual(list(self.base.glob(".onca-restore-*")), [])
        self.assertEqual(len(list((self.root / "backups").iterdir())), 2)

    def test_daily_backup_created_only_once_if_valid(self):
        self.assertIsNotNone(ensure_daily_backup(self.root))
        self.assertIsNone(ensure_daily_backup(self.root))

    def test_corrupt_daily_backup_does_not_count(self):
        result = ensure_daily_backup(self.root)
        (result / "manifest.json").write_text("{}")
        self.assertIsNotNone(ensure_daily_backup(self.root))


class IntegrityTests(IsolatedDatabase):
    def test_database_link_refused_before_opening_sqlite(self):
        db_path = self.root / "onca.db"
        with patch("app.paths.is_link", side_effect=lambda path: path == db_path):
            with self.assertRaises(ValidationError):
                database.get_connection()
        # A refused connection releases the operation lock.
        self.assertEqual(self.scalar("PRAGMA integrity_check"), "ok")

    def test_foreign_keys_enabled_on_every_connection(self):
        self.assertEqual(self.scalar("PRAGMA foreign_keys"), 1)
        with database.get_connection() as conn, self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO payments(student_id,amount,payment_date,payment_month) VALUES (999999,1,'2026-01-01','2026-01')")

    def test_integrity_and_foreign_key_check(self):
        self.assertEqual(self.scalar("PRAGMA integrity_check"), "ok")
        with database.get_connection() as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_write_trigger_refuses_invalid_amount(self):
        with self.assertRaises(sqlite3.IntegrityError), database.get_connection() as conn:
            conn.execute("INSERT INTO payments(student_id,amount,payment_date,payment_month) VALUES (?,-1,'2026-01-01','2026-01')", (self.student,))

    def test_latest_payment_plan_uses_ordered_index(self):
        with database.get_connection() as conn:
            plan = " ".join(row[3] for row in conn.execute("EXPLAIN QUERY PLAN SELECT payment_date FROM payments WHERE student_id=? ORDER BY payment_date DESC,payment_id DESC LIMIT 1", (self.student,)))
        self.assertIn("idx_payments_latest", plan)
        self.assertNotIn("TEMP B-TREE", plan)

    def test_current_database_initialization_does_not_backup_again(self):
        database.init_db()
        self.assertFalse((self.root / "backups").exists())

    def test_legacy_initialization_backs_up_before_upgrade(self):
        with database.get_connection() as conn:
            conn.execute("ALTER TABLE students DROP COLUMN medical_verified")
            conn.execute("PRAGMA user_version=1")
        database.init_db()
        backups = list((self.root / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(validate_backup(backups[0])["schema_version"], 1)
        self.assertEqual(self.scalar("PRAGMA user_version"), migrations.CURRENT_SCHEMA_VERSION)


class LoggingTests(unittest.TestCase):
    def test_log_records_only_event_and_exception_class(self):
        with tempfile.TemporaryDirectory() as directory:
            configure_logging(Path(directory))
            log_event("unexpected_exception", ValueError("SYNTHETIC_PERSONAL_SENTINEL"))
            logger = logging.getLogger("onca.technical")
            for handler in logger.handlers:
                handler.flush()
            content = (Path(directory) / "logs/technical.log").read_text()
            self.assertIn("unexpected_exception", content)
            self.assertIn("ValueError", content)
            self.assertNotIn("SYNTHETIC_PERSONAL_SENTINEL", content)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            logger.addHandler(logging.NullHandler())


if __name__ == "__main__":
    unittest.main()
