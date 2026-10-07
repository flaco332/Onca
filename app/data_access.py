"""Serialize database and attachment operations within and between processes.

SQLite transactions alone cannot freeze the attachment directory. Every app
write and complete backup shares this reentrant lock. Connections stay in the
thread that created them. The persistent lock file contains no user data.
"""
from contextlib import contextmanager
from pathlib import Path
import os
import threading
import time
from collections.abc import Iterator
from app.paths import managed_path

_guard = threading.Lock()
_locks: dict[str, threading.RLock] = {}
_local = threading.local()


@contextmanager
def data_operation(data_root: Path, timeout: float = 5.0) -> Iterator[None]:
    """Hold an OS advisory lock, reentrantly, for one data operation."""
    root = data_root.resolve()
    key = os.path.normcase(str(root))
    with _guard:
        mutex = _locks.setdefault(key, threading.RLock())
    with mutex:
        depths = getattr(_local, "depths", {})
        _local.depths = depths
        if depths.get(key, 0):
            depths[key] += 1
            try:
                yield
            finally:
                depths[key] -= 1
            return
        root.mkdir(parents=True, exist_ok=True)
        with managed_path(root, ".operation.lock").open("a+b") as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"0")
                handle.flush()
            deadline = time.monotonic() + timeout
            while True:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Data operation busy") from None
                    time.sleep(0.05)
            depths[key] = 1
            try:
                yield
            finally:
                depths.pop(key, None)
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_UN)
