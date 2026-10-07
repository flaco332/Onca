"""One worker, main-thread queue polling; worker code never calls Tk APIs."""
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from collections.abc import Callable


class BackgroundTasks:
    """Run slow filesystem work and deliver results exclusively through after."""
    def __init__(self, root, status, set_busy: Callable[[bool], None]):
        self.root, self.status, self.set_busy = root, status, set_busy
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="onca-worker")
        self.results = Queue()
        self.busy, self.alive = False, True
        self._after_id = self.root.after(50, self._poll)

    def start(self, label: str, operation: Callable, complete: Callable, failed: Callable) -> bool:
        """Reject concurrent operations rather than racing shared UI state."""
        if self.busy:
            return False
        self.busy = True
        self.set_busy(True)
        self.status.set(label)

        def work():
            try:
                self.results.put((True, operation(), complete, failed))
            except Exception as error:
                self.results.put((False, error, complete, failed))
        self.executor.submit(work)
        return True

    def _poll(self):
        self._after_id = None
        if not self.alive:
            return
        try:
            success, result, complete, failed = self.results.get_nowait()
        except Empty:
            pass
        else:
            self.busy = False
            self.set_busy(False)
            try:
                (complete if success else failed)(result)
            except Exception as error:
                failed(error)
        if self.alive:
            self._after_id = self.root.after(50, self._poll)

    def close(self) -> None:
        """Caller blocks window closure while busy, avoiding abandoned writes."""
        self.alive = False
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self.executor.shutdown(wait=False, cancel_futures=True)
