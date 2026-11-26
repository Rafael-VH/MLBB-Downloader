"""Interactive addon tools.

These are one-shot utilities, never part of a bulk download. The win-rate
endpoint answers with ``{status: "success", ...}`` instead of the standard
envelope, so no payload model is applied here either.
"""

from __future__ import annotations

from typing import Any

from mlbb_downloader.adapters.arena import ArenaClient

WIN_RATE_PATH = "/addon/win-rate-calculator"
IP_PATH = "/addon/ip"


def win_rate_calculator(
    client: ArenaClient,
    *,
    matches_now: int,
    win_rate_now: float,
    win_rate_future: float,
) -> dict[str, Any]:
    """Consecutive wins required to reach a target win rate."""
    return client.get_json(
        WIN_RATE_PATH,
        {
            "match-now": matches_now,
            "wr-now": win_rate_now,
            "wr-future": win_rate_future,
        },
    )


def ip_location(client: ArenaClient) -> dict[str, Any]:
    """Location the API resolves for the caller's IP."""
    return client.get_json(IP_PATH)
