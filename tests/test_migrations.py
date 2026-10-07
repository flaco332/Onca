"""Deterministic schema upgrades and failure rollback, in memory only."""
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from app import migrations
from app.errors import DatabaseError


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.execute("PRAGMA foreign_keys=ON")

    def test_new_database_reaches_current(self):
        migrations.migrate_database(self.conn)
        self.assertEqual(migrations.get_schema_version(self.conn), migrations.CURRENT_SCHEMA_VERSION)

    def test_legacy_version_zero_adopted_preserving_rows(self):
        self.conn.executescript(Path(migrations.SCHEMA_PATH).read_text())
        self.conn.execute("INSERT INTO students(first_name,last_name) VALUES ('Alumno','Demo')")
        migrations.migrate_database(self.conn)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM students").fetchone()[0], 1)
        self.assertEqual(migrations.get_schema_version(self.conn), migrations.CURRENT_SCHEMA_VERSION)

    def test_previous_version_upgrades(self):
        migrations.apply_migration(self.conn, 1)
        migrations.migrate_database(self.conn)
        self.assertEqual(migrations.get_schema_version(self.conn), migrations.CURRENT_SCHEMA_VERSION)

    def test_repeated_migration_is_idempotent(self):
        migrations.migrate_database(self.conn)
        before = list(self.conn.execute("SELECT sql FROM sqlite_master ORDER BY name"))
        migrations.migrate_database(self.conn)
        self.assertEqual(list(self.conn.execute("SELECT sql FROM sqlite_master ORDER BY name")), before)

    def test_version_two_verification_defaults_false_and_preserves_reference(self):
        migrations.apply_migration(self.conn, 1)
        migrations.apply_migration(self.conn, 2)
        self.conn.execute("INSERT INTO students(first_name,last_name) VALUES ('Alumno','Demo')")
        self.conn.execute("INSERT INTO medical_certificates(student_id,issue_date,file_path) VALUES (1,'2026-01-01','certificados/demo.pdf')")
        migrations.migrate_database(self.conn)
        self.assertEqual(self.conn.execute("SELECT medical_verified FROM students").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT file_path FROM medical_certificates").fetchone()[0], "certificados/demo.pdf")

    def test_failed_version_three_rolls_back_column_and_marker(self):
        migrations.apply_migration(self.conn, 1)
        migrations.apply_migration(self.conn, 2)
        def broken(conn):
            migrations.MIGRATIONS[3](conn)
            raise DatabaseError("synthetic failure")
        with self.assertRaises(DatabaseError):
            migrations.apply_migration(self.conn, 3, broken)
        self.assertEqual(migrations.get_schema_version(self.conn), 2)
        self.assertNotIn("medical_verified", {r[1] for r in self.conn.execute("PRAGMA table_info(students)")})

    def test_failed_single_migration_rolls_back_ddl_and_version(self):
        def broken(conn):
            conn.execute("CREATE TABLE transient(value TEXT)")
            raise DatabaseError("synthetic failure")
        with self.assertRaises(DatabaseError):
            migrations.apply_migration(self.conn, 1, broken)
        self.assertEqual(migrations.get_schema_version(self.conn), 0)
        self.assertIsNone(self.conn.execute("SELECT name FROM sqlite_master WHERE name='transient'").fetchone())

    def test_failed_later_migration_rolls_back_whole_upgrade(self):
        def broken(conn):
            raise DatabaseError("synthetic failure")
        with patch.dict(migrations.MIGRATIONS, {2: broken}), self.assertRaises(DatabaseError):
            migrations.migrate_database(self.conn)
        self.assertEqual(migrations.get_schema_version(self.conn), 0)
        self.assertEqual(list(self.conn.execute("SELECT name FROM sqlite_master")), [])

    def test_newer_schema_refused(self):
        self.conn.execute("PRAGMA user_version=999")
        with self.assertRaises(DatabaseError):
            migrations.migrate_database(self.conn)
        self.assertEqual(migrations.get_schema_version(self.conn), 999)

    def test_incompatible_existing_schema_refused(self):
        self.conn.execute("CREATE TABLE students(student_id TEXT)")
        with self.assertRaises(DatabaseError):
            migrations.migrate_database(self.conn)
        self.assertEqual(migrations.get_schema_version(self.conn), 0)

    def test_nonconsecutive_migration_refused(self):
        with self.assertRaises(DatabaseError):
            migrations.apply_migration(self.conn, 2)

    def legacy_names(self):
        schema = Path(migrations.SCHEMA_PATH).read_text(encoding="utf-8")
        schema = schema.replace("first_name TEXT NOT NULL,\n    last_name TEXT NOT NULL,", "name TEXT NOT NULL,")
        schema = schema.replace("ON students(last_name, first_name)", "ON students(name)")
        self.conn.executescript(schema)
        self.conn.execute("INSERT INTO students(student_id,name) VALUES (7,'Alumno Compuesto Prueba Sintética')")
        self.conn.execute("INSERT INTO payments(student_id,amount,payment_date,payment_month) VALUES (7,100,'2026-10-01','2026-10')")

    def test_legacy_single_name_migrates_without_guessing(self):
        self.legacy_names()
        migrations.validate_schema(self.conn)
        migrations.migrate_database(self.conn)
        self.assertEqual(self.conn.execute("SELECT student_id,first_name,last_name FROM students").fetchone(),
                         (7, "Alumno Compuesto Prueba Sintética", ""))
        self.assertEqual(self.conn.execute("SELECT student_id FROM payments").fetchone()[0], 7)
        self.assertEqual(list(self.conn.execute("PRAGMA foreign_key_check")), [])
        self.assertEqual(migrations.get_schema_version(self.conn), 4)

    def test_version_three_preserves_separated_names_and_medical_state(self):
        for version in (1, 2, 3):
            migrations.apply_migration(self.conn, version)
        self.conn.execute("INSERT INTO students(student_id,first_name,last_name,medical_verified) VALUES (7,'Alumno Compuesto','Prueba Sintética',1)")
        migrations.migrate_database(self.conn)
        self.assertEqual(self.conn.execute("SELECT student_id,first_name,last_name,medical_verified FROM students").fetchone(),
                         (7, "Alumno Compuesto", "Prueba Sintética", 1))

    def test_failed_upgrade_rolls_back_legacy_name_conversion(self):
        self.legacy_names()
        def broken(conn):
            raise DatabaseError("fallo sintético")
        with patch.dict(migrations.MIGRATIONS, {4: broken}), self.assertRaises(DatabaseError):
            migrations.migrate_database(self.conn)
        self.assertEqual(self.conn.execute("SELECT student_id,name FROM students").fetchone(), (7, "Alumno Compuesto Prueba Sintética"))
        self.assertNotIn("last_name", {r[1] for r in self.conn.execute("PRAGMA table_info(students)")})
        self.assertEqual(migrations.get_schema_version(self.conn), 0)

    def test_legacy_init_creates_verified_backup_before_migration(self):
        import tempfile
        from contextlib import closing
        from app import database
        from app.backups import validate_backup
        self.legacy_names()
        self.conn.commit()
        with tempfile.TemporaryDirectory(prefix="onca-legacy-name-") as folder:
            root = Path(folder)
            db_path = root / "onca.db"
            with closing(sqlite3.connect(db_path)) as destination:
                self.conn.backup(destination)
            with patch.object(database, "DATA_FOLDER", folder), patch.object(database, "DB_PATH", str(db_path)):
                database.init_db()
                with database.get_connection() as conn:
                    self.assertEqual(conn.execute("SELECT first_name,last_name FROM students").fetchone()[:],
                                     ("Alumno Compuesto Prueba Sintética", ""))
            backup = next((root / "backups").iterdir())
            self.assertEqual(validate_backup(backup)["schema_version"], 0)
            with closing(sqlite3.connect(backup / "onca.db")) as conn:
                self.assertEqual(conn.execute("SELECT name FROM students").fetchone()[0], "Alumno Compuesto Prueba Sintética")
