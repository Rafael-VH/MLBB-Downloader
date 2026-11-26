from __future__ import annotations

import httpx
import pytest

from mlbb_downloader.api.client import ArenaClient
from mlbb_downloader.api.errors import ApiError


def client_with(handler, *, retries: int = 0) -> ArenaClient:
    return ArenaClient(
        "https://api.test/api",
        delay=0.0,
        retries=retries,
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: None,
    )


def test_http_200_with_error_code_raises_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 10407,
                "message": "接口下线",
                "traceID": "t",
                "data": None,
            },
        )

    with client_with(handler) as client, pytest.raises(ApiError) as excinfo:
        client.get_json("/academy/heroes/ratings")

    assert excinfo.value.code == 10407
    assert excinfo.value.status == 200
    assert excinfo.value.message == "接口下线"


def test_http_200_with_success_code_is_accepted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 0, "message": "OK", "data": {"records": [], "total": 0}},
        )

    with client_with(handler) as client:
        payload = client.get_json("/academy/ranks")

    assert payload["code"] == 0


def test_payloads_without_code_are_accepted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "success", "required_no_lose_matches": 25},
        )

    with client_with(handler) as client:
        payload = client.get_json("/addon/win-rate-calculator")

    assert payload["required_no_lose_matches"] == 25
