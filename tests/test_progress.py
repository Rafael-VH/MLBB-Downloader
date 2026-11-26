"""Tests for optional job progress checkpoints."""

from __future__ import annotations

import json
from pathlib import Path

from mlbb_downloader.adapters.progress import ProgressTracker, progress_path


def test_progress_tracker_writes_checkpoint(tmp_path: Path) -> None:
    path = progress_path(tmp_path)
    tracker = ProgressTracker(path, "sync")
    tracker.save()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["command"] == "sync"
    assert data["status"] == "running"
    assert data["done"] == 0

    tracker.set_phase("heroes:index", total=1)
    tracker.tick(current="heroes:/heroes", counters={"downloaded": 1})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["phase"] == "heroes:index"
    assert data["total"] == 1
    assert data["done"] == 1
    assert data["current"] == "heroes:/heroes"
    assert data["counters"]["downloaded"] == 1

    tracker.finish(counters={"ok": True})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "finished"
    assert data["finished_at"] is not None
    assert data["counters"]["ok"] is True


def test_progress_tracker_fail(tmp_path: Path) -> None:
    tracker = ProgressTracker(progress_path(tmp_path), "check")
    tracker.fail("boom")
    data = json.loads(tracker.path.read_text(encoding="utf-8"))
    assert data["status"] == "failed"
    assert data["error"] == "boom"
