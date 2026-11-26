"""Run report serialization (JSON/Markdown)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mlbb_downloader.usecases.engine import CheckReport, SyncReport


def _sync_dict(report: SyncReport) -> dict[str, Any]:
    return {
        "downloaded": report.downloaded,
        "skipped": report.skipped,
        "failed": [{"key": f.key, "endpoint": f.endpoint, "error": f.error} for f in report.failed],
        "unavailable": [
            {"key": f.key, "endpoint": f.endpoint, "error": f.error} for f in report.unavailable
        ],
        "elapsed": report.elapsed,
    }


def _check_dict(report: CheckReport) -> dict[str, Any]:
    return {
        "unchanged": report.unchanged,
        "changed": report.changed,
        "new": report.new,
        "missing": report.missing,
        "corrupted": report.corrupted,
        "not_downloaded": report.not_downloaded,
        "failed": [{"key": f.key, "endpoint": f.endpoint, "error": f.error} for f in report.failed],
        "unavailable": [
            {"key": f.key, "endpoint": f.endpoint, "error": f.error} for f in report.unavailable
        ],
        "elapsed": report.elapsed,
    }


def build_report(command: str, reports: dict[str, SyncReport | CheckReport]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": command,
        "generated_at": datetime.now(UTC).isoformat(),
        "reports": {},
    }
    for name, report in reports.items():
        if isinstance(report, SyncReport):
            payload["reports"][name] = {"type": "sync", **_sync_dict(report)}
        else:
            payload["reports"][name] = {"type": "check", **_check_dict(report)}
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Report: {payload['command']}",
        "",
        f"- generated_at: {payload['generated_at']}",
        "",
    ]
    for name, report in payload["reports"].items():
        lines.append(f"## {name}")
        for key, value in report.items():
            if key == "type":
                continue
            if isinstance(value, list) and value and isinstance(value[0], dict):
                lines.append(f"- {key}: {len(value)}")
                for item in value[:20]:
                    lines.append(f"  - `{item.get('key', '')}`: {item.get('error', '')}")
            elif isinstance(value, list):
                lines.append(f"- {key}: {len(value)}")
                for item in value[:20]:
                    lines.append(f"  - `{item}`")
            else:
                lines.append(f"- {key}: {value}")
        lines.append("")
    return "\n".join(lines)


def write_report(path: Path, command: str, reports: dict[str, SyncReport | CheckReport]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_report(command, reports)
    if path.suffix.lower() == ".md":
        path.write_text(render_markdown(payload), encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
