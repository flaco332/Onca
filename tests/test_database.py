import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import database
from app.students_repository import add_student, get_students
from app.payments_repository import add_payment, get_payments_by_student
from app.activities_repository import create_activity_for_students, get_activities_by_student


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.addCleanup(patch.stopall)
        patch.object(database, "DATA_FOLDER", str(self.folder)).start()
        patch.object(database, "DB_PATH", str(self.folder / "onca.db")).start()
        database.init_db()

    def test_first_start_is_empty_and_reinitialization_preserves_data(self):
        self.assertEqual(get_students(), [])
        student = add_student("Alumno", "Demo Uno")
        database.init_db()
        self.assertEqual(get_students()[0]["student_id"], student)
        self.assertEqual(len(get_students()), 1)

    def test_synthetic_payments_activities_and_foreign_keys(self):
        student = add_student("Alumno", "Demo Dos")
        add_payment(student, 1.0, "2026-01-01", "2026-01", "Demo")
        create_activity_for_students([student], "Actividad Demo", "Otro", "2026-01-02")
        self.assertEqual(len(get_payments_by_student(student)), 1)
        self.assertEqual(len(get_activities_by_student(student)), 1)
        with self.assertRaises(sqlite3.IntegrityError):
            add_payment(999999, 1.0, "2026-01-01", "2026-01")

    def test_failed_group_activity_rolls_back(self):
        student = add_student("Alumno", "Demo Tres")
        with self.assertRaises(sqlite3.IntegrityError):
            create_activity_for_students([student, 999999], "Demo", "Otro", "2026-01-02")
        self.assertEqual(get_activities_by_student(student), [])

    def test_context_manager_closes_connection(self):
        with database.get_connection() as conn:
            conn.execute("SELECT 1")
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
