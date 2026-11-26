"""Tests for report serialization."""

from __future__ import annotations

import json
from pathlib import Path

from mlbb_downloader.reporting import build_report, write_report
from mlbb_downloader.usecases.engine import CheckReport, Failure, SyncReport


def test_build_report_sync_and_check() -> None:
    sync = SyncReport(downloaded=2, skipped=1, failed=[Failure("k", "/e", "boom")])
    sync.elapsed = 1.5
    check = CheckReport(unchanged=3, changed=["a"], new=["b"], missing=["c"], corrupted=["d"])
    check.elapsed = 0.5

    payload = build_report("sync", {"heroes": sync, "academy": check})

    assert payload["command"] == "sync"
    assert "generated_at" in payload
    assert payload["reports"]["heroes"]["type"] == "sync"
    assert payload["reports"]["heroes"]["downloaded"] == 2
    assert payload["reports"]["heroes"]["failed"][0]["error"] == "boom"
    assert payload["reports"]["academy"]["type"] == "check"
    assert payload["reports"]["academy"]["corrupted"] == ["d"]


def test_write_report_json(tmp_path: Path) -> None:
    sync = SyncReport(downloaded=1)
    path = tmp_path / "out" / "report.json"

    written = write_report(path, "sync", {"heroes": sync})

    assert written == path
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["command"] == "sync"
    assert data["reports"]["heroes"]["downloaded"] == 1


def test_write_report_markdown(tmp_path: Path) -> None:
    check = CheckReport(unchanged=5, changed=["/heroes/1"])
    path = tmp_path / "report.md"

    write_report(path, "check", {"heroes": check})

    text = path.read_text(encoding="utf-8")
    assert "# Report: check" in text
    assert "## heroes" in text
    assert "- unchanged: 5" in text
    assert "`/heroes/1`" in text
