from __future__ import annotations

import httpx
import pytest

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.errors import IncompletePageError


def envelope(records: list, total: int) -> dict:
    return {
        "code": 200,
        "message": "ok",
        "data": {"records": records, "total": total},
        "traceID": "test",
    }


def client_with(handler) -> ArenaClient:
    return ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=0,
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: None,
    )


def test_paginates_until_total_and_starts_at_page_one() -> None:
    pages = {
        1: [{"id": 1}, {"id": 2}],
        2: [{"id": 3}, {"id": 4}],
        3: [{"id": 5}],
    }
    seen: list[tuple[int, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        index = int(request.url.params["index"])
        size = int(request.url.params["size"])
        seen.append((index, size))
        return httpx.Response(200, json=envelope(pages.get(index, []), 5))

    with client_with(handler) as client:
        result = client.get_paged("/heroes", size=2)

    assert [record["id"] for record in result.records] == [1, 2, 3, 4, 5]
    assert result.total == 5
    assert result.pages == 3
    assert seen[0] == (1, 2), "pagination must start at page 1, never 0"


def test_incomplete_result_raises_instead_of_returning_partial_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        index = int(request.url.params["index"])
        records = [{"id": 1}] if index == 1 else []
        return httpx.Response(200, json=envelope(records, 10))

    with client_with(handler) as client, pytest.raises(IncompletePageError) as excinfo:
        client.get_paged("/heroes", size=5)

    assert excinfo.value.expected == 10
    assert excinfo.value.received == 1


def test_empty_collection_is_not_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope([], 0))

    with client_with(handler) as client:
        result = client.get_paged("/heroes", size=5)

    assert result.records == []
    assert result.total == 0
    assert result.pages == 1


def test_page_size_is_capped_at_server_maximum() -> None:
    seen: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(int(request.url.params["size"]))
        return httpx.Response(200, json=envelope([], 0))

    with client_with(handler) as client:
        client.get_paged("/heroes", size=1000)

    assert seen == [500]


def test_missing_total_still_paginates_until_empty_page() -> None:
    pages = {1: [{"id": 1}], 2: [{"id": 2}], 3: []}

    def handler(request: httpx.Request) -> httpx.Response:
        index = int(request.url.params["index"])
        payload = {
            "code": 200,
            "message": "ok",
            "data": {"records": pages.get(index, [])},
        }
        return httpx.Response(200, json=payload)

    with client_with(handler) as client:
        result = client.get_paged("/heroes", size=1)

    assert [record["id"] for record in result.records] == [1, 2]
    assert result.total is None
    assert result.pages == 3
