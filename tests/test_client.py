from __future__ import annotations

import httpx
import pytest

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.errors import ApiError


def client_with(handler, *, retries: int = 0, sleeps: list[float] | None = None) -> ArenaClient:
    recorded = sleeps if sleeps is not None else []
    return ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=retries,
        transport=httpx.MockTransport(handler),
        sleep=recorded.append,
    )


def test_retries_transient_server_errors_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, json={"status": "error", "code": "UNAVAILABLE"})
        return httpx.Response(200, json={"data": {"records": [], "total": 0}})

    sleeps: list[float] = []
    with client_with(handler, retries=3, sleeps=sleeps) as client:
        payload = client.get_json("/heroes")

    assert payload["data"]["total"] == 0
    assert calls["n"] == 3
    assert len(sleeps) == 2, "each retry must back off"


def test_client_error_is_not_retried_and_surfaces_message() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            400,
            json={
                "status": "error",
                "code": "BAD_REQUEST",
                "message": "The target win rate must be greater",
                "timestamp": "2026-11-26T00:00:00Z",
            },
        )

    with client_with(handler, retries=3) as client, pytest.raises(ApiError) as excinfo:
        client.get_json("/addon/win-rate-calculator")

    assert calls["n"] == 1
    assert excinfo.value.status == 400
    assert excinfo.value.code == "BAD_REQUEST"
    assert "target win rate" in excinfo.value.message


def test_requests_gzip_only() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("accept-encoding", ""))
        return httpx.Response(200, json={"data": {"records": [], "total": 0}})

    with client_with(handler) as client:
        client.get_json("/heroes")

    assert seen == ["gzip"], "zstd is avoided on purpose to drop the extra dependency"


def test_throttle_waits_between_requests() -> None:
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"records": [], "total": 0}})

    client = ArenaClient(
        "https://api.test/api",
        delay=1.0,
        retries=0,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        clock=lambda: 0.0,
    )
    with client:
        client.get_json("/heroes")
        assert sleeps == [], "first request must not wait"
        client.get_json("/heroes")

    assert sleeps == [1.0]


def test_network_errors_become_api_errors_after_retries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with client_with(handler, retries=1) as client, pytest.raises(ApiError):
        client.get_json("/heroes")
