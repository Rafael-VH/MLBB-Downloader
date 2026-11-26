from __future__ import annotations

import httpx
import pytest

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.errors import ApiError
from mlbb_downloader.usecases.addon import ip_location, win_rate_calculator


def make_client(handler, *, retries: int = 0) -> ArenaClient:
    return ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=retries,
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: None,
    )


def test_win_rate_calculator_sends_the_required_parameters() -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "status": "success",
                "match_now": 100,
                "wr_now": 50,
                "wr_future": 60,
                "required_no_lose_matches": 25,
                "message": "You need 25 consecutive wins",
            },
        )

    with make_client(handler) as client:
        result = win_rate_calculator(client, matches_now=100, win_rate_now=50, win_rate_future=60)

    assert result["required_no_lose_matches"] == 25
    assert seen[0]["match-now"] == "100"
    assert float(seen[0]["wr-now"]) == 50.0
    assert float(seen[0]["wr-future"]) == 60.0


def test_win_rate_calculator_surfaces_validation_messages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "status": "error",
                "code": "BAD_REQUEST",
                "message": "The target win rate (wr-future) must be greater",
            },
        )

    with make_client(handler) as client, pytest.raises(ApiError) as excinfo:
        win_rate_calculator(client, matches_now=100, win_rate_now=60, win_rate_future=50)

    assert "must be greater" in excinfo.value.message


def test_ip_location_returns_the_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/addon/ip"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "ok",
                "data": {"city": "Cochabamba", "country": "bo"},
            },
        )

    with make_client(handler) as client:
        payload = ip_location(client)

    assert payload["data"]["country"] == "bo"
