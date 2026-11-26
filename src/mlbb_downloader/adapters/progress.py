"""Optional job progress checkpoint for long-running CLI/GUI jobs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ProgressTracker:
    path: Path
    command: str
    status: str = "running"
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str | None = None
    phase: str | None = None
    total: int | None = None
    done: int = 0
    current: str | None = None
    counters: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "status": self.status,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "finished_at": self.finished_at,
            "phase": self.phase,
            "total": self.total,
            "done": self.done,
            "current": self.current,
            "counters": dict(self.counters),
            "error": self.error,
        }

    def save(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        partial = self.path.with_name(f"{self.path.name}.part")
        partial.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(partial, self.path)

    def set_phase(self, phase: str, *, total: int | None = None) -> None:
        self.phase = phase
        self.total = total
        self.done = 0
        self.current = None
        self.save()

    def tick(self, *, current: str | None = None, counters: dict[str, Any] | None = None) -> None:
        self.done += 1
        if current is not None:
            self.current = current
        if counters:
            self.counters.update(counters)
        self.save()

    def update(self, *, counters: dict[str, Any] | None = None, current: str | None = None) -> None:
        if current is not None:
            self.current = current
        if counters:
            self.counters.update(counters)
        self.save()

    def finish(self, *, counters: dict[str, Any] | None = None) -> None:
        self.status = "finished"
        self.finished_at = datetime.now(UTC).isoformat()
        if counters:
            self.counters.update(counters)
        self.save()

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.finished_at = datetime.now(UTC).isoformat()
        self.error = str(error)
        self.save()


def progress_path(root: Path) -> Path:
    return Path(root) / "_progress.json"
