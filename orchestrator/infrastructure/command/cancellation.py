from __future__ import annotations

import subprocess
import sys
import threading
from dataclasses import dataclass, field


class CommandCancelled(RuntimeError):
    pass


@dataclass
class CancellationRegistry:
    _cancelled: set[str] = field(default_factory=set)
    _processes: dict[str, subprocess.Popen[str]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def register(self, key: str, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._processes[key] = process
            cancelled = key in self._cancelled
        if cancelled:
            terminate_process_tree(process)

    def unregister(self, key: str, process: subprocess.Popen[str]) -> None:
        with self._lock:
            if self._processes.get(key) is process:
                self._processes.pop(key, None)

    def cancel(self, key: str) -> bool:
        with self._lock:
            self._cancelled.add(key)
            process = self._processes.get(key)
        if process is None:
            return False
        terminate_process_tree(process)
        return True

    def is_cancelled(self, key: str) -> bool:
        with self._lock:
            return key in self._cancelled

    def clear(self, key: str) -> None:
        with self._lock:
            self._cancelled.discard(key)
            self._processes.pop(key, None)


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    process.kill()
