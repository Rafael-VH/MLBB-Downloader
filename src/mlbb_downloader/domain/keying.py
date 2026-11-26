"""Stable artifact keys and entity identity extraction.

The API is a thin proxy over game tables, so the same entity exposes its id and
name at different nesting levels depending on the endpoint. These helpers
centralise the defensive extraction so every domain reads identity the same way.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from mlbb_downloader.domain.manifest import Manifest


def item_key(endpoint: str, params: dict[str, Any] | None = None) -> str:
    """Stable identity for a logical artifact, independent of parameter order."""
    clean = {key: value for key, value in (params or {}).items() if value is not None}
    if not clean:
        return endpoint
    query = urlencode(sorted(clean.items(), key=lambda pair: pair[0]))
    return f"{endpoint}?{query}"


def hero_identity(record: dict[str, Any]) -> tuple[int | None, str]:
    """Extract the canonical hero id and display name from a raw record."""
    payload = record.get("data") if isinstance(record.get("data"), dict) else record
    hero_id = record.get("hero_id") or payload.get("hero_id")

    hero = payload.get("hero")
    inner = (
        hero.get("data") if isinstance(hero, dict) and isinstance(hero.get("data"), dict) else hero
    )
    name = None
    if isinstance(inner, dict):
        name = inner.get("name")
    if not name:
        name = record.get("name") or payload.get("name")

    fallback = f"hero-{hero_id}" if hero_id is not None else "unknown-hero"
    return hero_id, str(name or fallback)


def local_entity_ids(
    manifest: Manifest,
    prefix: str,
    param: str = "hero_id",
) -> set[int]:
    """Entity ids for which at least one artifact exists under ``prefix``."""
    return {
        value
        for item in manifest.items.values()
        if item.endpoint.startswith(prefix) and isinstance((value := item.params.get(param)), int)
    }
