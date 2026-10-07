"""No Tk calls are allowed from worker threads; deterministic queue checks."""
import threading
import unittest
from app.background_tasks import BackgroundTasks


class FakeRoot:
    def __init__(self):
        self.thread = threading.get_ident()

    def after(self, delay, callback):
        assert threading.get_ident() == self.thread


class FakeStatus:
    def __init__(self):
        self.thread = threading.get_ident()

    def set(self, value):
        assert threading.get_ident() == self.thread


class WorkerTests(unittest.TestCase):
    def test_result_delivered_on_main_thread(self):
        tasks = BackgroundTasks(FakeRoot(), FakeStatus(), lambda value: None)
        self.addCleanup(tasks.close)
        main = threading.get_ident()
        result = []
        tasks.start("Working", threading.get_ident, lambda value: result.append((value, threading.get_ident())), self.fail)
        tasks.executor.shutdown(wait=True)
        tasks._poll()
        self.assertNotEqual(result[0][0], main)
        self.assertEqual(result[0][1], main)
        self.assertFalse(tasks.busy)

    def test_failure_delivered_and_busy_rejects_second_operation(self):
        tasks = BackgroundTasks(FakeRoot(), FakeStatus(), lambda value: None)
        self.addCleanup(tasks.close)
        result = []
        def broken():
            raise ValueError("synthetic")
        self.assertTrue(tasks.start("Working", broken, self.fail, result.append))
        self.assertFalse(tasks.start("Other", broken, self.fail, result.append))
        tasks.executor.shutdown(wait=True)
        tasks._poll()
        self.assertIsInstance(result[0], ValueError)
