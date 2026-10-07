"""Nombres separados, compatibilidad y búsquedas con datos sintéticos."""
import unittest
from unittest.mock import patch

from app import database, student_service as students
from app.errors import FieldValidationError
from test_hardening import IsolatedDatabase


class DisplayNameTests(unittest.TestCase):
    def test_compound_name(self):
        self.assertEqual(students.display_name(" Alumno Compuesto ", " Prueba Sintética "), "Alumno Compuesto Prueba Sintética")

    def test_missing_surnames(self):
        for surname in (None, "", " "):
            self.assertEqual(students.display_name("Prueba", surname), "Prueba")

    def test_empty_parts(self):
        self.assertEqual(students.display_name(None, None), "")

    def test_field_validation(self):
        clean = students.validate_student({"first_name": "Prueba Ñora", "last_name": "Prueba-Compuesta O'Ensayo"})
        self.assertEqual(clean["name"], "Prueba Ñora Prueba-Compuesta O'Ensayo")
        for field, value in (("first_name", ""), ("first_name", "Prueba12"), ("last_name", "Prueba2")):
            with self.subTest(field=field), self.assertRaises(FieldValidationError) as error:
                students.validate_student({"first_name": "Prueba", field: value})
            self.assertIn(field, error.exception.errors)


class StudentNameTests(IsolatedDatabase):
    def named_student(self):
        return students.save_student_to_db({"first_name": "Alumno Compuesto", "last_name": "Ensayo Sintético"})

    def test_name_and_surnames_round_trip(self):
        student_id = self.named_student()
        row = next(row for row in students.load_students_from_db() if row["student_id"] == student_id)
        self.assertEqual((row["first_name"], row["last_name"], row["name"]),
                         ("Alumno Compuesto", "Ensayo Sintético", "Alumno Compuesto Ensayo Sintético"))

    def test_optional_surnames(self):
        student_id = students.save_student_to_db({"first_name": "Prueba"})
        self.assertEqual(self.scalar("SELECT last_name FROM students WHERE student_id=?", (student_id,)), "")

    def test_legacy_draft_not_split(self):
        student_id = students.save_student_to_db({"name": "Alumno Compuesto Prueba Sintética"})
        with database.get_connection() as conn:
            row = conn.execute("SELECT first_name,last_name FROM students WHERE student_id=?", (student_id,)).fetchone()
        self.assertEqual(tuple(row), ("Alumno Compuesto Prueba Sintética", ""))

    def test_edit_surnames_preserves_id_and_history(self):
        from app.payment_service import add_payment, get_payments_by_student
        student_id = self.named_student()
        add_payment(student_id, 100, "2026-10-01", "2026-10")
        result = students.save_student_to_db({"student_id": student_id, "first_name": "Alumno Compuesto", "last_name": "Prueba-Compuesta"})
        self.assertEqual(result, student_id)
        self.assertEqual(self.scalar("SELECT last_name FROM students WHERE student_id=?", (student_id,)), "Prueba-Compuesta")
        self.assertEqual(len(get_payments_by_student(student_id)), 1)
        students.save_student_to_db({"student_id": student_id, "first_name": "Alumno Compuesto", "last_name": ""})
        self.assertEqual(self.scalar("SELECT last_name FROM students WHERE student_id=?", (student_id,)), "")

    def test_loaded_draft_preserves_existing_separation(self):
        student_id = self.named_student()
        draft = next(row for row in students.load_students_from_db() if row["student_id"] == student_id)
        draft["phone"] = "+52 55 0000 0000"
        students.save_student_to_db(draft)
        self.assertEqual(self.scalar("SELECT first_name FROM students WHERE student_id=?", (student_id,)), "Alumno Compuesto")
        self.assertEqual(self.scalar("SELECT last_name FROM students WHERE student_id=?", (student_id,)), "Ensayo Sintético")

    def test_search_first_name(self):
        student_id = self.named_student()
        self.assertEqual([r["student_id"] for r in students.load_students_from_db(search="alumno compuesto")], [student_id])

    def test_legacy_update_preserves_existing_separation(self):
        student_id = self.named_student()
        students.save_student_to_db({"student_id": student_id, "name": "Alumno Compuesto Ensayo Sintético", "has_medical": True})
        self.assertEqual(self.scalar("SELECT first_name FROM students WHERE student_id=?", (student_id,)), "Alumno Compuesto")
        self.assertEqual(self.scalar("SELECT last_name FROM students WHERE student_id=?", (student_id,)), "Ensayo Sintético")

    def test_search_surnames(self):
        student_id = self.named_student()
        self.assertEqual([r["student_id"] for r in students.load_students_from_db(search=" ENSAYO ")], [student_id])

    def test_search_full_name(self):
        student_id = self.named_student()
        self.assertEqual([r["student_id"] for r in students.load_students_from_db(search="Alumno Compuesto Ensayo Sintético")], [student_id])

    def test_search_no_extra_queries_or_sql_interpolation(self):
        self.named_student()
        connection = database.get_connection()
        statements = []
        connection.set_trace_callback(statements.append)
        with patch("app.students_repository.get_connection", return_value=connection):
            self.assertEqual(students.load_students_from_db(search="' OR 1=1 --"), [])
        self.assertEqual(sum(s.lstrip().upper().startswith("SELECT") for s in statements), 1)
