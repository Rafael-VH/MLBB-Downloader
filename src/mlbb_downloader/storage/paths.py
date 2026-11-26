"""Output path construction that cannot escape the data root."""

from __future__ import annotations

from pathlib import Path

from mlbb_downloader.utils.slug import sanitize_component


def data_path(root: Path, *parts: str) -> Path:
    """Resolve ``parts`` under ``root``, sanitizing each component."""
    root_path = Path(root).resolve()
    cleaned: list[str] = []
    for part in parts:
        text = str(part)
        if text in {".", ".."}:
            raise ValueError(f"refusing path component {text!r}")
        cleaned.append(sanitize_component(text))

    candidate = root_path.joinpath(*cleaned).resolve()
    if candidate != root_path and root_path not in candidate.parents:
        raise ValueError(f"path escapes data root: {candidate}")
    return candidate
