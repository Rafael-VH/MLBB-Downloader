"""Background workers for GUI tasks."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from mlbb_downloader.errors import JobCancelledError


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)
    log = Signal(str)


@dataclass(slots=True)
class JobResult:
    ok: bool
    payload: Any = None
    error: str | None = None


class TaskWorker(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            payload = self.fn()
        except JobCancelledError:
            self.signals.finished.emit(JobResult(ok=False, error="cancelled"))
            return
        except Exception:  # noqa: BLE001 - GUI boundary reports any failure
            self.signals.error.emit(traceback.format_exc())
            self.signals.finished.emit(JobResult(ok=False, error="failed"))
            return
        self.signals.finished.emit(JobResult(ok=True, payload=payload))