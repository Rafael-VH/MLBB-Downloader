from __future__ import annotations

from pathlib import Path

import httpx

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.downloaders.academy import (
    ACADEMY_COLLECTIONS,
    check_academy,
    hero_lanes,
    sync_academy,
)
from mlbb_downloader.adapters.fsstore import DataStore

CATALOG_RECORD = {
    "data": {
        "head": "https://cdn.example/head.png",
        "hero": {"data": {"name": "Miya"}},
        "hero_id": 1,
    }
}

LANE_RECORD = {
    "data": {
        "hero": {
            "data": {
                "roadsort": [
                    {"data": {"road_sort_id": "5", "road_sort_title": "Gold Lane"}},
                    {"data": {"road_sort_id": "2", "road_sort_title": "Mid Lane"}},
                ]
            }
        },
        "hero_id": 1,
    }
}


def envelope(records: list, total: int) -> dict:
    return {
        "code": 0,
        "message": "OK",
        "data": {"records": records, "total": total},
        "traceID": "t",
    }


class Server:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.lane_records = [LANE_RECORD]
        self.catalog_records = [CATALOG_RECORD]

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(path)
        if path == "/api/academy/heroes/catalog":
            return httpx.Response(
                200, json=envelope(self.catalog_records, len(self.catalog_records))
            )
        if path == "/api/academy/heroes/1/lane":
            return httpx.Response(200, json=envelope(self.lane_records, 1))
        if path.endswith("/builds"):
            lane = request.url.params.get("lane")
            return httpx.Response(200, json=envelope([{"lane": lane}], 1))
        if path.endswith("/win-rate/timeline"):
            lane = request.url.params.get("lane")
            return httpx.Response(200, json=envelope([{"lane": lane}], 1))
        return httpx.Response(200, json=envelope([{"path": path}], 1))


def make_client(server: Server) -> ArenaClient:
    return ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=0,
        transport=httpx.MockTransport(server.handler),
        sleep=lambda _seconds: None,
    )


def make_store(tmp_path: Path) -> DataStore:
    return DataStore(tmp_path, base_url="https://api.test/api")


EXPECTED_ARTIFACTS = (
    len(ACADEMY_COLLECTIONS)  # static collections, catalog included
    + 5  # lane, stats, counters, teammates, trends for one hero
    + 2 * 2  # builds + win-rate timeline for the two lanes the hero plays
)


def test_sync_downloads_collections_hero_artifacts_and_derived_lanes(
    tmp_path: Path,
) -> None:
    server = Server()
    store = make_store(tmp_path)

    with make_client(server) as client:
        report = sync_academy(client, store)

    assert report.downloaded == EXPECTED_ARTIFACTS
    assert report.failed == []
    assert report.unavailable == []
    assert store.exists("/academy/heroes/catalog")

    builds = [path for path in server.calls if path.endswith("/builds")]
    timeline = [path for path in server.calls if path.endswith("/win-rate/timeline")]
    assert len(builds) == 2
    assert len(timeline) == 2
    lane_keys = [
        key for key in store.manifest.items if "/builds" in key or "/win-rate/timeline" in key
    ]
    assert len(lane_keys) == 4, "lane-specific artifacts are keyed by their lane"
    assert all("lane=gold" in key or "lane=mid" in key for key in lane_keys)


def test_builds_only_use_lanes_the_hero_actually_plays(tmp_path: Path) -> None:
    requested_keys: list[str] = []
    server = Server()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/builds"):
            requested_keys.append(str(request.url.params.get("lane")))
        return server.handler(request)

    store = make_store(tmp_path)
    with ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=0,
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: None,
    ) as client:
        sync_academy(client, store)

    assert sorted(requested_keys) == ["gold", "mid"]


def test_second_sync_downloads_nothing(tmp_path: Path) -> None:
    server = Server()
    with make_client(server) as client:
        first = sync_academy(client, make_store(tmp_path))
    with make_client(server) as client:
        second = sync_academy(client, make_store(tmp_path))

    assert first.downloaded == EXPECTED_ARTIFACTS
    assert second.downloaded == 0
    assert second.skipped == EXPECTED_ARTIFACTS


def test_limit_only_expands_the_requested_heroes(tmp_path: Path) -> None:
    server = Server()
    server.catalog_records = [
        CATALOG_RECORD,
        {
            "data": {
                "hero": {"data": {"name": "Balmond"}},
                "hero_id": 2,
            }
        },
    ]
    store = make_store(tmp_path)

    with make_client(server) as client:
        report = sync_academy(client, store, limit=1)

    assert report.downloaded == EXPECTED_ARTIFACTS
    assert not any("/heroes/2/" in path for path in server.calls)
    assert len(server.catalog_records) == 2


def test_no_user_generated_or_discontinued_endpoints_are_scheduled(
    tmp_path: Path,
) -> None:
    server = Server()
    with make_client(server) as client:
        sync_academy(client, make_store(tmp_path))

    assert not any("recommended" in path for path in server.calls)
    assert not any("ratings" in path for path in server.calls)
    assert not any("/ranks/" in path for path in server.calls)


def test_check_reports_every_stored_artifact_as_unchanged(tmp_path: Path) -> None:
    server = Server()
    with make_client(server) as client:
        sync_academy(client, make_store(tmp_path))

    with make_client(server) as client:
        report = check_academy(client, make_store(tmp_path))

    assert report.unchanged == EXPECTED_ARTIFACTS
    assert report.changed == []
    assert report.missing == []
    assert report.not_downloaded == 0


def test_check_counts_remote_heroes_that_are_not_local(tmp_path: Path) -> None:
    server = Server()
    with make_client(server) as client:
        sync_academy(client, make_store(tmp_path), limit=1)

    server.catalog_records = [
        CATALOG_RECORD,
        {"data": {"hero": {"data": {"name": "Balmond"}}, "hero_id": 2}},
    ]
    with make_client(server) as client:
        report = check_academy(client, make_store(tmp_path))

    assert report.not_downloaded == 1


def test_hero_lanes_maps_every_sort_id_and_dedupes() -> None:
    roadsort = [
        {"data": {"road_sort_id": str(value), "road_sort_title": "ignored"}}
        for value in ("1", "2", "3", "4", "5", "1")
    ]
    records = [{"data": {"hero": {"data": {"roadsort": roadsort}}}}]

    assert hero_lanes(records) == ["exp", "mid", "roam", "jungle", "gold"]


def test_hero_lanes_falls_back_to_the_title() -> None:
    roadsort = [
        {"data": {"road_sort_title": "Exp Lane"}},
        {"data": {"road_sort_title": "Jungle"}},
        {"data": {"road_sort_title": "Gold Lane"}},
    ]
    records = [{"data": {"hero": {"data": {"roadsort": roadsort}}}}]

    assert hero_lanes(records) == ["exp", "jungle", "gold"]


def test_hero_lanes_is_empty_for_unexpected_payloads() -> None:
    assert hero_lanes([]) == []
    assert hero_lanes([{"data": None}]) == []
    assert hero_lanes([{"data": {"hero": {"data": {"roadsort": []}}}}]) == []
