"""Small cross-platform advisory lock for mutable derived artifacts."""

from __future__ import annotations

import contextlib
import os
import time


class LockTimeout(TimeoutError):
    pass


@contextlib.contextmanager
def locked_file(target_path: str, timeout: float = 15.0):
    """Lock ``target_path + '.lock'`` for a read-modify-write transaction."""

    lock_path = os.path.abspath(target_path) + ".lock"
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    handle = open(lock_path, "a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    deadline = time.monotonic() + max(0.0, float(timeout))
    acquired = False
    try:
        while not acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except (OSError, IOError):
                if time.monotonic() >= deadline:
                    raise LockTimeout("Timed out waiting for artifact lock: " + lock_path)
                time.sleep(0.05)
        yield lock_path
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (OSError, IOError):
                pass
        handle.close()
