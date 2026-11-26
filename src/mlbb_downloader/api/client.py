"""HTTP client for the Rone Arena API.

Runtime facts this client is built around (verified against the live API):
- Responses are compressed with zstd by default; gzip is accepted and is used here
  so the project does not need an extra decoder dependency.
- Pagination uses ``size`` (max 500) and ``index``, which is a 1-based page number.
  ``index=0`` returns an empty page with HTTP 200, so pagination starts at 1.
- No ETag and no Last-Modified headers are sent; content hashes are the only signal.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from mlbb_downloader import __version__
from mlbb_downloader.api.errors import ApiError, IncompletePageError
from mlbb_downloader.config import (
    DEFAULT_BASE_URL,
    DEFAULT_DELAY,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
)

MAX_PAGE_SIZE = 500
MAX_PAGES = 10_000
RETRY_STATUS = frozenset({403, 405, 408, 425, 429, 500, 502, 503, 504})


@dataclass(slots=True)
class PagedResult:
    endpoint: str
    records: list[dict[str, Any]] = field(default_factory=list)
    total: int | None = None
    pages: int = 0


class ArenaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        delay: float = DEFAULT_DELAY,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        page_size: int = DEFAULT_PAGE_SIZE,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        user_agent: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.retries = retries
        self.page_size = min(page_size, MAX_PAGE_SIZE)
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self._client = httpx.Client(
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
            headers={
                "accept": "application/json",
                "accept-encoding": "gzip",
                "user-agent": user_agent or f"mlbb-downloader/{__version__}",
            },
        )

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ArenaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- public API --------------------------------------------------------
    def get_json(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self._url(path)
        query = {key: value for key, value in (params or {}).items() if value is not None}
        attempt = 0
        while True:
            try:
                self._wait()
                response = self._client.get(url, params=query)
            except httpx.HTTPError as exc:
                if attempt >= self.retries:
                    raise ApiError(f"request failed: {exc}", url=url) from exc
                self._backoff(attempt)
                attempt += 1
                continue

            if response.status_code in RETRY_STATUS and attempt < self.retries:
                self._backoff(attempt)
                attempt += 1
                continue

            if response.status_code >= 400:
                raise self._error_from(response, url)

            try:
                payload = response.json()
            except ValueError as exc:
                raise ApiError(
                    "response was not valid JSON",
                    status=response.status_code,
                    url=url,
                ) from exc

            if not isinstance(payload, dict):
                raise ApiError("response was not a JSON object", url=url)
            return payload

    def get_paged(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        size: int | None = None,
    ) -> PagedResult:
        page_size = min(size or self.page_size, MAX_PAGE_SIZE)
        base = dict(params or {})
        records: list[dict[str, Any]] = []
        total: int | None = None
        page = 1

        while True:
            payload = self.get_json(path, {**base, "size": page_size, "index": page})
            data = payload.get("data")
            if not isinstance(data, dict):
                raise ApiError(f"{path}: expected a 'data' object", url=path)

            batch = data.get("records") or []
            if not isinstance(batch, list):
                raise ApiError(f"{path}: 'data.records' is not a list", url=path)

            page_total = data.get("total")
            if isinstance(page_total, int):
                total = page_total

            records.extend(batch)

            if not batch:
                break
            if total is not None and len(records) >= total:
                break

            page += 1
            if page > MAX_PAGES:
                raise ApiError(f"{path}: exceeded {MAX_PAGES} pages", url=path)

        if total is not None and len(records) != total:
            raise IncompletePageError(path, total, len(records))

        return PagedResult(endpoint=path, records=records, total=total, pages=page)

    # -- internals ---------------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _wait(self) -> None:
        now = self._clock()
        if self._last_request is not None:
            remaining = self.delay - (now - self._last_request)
            if remaining > 0:
                self._sleep(remaining)
                now = self._clock()
        self._last_request = now

    def _backoff(self, attempt: int) -> None:
        self._sleep(min(self.delay * (2**attempt), 30.0))

    @staticmethod
    def _error_from(response: httpx.Response, url: str) -> ApiError:
        code: str | int | None = None
        message = f"HTTP {response.status_code}"
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            code = body.get("code")
            message = body.get("message") or message
        return ApiError(message, status=response.status_code, code=code, url=url)
