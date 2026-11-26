from __future__ import annotations

from pathlib import Path

from mlbb_downloader.adapters.fsstore import DataStore
from mlbb_downloader.domain.keying import image_key


def test_save_bytes_writes_atomically_and_records_manifest(tmp_path: Path) -> None:
    store = DataStore(tmp_path, base_url="https://api.test/api")
    key = image_key("https://example.com/a.png")
    data = b"\x89PNG\r\n\x1a\nhello"

    item = store.save_bytes(
        key,
        "heroes/miya/images/a.png",
        data,
        source_url="https://example.com/a.png",
        content_type="image/png",
    )
    store.flush()

    target = tmp_path / "heroes" / "miya" / "images" / "a.png"
    assert target.read_bytes() == data
    assert item.kind == "binary"
    assert item.source_url == "https://example.com/a.png"
    assert item.size == len(data)
    assert store.exists(key)
    assert list(tmp_path.rglob("*.part")) == []

    reloaded = DataStore(tmp_path)
    assert reloaded.manifest.items[key].sha256 == item.sha256
    assert reloaded.manifest.schema_version == 2


def test_save_json_marks_kind_json(tmp_path: Path) -> None:
    store = DataStore(tmp_path)
    key = store.manifest_key_for("/heroes", {})
    item = store.save_json(key, "heroes/index.json", {"ok": True}, endpoint="/heroes")

    assert item.kind == "json"
