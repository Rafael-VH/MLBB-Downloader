"""Atomic JSON manifest describing every downloaded artifact."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from pydantic import BaseModel, Field


def item_key(endpoint: str, params: dict[str, Any] | None = None) -> str:
    """Stable identity for a logical artifact, independent of parameter order."""
    clean = {key: value for key, value in (params or {}).items() if value is not None}
    if not clean:
        return endpoint
    query = urlencode(sorted(clean.items(), key=lambda pair: pair[0]))
    return f"{endpoint}?{query}"


class ManifestItem(BaseModel):
    endpoint: str
    params: dict[str, Any] = Field(default_factory=dict)
    path: str
    sha256: str
    size: int
    downloaded_at: datetime
    total: int | None = None


class Manifest(BaseModel):
    schema_version: int = 1
    base_url: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: dict[str, ManifestItem] = Field(default_factory=dict)


class ManifestStore:
    """Reads and writes the manifest atomically.

    A corrupt manifest is quarantined instead of aborting the run: losing the index
    costs a re-download, while refusing to start costs the whole session.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.path = self.root / "manifest.json"

    def load(self) -> Manifest:
        if not self.path.exists():
            return Manifest()
        try:
            return Manifest.model_validate_json(self.path.read_text(encoding="utf-8"))
        except Exception:
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
            self.path.replace(self.path.with_name(f"manifest.json.corrupt-{stamp}"))
            return Manifest()

    def save(self, manifest: Manifest) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        manifest.generated_at = datetime.now(UTC)
        temp = self.path.with_name("manifest.json.tmp")
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(manifest.model_dump_json(indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.path)
