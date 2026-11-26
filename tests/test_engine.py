from __future__ import annotations

from pathlib import Path

import httpx

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.adapters.fsstore import DataStore
from mlbb_downloader.usecases.engine import (
    Artifact,
    CheckReport,
    SyncReport,
    check_manifest,
    check_many,
    check_one,
    load_records,
    sync_many,
    sync_one,
)


def envelope(records: list, total: int) -> dict:
    return {
        "code": 0,
        "message": "OK",
        "data": {"records": records, "total": total},
        "traceID": "t",
    }


def make_client(handler) -> ArenaClient:
    return ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=0,
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: None,
    )


def make_store(tmp_path: Path) -> DataStore:
    return DataStore(tmp_path, base_url="https://api.test/api")


def test_sync_one_stores_and_returns_records(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope([{"id": 1}], 1))

    store = make_store(tmp_path)
    report = SyncReport()
    artifact = Artifact("/heroes", "heroes/index.json")

    with make_client(handler) as client:
        records = sync_one(client, store, artifact, report)

    assert records == [{"id": 1}]
    assert report.downloaded == 1
    assert report.failed == []
    assert store.exists(artifact.key)
    assert store.load_json(artifact.key)["total"] == 1


def test_sync_one_reads_existing_artifact_from_disk_without_a_request(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=envelope([{"id": 1}], 1))

    store = make_store(tmp_path)
    artifact = Artifact("/heroes", "heroes/index.json")
    with make_client(handler) as client:
        sync_one(client, store, artifact, SyncReport())
    calls.clear()

    with make_client(handler) as client:
        records = sync_one(client, store, artifact, SyncReport())

    assert calls == [], "an artifact present on disk must not be re-fetched"
    assert records == [{"id": 1}]


def test_force_ignores_the_stored_copy(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=envelope([{"id": len(calls)}], 1))

    store = make_store(tmp_path)
    artifact = Artifact("/heroes", "heroes/index.json")
    with make_client(handler) as client:
        sync_one(client, store, artifact, SyncReport())
    with make_client(handler) as client:
        sync_one(client, store, artifact, SyncReport())
    calls.clear()

    with make_client(handler) as client:
        records = sync_one(client, store, artifact, SyncReport(), force=True)

    assert len(calls) == 1
    assert records == [{"id": 1}]


def test_sync_many_isolates_failures(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/bad"):
            return httpx.Response(500, json={"status": "error", "message": "boom"})
        return httpx.Response(200, json=envelope([{"path": request.url.path}], 1))

    store = make_store(tmp_path)
    artifacts = [
        Artifact("/bad", "bad.json"),
        Artifact("/good", "good.json"),
    ]

    with make_client(handler) as client:
        report = sync_many(client, store, artifacts, SyncReport())

    assert report.downloaded == 1
    assert [failure.endpoint for failure in report.failed] == ["/bad"]
    assert store.exists("/good")


def test_optional_artifact_failure_is_unavailable_not_failed(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 10407, "message": "接口下线", "data": None},
        )

    store = make_store(tmp_path)
    artifact = Artifact("/academy/heroes/ratings", "ratings.json", optional=True)

    with make_client(handler) as client:
        report = sync_many(client, store, [artifact], SyncReport())

    assert report.failed == []
    assert [failure.endpoint for failure in report.unavailable] == ["/academy/heroes/ratings"]
    assert report.downloaded == 0


def test_check_one_reports_unchanged_then_changed(tmp_path: Path) -> None:
    revision = {"value": 1}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope([{"revision": revision["value"]}], 1))

    store = make_store(tmp_path)
    artifact = Artifact("/heroes", "heroes/index.json")
    with make_client(handler) as client:
        sync_one(client, store, artifact, SyncReport())

    report = CheckReport()
    with make_client(handler) as client:
        check_one(client, store, artifact, report)
    assert report.unchanged == 1
    assert report.changed == []

    revision["value"] = 2
    report = CheckReport()
    with make_client(handler) as client:
        check_one(client, store, artifact, report)
    assert report.changed == [artifact.key]
    assert report.unchanged == 0


def test_check_many_reports_new_and_missing(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope([{"id": 1}], 1))

    store = make_store(tmp_path)
    stored = Artifact("/stored", "stored.json")
    absent = Artifact("/absent", "absent.json")
    with make_client(handler) as client:
        sync_one(client, store, stored, SyncReport())
    (tmp_path / "stored.json").unlink()

    report = CheckReport()
    with make_client(handler) as client:
        check_many(client, store, [stored, absent], report)

    assert report.missing == [stored.key]
    assert report.new == [absent.key]


def test_check_manifest_touches_only_manifest_entries(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=envelope([{"id": 1}], 1))

    store = make_store(tmp_path)
    artifacts = [
        Artifact("/heroes", "heroes/index.json"),
        Artifact("/heroes/1/stats", "heroes/one/stats.json"),
    ]
    with make_client(handler) as client:
        sync_many(client, store, artifacts, SyncReport())
    calls.clear()

    report = CheckReport()
    with make_client(handler) as client:
        check_manifest(client, store, report, prefix="/heroes")

    assert len(calls) == 2
    assert report.unchanged == 2


def test_check_manifest_can_skip_the_index(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=envelope([{"id": 1}], 1))

    store = make_store(tmp_path)
    index = Artifact("/heroes", "heroes/index.json")
    detail = Artifact("/heroes/1", "heroes/one/detail.json")
    with make_client(handler) as client:
        sync_many(client, store, [index, detail], SyncReport())
    calls.clear()

    with make_client(handler) as client:
        check_manifest(client, store, CheckReport(), prefix="/heroes", skip={index.key})

    assert calls == ["/api/heroes/1"]


def test_check_manifest_ignores_other_domains(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=envelope([{"id": 1}], 1))

    store = make_store(tmp_path)
    artifacts = [
        Artifact("/heroes", "heroes/index.json"),
        Artifact("/academy/ranks", "academy/ranks.json"),
    ]
    with make_client(handler) as client:
        sync_many(client, store, artifacts, SyncReport())
    calls.clear()

    with make_client(handler) as client:
        check_manifest(client, store, CheckReport(), prefix="/academy")

    assert calls == ["/api/academy/ranks"]


def test_load_records_is_empty_when_the_artifact_is_absent(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    assert load_records(store, "/missing") == []


def test_check_reports_corrupted_local_file(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope([{"id": 1}], 1))

    store = make_store(tmp_path)
    artifact = Artifact("/heroes", "heroes/index.json")
    with make_client(handler) as client:
        sync_one(client, store, artifact, SyncReport())

    # corrupt the file on disk
    target = tmp_path / "heroes" / "index.json"
    target.write_text("corrupted", encoding="utf-8")

    report = CheckReport()
    with make_client(handler) as client:
        check_one(client, store, artifact, report)

    assert report.corrupted == [artifact.key]
    assert report.changed == []
    assert report.unchanged == 0
