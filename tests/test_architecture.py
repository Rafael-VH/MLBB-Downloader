"""Architecture guardrails.

The domain layer must stay pure: no HTTP, no CLI, no adapters, no usecases,
and no filesystem writes. This test makes the dependency rule executable.
"""

from __future__ import annotations

from pathlib import Path

BANNED = (
    "httpx",
    "typer",
    "mlbb_downloader.adapters",
    "mlbb_downloader.usecases",
    "mlbb_downloader.cli",
)

WRITE_HINTS = (
    "write_text(",
    "write_bytes(",
    "open(",
    "os.replace(",
    "mkdir(",
)


def test_domain_is_pure() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "mlbb_downloader" / "domain"
    for path in sorted(root.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        for banned in BANNED:
            assert banned not in src, f"{path.name} imports {banned}"
        for hint in WRITE_HINTS:
            assert hint not in src, f"{path.name} performs IO ({hint})"
