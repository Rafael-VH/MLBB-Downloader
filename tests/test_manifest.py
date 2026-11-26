from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from mlbb_downloader.adapters.manifest_store import ManifestStore
from mlbb_downloader.domain.keying import canonical_image_url, image_key, item_key
from mlbb_downloader.domain.manifest import Manifest, ManifestItem


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

    assert loaded.schema_version == 2
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


def test_loads_v1_manifest_compatibly(tmp_path: Path) -> None:
    store = ManifestStore(tmp_path)
    store.path.write_text(
        """
        {
          "schema_version": 1,
          "base_url": "https://api.test/api",
          "generated_at": "2026-01-01T00:00:00Z",
          "items": {
            "/heroes": {
              "endpoint": "/heroes",
              "params": {},
              "path": "heroes/index.json",
              "sha256": "abc",
              "size": 3,
              "downloaded_at": "2026-01-01T00:00:00Z",
              "total": 1
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    loaded = store.load()

    assert loaded.schema_version == 1
    item = loaded.items["/heroes"]
    assert item.kind == "json"
    assert item.source_url is None


def test_canonical_image_url_unwraps_wsrv() -> None:
    wrapped = (
        "https://wsrv.nl/?url=https%3A%2F%2Fakmweb.youngjoygame.com%2Fweb%2Fgms%2Fimage%2Fa.jpg"
    )
    assert canonical_image_url(wrapped) == "https://akmweb.youngjoygame.com/web/gms/image/a.jpg"
    assert canonical_image_url("https://example.com/a.png") == "https://example.com/a.png"


def test_image_key_uses_canonical_url() -> None:
    wrapped = "https://wsrv.nl/?url=https%3A%2F%2Fexample.com%2Fa.png"
    assert image_key(wrapped) == image_key("https://example.com/a.png")
