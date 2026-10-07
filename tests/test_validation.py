import unittest

from app.validation import (
    validate_person_name,
    validate_phone,
    normalize_activity_status,
    activity_status_label,
)


class ValidationTests(unittest.TestCase):
    def test_person_name_accepts_spanish_letters_and_accents(self):
        self.assertTrue(validate_person_name("Alumno Prueba"))
        self.assertTrue(validate_person_name("Ejémplo Fictício"))
        self.assertTrue(validate_person_name("Demo-Sintético"))
        self.assertTrue(validate_person_name("Alumno Ficticio"))

    def test_person_name_rejects_numbers_and_symbols(self):
        self.assertFalse(validate_person_name("Prueba123"))
        self.assertFalse(validate_person_name("Prueba@"))
        self.assertFalse(validate_person_name("👩‍💻"))

    def test_phone_accepts_only_digits(self):
        self.assertTrue(validate_phone("0000000000"))
        self.assertTrue(validate_phone("1111111111"))

    def test_phone_rejects_letters(self):
        self.assertFalse(validate_phone("222abc4567"))
        self.assertTrue(validate_phone("222 123 4567"))
        self.assertTrue(validate_phone("222-123-4567"))

    def test_activity_status_mapping_is_spanish(self):
        self.assertEqual(normalize_activity_status("registered"), "registered")
        self.assertEqual(activity_status_label("registered"), "Pendiente")
        self.assertEqual(activity_status_label("attended"), "Asistió")
        self.assertEqual(activity_status_label("cancelled"), "Cancelado")


if __name__ == "__main__":
    unittest.main()
