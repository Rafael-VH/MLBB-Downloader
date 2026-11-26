"""Domain exceptions."""

from __future__ import annotations


class ApiError(Exception):
    """The API returned an error or the request could not be completed."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | int | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.url = url


class IncompletePageError(Exception):
    """The server reported a total that does not match what it delivered.

    This is fatal by design: silently storing partial data is worse than failing.
    """

    def __init__(self, endpoint: str, expected: int, received: int) -> None:
        super().__init__(f"{endpoint}: server reported {expected} records but delivered {received}")
        self.endpoint = endpoint
        self.expected = expected
        self.received = received


class JobCancelledError(Exception):
    """The user cancelled a running job."""
