"""Compatibility imports for older callers; UI now calls the student service."""
from app.student_service import (load_students_from_db, save_student_to_db,
                                delete_student_from_db, split_name, join_name)
