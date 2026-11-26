"""Main GUI window."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.adapters.fsstore import DataStore
from mlbb_downloader.adapters.progress import progress_path
from mlbb_downloader.config import Settings, default_output_dir
from mlbb_downloader.gui.workers import JobResult, TaskWorker
from mlbb_downloader.usecases.academy import check_academy, sync_academy
from mlbb_downloader.usecases.heroes import check_heroes, sync_heroes
from mlbb_downloader.usecases.images import check_images, sync_images


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MLBB Downloader")
        self.resize(900, 640)
        self._busy = False

        self.output_edit = QLineEdit(str(default_output_dir()))
        self.browse_btn = QPushButton("Browse")
        self.sync_btn = QPushButton("Sync all")
        self.check_btn = QPushButton("Check all")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.images_check = QCheckBox("Images")
        self.images_check.setChecked(True)
        self.local_only_check = QCheckBox("Local-only check")
        self.status_label = QLabel("Ready")
        self._cancel_event: threading.Event | None = None
        self.phase_label = QLabel("Phase: -")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)

        top = QHBoxLayout()
        top.addWidget(QLabel("Output:"))
        top.addWidget(self.output_edit, 1)
        top.addWidget(self.browse_btn)

        actions = QHBoxLayout()
        actions.addWidget(self.sync_btn)
        actions.addWidget(self.check_btn)
        actions.addWidget(self.cancel_btn)
        actions.addWidget(self.images_check)
        actions.addWidget(self.local_only_check)
        actions.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.log, 1)

        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

        self.browse_btn.clicked.connect(self._browse)
        self.sync_btn.clicked.connect(self._run_sync)
        self.check_btn.clicked.connect(self._run_check)
        self.cancel_btn.clicked.connect(self._cancel_job)

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self._poll_progress)
        self.timer.start()

        from PySide6.QtCore import QThreadPool

        self.pool = QThreadPool.globalInstance()

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select output directory", self.output_edit.text()
        )
        if path:
            self.output_edit.setText(path)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for w in (self.sync_btn, self.check_btn, self.browse_btn, self.output_edit):
            w.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.status_label.setText("Running..." if busy else "Ready")

    def _cancel_job(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
            self.status_label.setText("Cancelling...")
            self._log("Cancel requested...")

    def _log(self, msg: str) -> None:
        self.log.appendPlainText(msg)

    def _build(self) -> tuple[Path, ArenaClient, DataStore]:
        settings = Settings()
        settings.output_dir = Path(self.output_edit.text()).expanduser()
        client = ArenaClient(settings.base_url, delay=settings.delay, timeout=settings.timeout)
        store = DataStore(settings.output_dir, base_url=settings.base_url)
        return settings.output_dir, client, store

    def _run_sync(self) -> None:
        self._run_job("sync")

    def _run_check(self) -> None:
        self._run_job("check")

    def _run_job(self, command: str) -> None:
        if self._busy:
            return
        include_images = self.images_check.isChecked()
        local_only = self.local_only_check.isChecked()
        self._cancel_event = threading.Event()
        self._set_busy(True)
        self.progress.setRange(0, 0)
        self.phase_label.setText("Phase: starting")
        self._log(f"== {command} ==")

        cancel = self._cancel_event

        def task() -> dict[str, Any]:
            _dir, client, store = self._build()
            with client:
                if command == "sync":
                    heroes = sync_heroes(client, store, cancel=cancel)
                    academy = sync_academy(client, store, cancel=cancel)
                    img = sync_images(client, store, cancel=cancel) if include_images else None
                else:
                    heroes = check_heroes(client, store, cancel=cancel)
                    academy = check_academy(client, store, cancel=cancel)
                    img = (
                        check_images(client, store, local_only=local_only, cancel=cancel)
                        if include_images
                        else None
                    )
            return {"heroes": heroes, "academy": academy, "images": img}

        worker = TaskWorker(task)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)
        self.pool.start(worker)

    def _on_finished(self, result: JobResult) -> None:
        self._set_busy(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        if not result.ok:
            if result.error == "cancelled":
                self.status_label.setText("Cancelled")
                self._log("Cancelled.")
            else:
                self.status_label.setText("Failed")
            return
        payload = result.payload or {}
        for name, rep in payload.items():
            if rep is None:
                continue
            if hasattr(rep, "downloaded"):
                self._log(
                    f"{name}: downloaded={rep.downloaded} skipped={rep.skipped} "
                    f"failed={len(rep.failed)}"
                )
            else:
                self._log(
                    f"{name}: unchanged={rep.unchanged} changed={len(rep.changed)} "
                    f"missing={len(rep.missing)} corrupted={len(rep.corrupted)}"
                )
        self.status_label.setText("Done")
        self._poll_progress()

    def _on_error(self, tb: str) -> None:
        self._log(tb)
        QMessageBox.critical(self, "Job failed", "The background job failed. See log for details.")

    def _poll_progress(self) -> None:
        path = progress_path(Path(self.output_edit.text()).expanduser())
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        phase = data.get("phase") or "-"
        done = data.get("done", 0)
        total = data.get("total")
        status = data.get("status", "-")
        counters = data.get("counters", {})
        if total:
            self.progress.setRange(0, int(total))
            self.progress.setValue(int(done))
        elif self._busy:
            self.progress.setRange(0, 0)
        self.phase_label.setText(f"Phase: {phase} | {done}/{total or '?'} | {status}")
        if counters and self._busy:
            self.status_label.setText(f"Running... {counters}")