"""Data store: writes artifacts and keeps the manifest in sync."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mlbb_downloader.adapters.manifest_store import ManifestStore
from mlbb_downloader.adapters.paths import data_path
from mlbb_downloader.domain.keying import image_key, item_key
from mlbb_downloader.domain.manifest import ManifestItem


def serialize_json(payload: Any) -> bytes:
    """Deterministic serialization used for hashing and writing."""
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


class DataStore:
    def __init__(self, root: Path, *, base_url: str = "") -> None:
        self.root = Path(root)
        self.manifest_path = self.root / "manifest.json"
        self._manifest_store = ManifestStore(self.root)
        self.manifest = self._manifest_store.load()
        if base_url:
            self.manifest.base_url = base_url

    # -- identity ----------------------------------------------------------
    @staticmethod
    def manifest_key_for(endpoint: str, params: dict[str, Any] | None = None) -> str:
        return item_key(endpoint, params)

    @staticmethod
    def image_key_for(url: str) -> str:
        return image_key(url)

    # -- queries -----------------------------------------------------------
    def exists(self, key: str) -> bool:
        item = self.manifest.items.get(key)
        if item is None:
            return False
        return (self.root / item.path).exists()

    def load_json(self, key: str) -> dict[str, Any] | None:
        """Read a stored artifact back into memory, if it is still on disk."""
        item = self.manifest.items.get(key)
        if item is None:
            return None
        target = self.root / item.path
        if not target.exists():
            return None
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None

    def sha256(self, key: str) -> str | None:
        item = self.manifest.items.get(key)
        return item.sha256 if item else None

    def has_file(self, key: str) -> bool:
        """True when the manifest entry exists and its file is present on disk."""
        return self.exists(key)

    # -- writes ------------------------------------------------------------
    def save_json(
        self,
        key: str,
        relative_path: str,
        payload: Any,
        *,
        endpoint: str,
        params: dict[str, Any] | None = None,
        total: int | None = None,
    ) -> ManifestItem:
        target = data_path(self.root, *relative_path.split("/"))
        data = serialize_json(payload)
        digest = hashlib.sha256(data).hexdigest()

        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f"{target.name}.part")
        partial.write_bytes(data)
        os.replace(partial, target)

        item = ManifestItem(
            endpoint=endpoint,
            params=dict(params or {}),
            path=relative_path,
            sha256=digest,
            size=len(data),
            downloaded_at=datetime.now(UTC),
            total=total,
            kind="json",
        )
        self.manifest.items[key] = item
        return item

    def save_bytes(
        self,
        key: str,
        relative_path: str,
        data: bytes,
        *,
        source_url: str,
        endpoint: str = "",
        params: dict[str, Any] | None = None,
        content_type: str | None = None,
    ) -> ManifestItem:
        target = data_path(self.root, *relative_path.split("/"))
        digest = hashlib.sha256(data).hexdigest()

        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f"{target.name}.part")
        partial.write_bytes(data)
        os.replace(partial, target)

        item = ManifestItem(
            endpoint=endpoint,
            params=dict(params or {}),
            path=relative_path,
            sha256=digest,
            size=len(data),
            downloaded_at=datetime.now(UTC),
            kind="binary",
            source_url=source_url,
            content_type=content_type,
        )
        self.manifest.items[key] = item
        return item

    def flush(self) -> None:
        self._manifest_store.save(self.manifest)
