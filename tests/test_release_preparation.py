"""Preparación de RC, primer inicio y exclusiones sin compilar ni datos reales."""
import ast
from contextlib import closing
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import run
from app import database, paths, student_service
from app.logging_config import logger
from app.migrations import CURRENT_SCHEMA_VERSION
from app.version import __version__, windows_version
from tools.public_snapshot import export_snapshot, validate_source_file

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("students", "payments", "medical_certificates", "extra_activities", "student_activities")


class VersionTests(unittest.TestCase):
    def test_rc_and_stable_windows_versions(self):
        self.assertEqual(windows_version("0.9.0-rc1"), (0, 9, 0, 0))
        self.assertEqual(windows_version("1.0.0"), (1, 0, 0, 0))
        self.assertEqual(len(windows_version()), 4)

    def test_invalid_and_oversized_versions(self):
        for value in ("1.0", "01.0.0", "1.0.0-rc0", "1.0.0-preview", "65536.0.0"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                windows_version(value)

    def test_spec_rc_metadata_without_running_build(self):
        class Info:
            def __init__(self, *args, **kwargs):
                self.args, self.kwargs = args, kwargs
        module = SimpleNamespace(**{name: Info for name in ("VSVersionInfo", "FixedFileInfo", "StringFileInfo", "StringTable", "StringStruct", "VarFileInfo", "VarStruct")})
        tree = ast.parse((ROOT / "OncaAlumnos.spec").read_text(encoding="utf-8"))
        prefix = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "Analysis":
                break
            prefix.append(node)
        scope = {"SPECPATH": str(ROOT)}
        with patch.dict(sys.modules, {"PyInstaller.utils.win32.versioninfo": module}):
            exec(compile(ast.Module(body=prefix, type_ignores=[]), "metadata-only", "exec"), scope)
        self.assertEqual(scope["version"], __version__)
        self.assertEqual(scope["version_info"].kwargs["ffi"].kwargs["filevers"], windows_version())
        self.assertEqual(scope["version_info"].kwargs["ffi"].kwargs["flags"], 2)


class FirstRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="onca-first-run-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for module, name, value in ((database, "DATA_FOLDER", str(self.root)), (database, "DB_PATH", str(self.root / "onca.db")), (run, "DB_PATH", str(self.root / "onca.db"))):
            mocked = patch.object(module, name, value)
            mocked.start()
            self.addCleanup(mocked.stop)
        self.addCleanup(self.close_logs)

    def close_logs(self):
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    def counts(self):
        with closing(sqlite3.connect(self.root / "onca.db")) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], CURRENT_SCHEMA_VERSION)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            return [conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in TABLES]

    def test_new_install_and_restart_remain_empty(self):
        for _ in range(2):
            self.assertTrue(run.prepare_data(smoke=True))
            self.assertEqual(self.counts(), [0] * len(TABLES))
            for folder in ("certificados", "backups", "logs"):
                self.assertTrue((self.root / folder).is_dir())
        self.assertEqual(list((self.root / "certificados").iterdir()), [])
        self.assertEqual(list((self.root / "backups").iterdir()), [])

    def test_regular_start_only_creates_empty_daily_backup(self):
        from app.backups import validate_backup
        for _ in range(2):
            self.assertTrue(run.prepare_data())
        self.assertEqual(self.counts(), [0] * len(TABLES))
        backups = list((self.root / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(validate_backup(backups[0])["schema_version"], CURRENT_SCHEMA_VERSION)

    def test_user_record_survives_reinitialization(self):
        run.prepare_data(smoke=True)
        student_id = student_service.save_student_to_db({"first_name": "Alumno", "last_name": "Prueba"})
        run.prepare_data(smoke=True)
        self.assertEqual(self.counts(), [1, 0, 0, 0, 0])
        self.assertEqual(student_service.load_students_from_db()[0]["student_id"], student_id)

    def test_frozen_program_files_does_not_define_data_location(self):
        with patch.dict("os.environ", {"LOCALAPPDATA": str(self.root / "local")}, clear=True), patch.object(sys, "platform", "win32"), patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(self.root / "Program Files/OncaAlumnos.exe")):
            self.assertEqual(paths.get_data_dir(), str(self.root / "local/OncaAlumnos"))


class SnapshotTests(unittest.TestCase):
    def archive(self, files):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return buffer.getvalue()

    def test_private_artifacts_and_traversal_rejected(self):
        for name in ("app/onca.db", "docs/user.pdf", "app/secret.key", "app/logs/private.txt", ".private/report.md", "../README.md", "app/../private.py", "app/data/demo.csv", "docs/alumnos.csv", "app/alumnos.json", "docs/payments.xlsx"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_source_file(name, b"synthetic")

    def test_structured_fixture_is_allowed_only_under_tests(self):
        validate_source_file("tests/fixtures/synthetic.json", b'{"synthetic":true}')

    def test_secret_pattern_rejected_without_disclosing_value(self):
        token = ("gh" + "p_" + "A" * 36).encode()
        with self.assertRaises(ValueError) as error:
            validate_source_file("app/config.py", token)
        self.assertNotIn(token.decode(), str(error.exception))

    def test_symlinks_and_binaries_rejected(self):
        for data, mode in ((b"outside", 0o120777), (b"binary\x00content", 0o100644)):
            with self.assertRaises(ValueError):
                validate_source_file("app/example.py", data, mode=mode)

    def test_only_reviewed_source_and_synthetic_tests_exported(self):
        data = self.archive({"app/version.py": b"synthetic", "tests/fixtures/example.py": b"synthetic", "docs/changes/internal.md": b"internal"})
        with tempfile.TemporaryDirectory() as folder, patch("tools.public_snapshot.subprocess.run", return_value=SimpleNamespace(returncode=0)), patch("tools.public_snapshot.subprocess.check_output", return_value=data):
            output = Path(folder) / "candidate"
            self.assertEqual(export_snapshot(ROOT, output), 2)
            self.assertTrue((output / "tests/fixtures/example.py").exists())
            self.assertFalse((output / "docs/changes").exists())
            self.assertFalse((output / ".git").exists())

    def test_existing_candidate_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder, patch("tools.public_snapshot.subprocess.run", return_value=SimpleNamespace(returncode=0)), patch("tools.public_snapshot.subprocess.check_output", return_value=self.archive({"README.md": b"synthetic"})):
            output = Path(folder)
            marker = output / "sentinel.txt"
            marker.write_text("synthetic", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                export_snapshot(ROOT, output)
            self.assertEqual(marker.read_text(), "synthetic")
            self.assertEqual(list(output.iterdir()), [marker])

    def test_dirty_head_not_exported(self):
        with patch("tools.public_snapshot.subprocess.run", return_value=SimpleNamespace(returncode=1)), patch("tools.public_snapshot.subprocess.check_output") as archive:
            with self.assertRaises(ValueError):
                export_snapshot(ROOT, ROOT / "never-created")
            archive.assert_not_called()


class ThirdPartyNoticeTests(unittest.TestCase):
    def test_license_and_vendor_notice_preserved_without_build(self):
        from build_release import copy_third_party_notices
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runtime = root / "runtime"
            runtime.mkdir()
            (runtime / "LICENSE.txt").write_text("synthetic Python terms", encoding="utf-8")
            source = root / "source"
            (source / "third_party_licenses").mkdir(parents=True)
            (source / "third_party_licenses/Tcl-license.terms").write_text("synthetic Tcl terms", encoding="utf-8")
            (source / "THIRD_PARTY_NOTICES.md").write_text("synthetic summary", encoding="utf-8")
            (source / "LICENSE").write_text("synthetic project license", encoding="utf-8")
            (source / "NOTICE").write_text("synthetic project attribution", encoding="utf-8")
            package = root / "installed"
            (package / "vendor").mkdir(parents=True)
            (package / "vendor/NOTICE").write_text("synthetic vendor attribution", encoding="utf-8")
            dist = SimpleNamespace(files=[Path("vendor/NOTICE")], locate_file=lambda file: package / file)
            output = root / "candidate"
            output.mkdir()
            with patch("build_release.sys.base_prefix", str(runtime)), patch("build_release.distribution", return_value=dist), patch("build_release.subprocess.run") as build:
                copy_third_party_notices(source, output)
                build.assert_not_called()
            self.assertEqual((output / "THIRD_PARTY_NOTICES/setuptools/vendor/NOTICE").read_text(), "synthetic vendor attribution")
            self.assertTrue((output / "THIRD_PARTY_NOTICES/Tcl-license.terms").exists())
            self.assertEqual((output / "LICENSE").read_text(), "synthetic project license")
            self.assertEqual((output / "NOTICE").read_text(), "synthetic project attribution")
            self.assertFalse(any(output.rglob("*.exe")))
