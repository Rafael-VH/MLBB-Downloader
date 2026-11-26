from __future__ import annotations

from pathlib import Path

import httpx

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.adapters.fsstore import DataStore
from mlbb_downloader.usecases.heroes import HERO_SUBRESOURCES, check_heroes, sync_heroes

HERO = {"hero_id": 1, "data": {"hero": {"data": {"name": "Miya"}}}}


def envelope(records: list, total: int) -> dict:
    return {
        "code": 200,
        "message": "ok",
        "data": {"records": records, "total": total},
        "traceID": "t",
    }


def make_handler(state: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/heroes":
            return httpx.Response(200, json=envelope([HERO], 1))
        return httpx.Response(
            200,
            json=envelope([{"path": path, "revision": state["revision"]}], 1),
        )

    return handler


def make_client(handler) -> ArenaClient:
    return ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=0,
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: None,
    )


def test_sync_downloads_index_plus_every_subresource(tmp_path: Path) -> None:
    state = {"revision": 1}
    store = DataStore(tmp_path, base_url="https://api.test/api")

    with make_client(make_handler(state)) as client:
        report = sync_heroes(client, store)

    expected = 1 + 3 + len(HERO_SUBRESOURCES)
    assert report.downloaded == expected
    assert report.failed == []
    assert store.exists(store.manifest_key_for("/heroes", {}))
    assert store.manifest_path.exists()


def test_second_sync_skips_everything_already_downloaded(tmp_path: Path) -> None:
    state = {"revision": 1}
    store = DataStore(tmp_path, base_url="https://api.test/api")

    with make_client(make_handler(state)) as client:
        first = sync_heroes(client, store)
    with make_client(make_handler(state)) as client:
        second = sync_heroes(client, DataStore(tmp_path, base_url="https://api.test/api"))

    assert first.downloaded > 0
    assert second.downloaded == 0
    assert second.skipped == first.downloaded


def test_force_redownloads(tmp_path: Path) -> None:
    state = {"revision": 1}

    with make_client(make_handler(state)) as client:
        sync_heroes(client, DataStore(tmp_path, base_url="https://api.test/api"))
    with make_client(make_handler(state)) as client:
        forced = sync_heroes(
            client,
            DataStore(tmp_path, base_url="https://api.test/api"),
            force=True,
        )

    assert forced.downloaded > 0
    assert forced.skipped == 0


def test_check_reports_changed_items_without_downloading(tmp_path: Path) -> None:
    state = {"revision": 1}

    with make_client(make_handler(state)) as client:
        sync_heroes(client, DataStore(tmp_path, base_url="https://api.test/api"))

    state["revision"] = 2

    with make_client(make_handler(state)) as client:
        report = check_heroes(client, DataStore(tmp_path, base_url="https://api.test/api"))

    assert len(report.changed) == len(HERO_SUBRESOURCES) + 3
    assert report.unchanged == 1, "the hero index did not change"
    assert report.new == []


def test_limit_only_touches_requested_heroes(tmp_path: Path) -> None:
    state = {"revision": 1}
    store = DataStore(tmp_path, base_url="https://api.test/api")

    with make_client(make_handler(state)) as client:
        report = sync_heroes(client, store, limit=0)

    assert report.downloaded == 4, "limit=0 stores index and global collections"


def test_check_does_not_fetch_never_downloaded_heroes(tmp_path: Path) -> None:
    state = {"revision": 1}
    calls: list[str] = []

    def counting_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return make_handler(state)(request)

    store = DataStore(tmp_path, base_url="https://api.test/api")
    with make_client(counting_handler) as client:
        report = check_heroes(client, store)

    assert "/api/heroes" in calls
    assert "/api/heroes/rank" in calls
    assert "/api/heroes/positions" in calls
    assert "/api/heroes/wallpapers" in calls
    assert report.not_downloaded == 1
    assert "/heroes" in report.new


def test_sync_single_hero_id(tmp_path: Path) -> None:
    state = {"revision": 1}
    store = DataStore(tmp_path, base_url="https://api.test/api")

    with make_client(make_handler(state)) as client:
        report = sync_heroes(client, store, hero_id=1)

    assert report.downloaded == 1 + len(HERO_SUBRESOURCES)
    assert report.failed == []
    assert report.skipped == 0
