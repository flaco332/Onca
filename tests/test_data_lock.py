"""Locks coordinate cooperating threads/processes without inspecting user data."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from app.data_access import data_operation


class DataLockTests(unittest.TestCase):
    def test_reentrant_and_released_after_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError), data_operation(root):
                with data_operation(root):
                    raise ValueError("synthetic")
            with data_operation(root):
                pass
            self.assertEqual((root / ".operation.lock").read_bytes(), b"0")

    def test_other_process_cannot_enter_locked_operation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = """
from pathlib import Path
import sys
from app.data_access import data_operation
try:
    with data_operation(Path(sys.argv[1]), timeout=0.1):
        raise AssertionError('Lock not enforced')
except TimeoutError:
    print('locked')
"""
            with data_operation(root):
                result = subprocess.run([sys.executable, "-c", script, str(root)],
                                        cwd=Path(__file__).resolve().parents[1],
                                        capture_output=True, text=True, timeout=10, check=True)
            self.assertEqual(result.stdout.strip(), "locked")

    def test_threads_serialize_operations(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ready, release = threading.Event(), threading.Event()
            order = []
            def first():
                with data_operation(root):
                    order.append("first")
                    ready.set()
                    if not release.wait(5):
                        raise AssertionError("Test worker timeout")
                    order.append("first-done")
            def second():
                with data_operation(root):
                    order.append("second")
            with ThreadPoolExecutor(max_workers=2) as workers:
                first_result = workers.submit(first)
                self.assertTrue(ready.wait(5))
                second_result = workers.submit(second)
                release.set()
                first_result.result(timeout=5)
                second_result.result(timeout=5)
            self.assertEqual(order, ["first", "first-done", "second"])
