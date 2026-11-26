from __future__ import annotations

from pathlib import Path

import httpx

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.adapters.fsstore import DataStore
from mlbb_downloader.domain.keying import image_key, item_key
from mlbb_downloader.usecases.images import check_images, sync_images


def make_client(handler) -> ArenaClient:
    return ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=0,
        transport=httpx.MockTransport(handler),
        sleep=lambda _s: None,
    )


def seed_hero(store: DataStore) -> None:
    hero_key = item_key("/heroes/1", {"hero_id": 1})
    store.save_json(
        hero_key,
        "heroes/Miya/detail.json",
        {
            "endpoint": "/heroes/1",
            "total": 1,
            "records": [
                {
                    "hero_id": 1,
                    "data": {
                        "head": "https://wsrv.nl/?url=https%3A%2F%2Fcdn.test%2Fhead.jpg",
                        "hero": {
                            "data": {"name": "Miya", "painting": "https://cdn.test/painting.png"}
                        },
                    },
                }
            ],
        },
        endpoint="/heroes/1",
        params={"hero_id": 1},
        total=1,
    )
    wp_key = item_key("/heroes/1/wallpapers", {"hero_id": 1})
    store.save_json(
        wp_key,
        "heroes/Miya/wallpapers.json",
        {
            "endpoint": "/heroes/1/wallpapers",
            "total": 1,
            "records": [
                {
                    "data": {
                        "skinid": "skin01",
                        "pictures": [
                            {
                                "resolution": "1920x1080",
                                "url": "https://wsrv.nl/?url=https%3A%2F%2Fcdn.test%2Fwp.jpg",
                            }
                        ],
                    }
                }
            ],
        },
        endpoint="/heroes/1/wallpapers",
        params={"hero_id": 1},
        total=1,
    )
    store.flush()


def image_handler(state: dict[str, bytes]):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for name, data in state.items():
            if name in url:
                return httpx.Response(200, content=data, headers={"content-type": "image/jpeg"})
        return httpx.Response(404, content=b"no")

    return handler


def test_sync_images_downloads_and_resumes(tmp_path: Path) -> None:
    store = DataStore(tmp_path, base_url="https://api.test/api")
    seed_hero(store)
    state = {"head.jpg": b"HEAD", "painting.png": b"PAINT", "wp.jpg": b"WALL"}

    with make_client(image_handler(state)) as client:
        report = sync_images(client, store)

    assert report.downloaded == 3
    assert report.failed == []

    with make_client(image_handler(state)) as client:
        second = sync_images(client, DataStore(tmp_path))

    assert second.downloaded == 0
    assert second.skipped == 3


def test_check_images_reports_missing_and_changed(tmp_path: Path) -> None:
    store = DataStore(tmp_path, base_url="https://api.test/api")
    seed_hero(store)
    state = {"head.jpg": b"HEAD", "painting.png": b"PAINT", "wp.jpg": b"WALL"}

    with make_client(image_handler(state)) as client:
        sync_images(client, store)

    # remove one file
    wp_key = image_key("https://cdn.test/wp.jpg")
    wp_path = tmp_path / store.manifest.items[wp_key].path
    wp_path.unlink()
    # change remote bytes for another
    state["head.jpg"] = b"HEAD2"

    with make_client(image_handler(state)) as client:
        report = check_images(client, DataStore(tmp_path))

    assert wp_key in report.missing
    assert any("head.jpg" in k or "cdn.test/head.jpg" in k for k in report.changed)
    assert report.unchanged == 1


def test_check_images_reports_corrupted_local_file(tmp_path: Path) -> None:
    store = DataStore(tmp_path, base_url="https://api.test/api")
    seed_hero(store)
    state = {"head.jpg": b"HEAD", "painting.png": b"PAINT", "wp.jpg": b"WALL"}

    with make_client(image_handler(state)) as client:
        sync_images(client, store)

    head_key = image_key("https://cdn.test/head.jpg")
    head_path = tmp_path / store.manifest.items[head_key].path
    head_path.write_bytes(b"BAD")

    with make_client(image_handler(state)) as client:
        report = check_images(client, DataStore(tmp_path))

    assert head_key in report.corrupted
    assert head_key not in report.changed


def test_check_images_local_only_skips_remote(tmp_path: Path) -> None:
    store = DataStore(tmp_path, base_url="https://api.test/api")
    seed_hero(store)
    state = {"head.jpg": b"HEAD", "painting.png": b"PAINT", "wp.jpg": b"WALL"}

    with make_client(image_handler(state)) as client:
        sync_images(client, store)

    calls: list[str] = []

    def no_network(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(500, content=b"should not be called")

    with make_client(no_network) as client:
        report = check_images(client, DataStore(tmp_path), local_only=True)

    assert calls == []
    assert report.unchanged == 3
    assert report.changed == []
    assert report.failed == []
