from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from mlbb_downloader.storage.manifest import (
    Manifest,
    ManifestItem,
    ManifestStore,
    item_key,
)


def make_item(path: str = "heroes/miya/detail.json") -> ManifestItem:
    return ManifestItem(
        endpoint="/heroes/miya",
        params={"id": 1},
        path=path,
        sha256="a" * 64,
        size=10,
        downloaded_at=datetime.now(UTC),
    )


def test_roundtrip(tmp_path: Path) -> None:
    store = ManifestStore(tmp_path)
    manifest = Manifest(base_url="https://api.test/api")
    manifest.items[item_key("/heroes/miya", {"id": 1})] = make_item()

    store.save(manifest)
    loaded = store.load()

    assert loaded.schema_version == 1
    assert len(loaded.items) == 1
    assert next(iter(loaded.items.values())).sha256 == "a" * 64


def test_save_is_atomic_and_leaves_no_temp_file(tmp_path: Path) -> None:
    store = ManifestStore(tmp_path)
    store.save(Manifest())

    leftovers = [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []
    assert store.path.exists()


def test_corrupt_manifest_is_quarantined_not_fatal(tmp_path: Path) -> None:
    store = ManifestStore(tmp_path)
    store.path.write_text("{ this is not json", encoding="utf-8")

    loaded = store.load()

    assert loaded.items == {}
    backup = list(tmp_path.glob("manifest.json.corrupt-*"))
    assert len(backup) == 1, "corrupt manifest must be preserved for inspection"


def test_item_key_is_stable_across_param_order() -> None:
    first = item_key("/heroes/1/stats", {"rank": "all", "lang": "en"})
    second = item_key("/heroes/1/stats", {"lang": "en", "rank": "all"})

    assert first == second


def test_item_key_distinguishes_params() -> None:
    assert item_key("/heroes", {"size": 500}) != item_key("/heroes", {"size": 10})
