"""Heroes domain: the vertical slice that proves the engine."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from mlbb_downloader.api.client import ArenaClient
from mlbb_downloader.api.errors import ApiError, IncompletePageError
from mlbb_downloader.storage.store import DataStore, serialize_json
from mlbb_downloader.utils.slug import sanitize_component

INDEX_ENDPOINT = "/heroes"
INDEX_RELATIVE_PATH = "heroes/index.json"


@dataclass(frozen=True, slots=True)
class HeroResource:
    name: str
    template: str


HERO_SUBRESOURCES: tuple[HeroResource, ...] = (
    HeroResource("detail", "/heroes/{hero_id}"),
    HeroResource("stats", "/heroes/{hero_id}/stats"),
    HeroResource("skill-combos", "/heroes/{hero_id}/skill-combos"),
    HeroResource("trends", "/heroes/{hero_id}/trends"),
    HeroResource("relations", "/heroes/{hero_id}/relations"),
    HeroResource("counters", "/heroes/{hero_id}/counters"),
    HeroResource("compatibility", "/heroes/{hero_id}/compatibility"),
    HeroResource("wallpapers", "/heroes/{hero_id}/wallpapers"),
)


@dataclass(slots=True)
class Failure:
    key: str
    endpoint: str
    error: str


@dataclass(slots=True)
class SyncReport:
    downloaded: int = 0
    skipped: int = 0
    failed: list[Failure] = field(default_factory=list)
    elapsed: float = 0.0


@dataclass(slots=True)
class CheckReport:
    unchanged: int = 0
    changed: list[str] = field(default_factory=list)
    new: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    not_downloaded: int = 0
    failed: list[Failure] = field(default_factory=list)
    elapsed: float = 0.0


def hero_identity(record: dict[str, Any]) -> tuple[int | None, str]:
    """Extract the canonical hero id and display name from a raw record.

    The API is a thin proxy over game tables, so the id may sit at the top level
    or inside ``data``; the name may sit one or two ``data`` levels down.
    """
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


def _artifact_payload(endpoint: str, records: list[dict[str, Any]], total: int | None) -> dict:
    return {"endpoint": endpoint, "total": total, "records": records}


def _local_hero_ids(store: DataStore) -> set[int]:
    ids: set[int] = set()
    for item in store.manifest.items.values():
        hero_id = item.params.get("hero_id")
        if isinstance(hero_id, int):
            ids.add(hero_id)
    return ids


def sync_heroes(
    client: ArenaClient,
    store: DataStore,
    *,
    limit: int | None = None,
    force: bool = False,
    page_size: int | None = None,
) -> SyncReport:
    started = time.monotonic()
    report = SyncReport()

    index = client.get_paged(INDEX_ENDPOINT, size=page_size)
    index_key = store.manifest_key_for(INDEX_ENDPOINT, {})
    index_payload = _artifact_payload(INDEX_ENDPOINT, index.records, index.total)

    if force or not store.exists(index_key):
        store.save_json(
            index_key,
            INDEX_RELATIVE_PATH,
            index_payload,
            endpoint=INDEX_ENDPOINT,
            total=index.total,
        )
        report.downloaded += 1
    else:
        report.skipped += 1

    heroes = index.records if limit is None else index.records[:limit]

    for hero in heroes:
        hero_id, name = hero_identity(hero)
        folder = sanitize_component(name)
        params = {"hero_id": hero_id}

        for resource in HERO_SUBRESOURCES:
            endpoint = resource.template.format(hero_id=hero_id)
            key = store.manifest_key_for(endpoint, params)

            if not force and store.exists(key):
                report.skipped += 1
                continue

            try:
                fetched = client.get_paged(endpoint, size=page_size)
            except (ApiError, IncompletePageError) as exc:
                report.failed.append(Failure(key=key, endpoint=endpoint, error=str(exc)))
                continue

            store.save_json(
                key,
                f"heroes/{folder}/{resource.name}.json",
                _artifact_payload(endpoint, fetched.records, fetched.total),
                endpoint=endpoint,
                params=params,
                total=fetched.total,
            )
            report.downloaded += 1

        store.flush()

    store.flush()
    report.elapsed = time.monotonic() - started
    return report


def check_heroes(
    client: ArenaClient,
    store: DataStore,
    *,
    limit: int | None = None,
    page_size: int | None = None,
) -> CheckReport:
    """Compare remote data against local artifacts.

    Work is proportional to what is stored locally: heroes never downloaded are
    reported as counts, not fetched item by item.
    """
    started = time.monotonic()
    report = CheckReport()

    index = client.get_paged(INDEX_ENDPOINT, size=page_size)
    _compare(
        store,
        INDEX_ENDPOINT,
        {},
        _artifact_payload(INDEX_ENDPOINT, index.records, index.total),
        report,
    )

    local_ids = _local_hero_ids(store)
    heroes = index.records if limit is None else index.records[:limit]

    for hero in index.records:
        hero_id, _ = hero_identity(hero)
        if hero_id not in local_ids:
            report.not_downloaded += 1

    for hero in heroes:
        hero_id, _ = hero_identity(hero)
        if hero_id not in local_ids:
            continue
        params = {"hero_id": hero_id}

        for resource in HERO_SUBRESOURCES:
            endpoint = resource.template.format(hero_id=hero_id)
            try:
                fetched = client.get_paged(endpoint, size=page_size)
            except (ApiError, IncompletePageError) as exc:
                report.failed.append(Failure(key=endpoint, endpoint=endpoint, error=str(exc)))
                continue
            _compare(
                store,
                endpoint,
                params,
                _artifact_payload(endpoint, fetched.records, fetched.total),
                report,
            )

    report.elapsed = time.monotonic() - started
    return report


def _compare(
    store: DataStore,
    endpoint: str,
    params: dict[str, Any],
    payload: dict,
    report: CheckReport,
) -> None:
    key = store.manifest_key_for(endpoint, params)
    item = store.manifest.items.get(key)

    if item is None:
        report.new.append(key)
        return

    target = store.root / item.path
    if not target.exists():
        report.missing.append(key)
        return

    digest = hashlib.sha256(serialize_json(payload)).hexdigest()
    if digest != item.sha256:
        report.changed.append(key)
        return

    report.unchanged += 1
