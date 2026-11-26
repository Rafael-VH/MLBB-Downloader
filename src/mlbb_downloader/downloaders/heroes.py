"""Heroes domain, expressed on top of the generic artifact engine."""

from __future__ import annotations

import time
from dataclasses import dataclass

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.domain.keying import hero_identity, local_entity_ids
from mlbb_downloader.downloaders.engine import (
    Artifact,
    CheckReport,
    Failure,
    SyncReport,
    check_manifest,
    check_one,
    sync_many,
    sync_one,
)
from mlbb_downloader.adapters.fsstore import DataStore
from mlbb_downloader.domain.layout import sanitize_component

__all__ = [
    "HERO_SUBRESOURCES",
    "CheckReport",
    "Failure",
    "SyncReport",
    "check_heroes",
    "hero_identity",
    "sync_heroes",
]

INDEX_ENDPOINT = "/heroes"
INDEX_RELATIVE_PATH = "heroes/index.json"
INDEX = Artifact(INDEX_ENDPOINT, INDEX_RELATIVE_PATH)


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


def hero_artifacts(hero_id: int, folder: str) -> list[Artifact]:
    return [
        Artifact(
            endpoint=resource.template.format(hero_id=hero_id),
            relative_path=f"heroes/{folder}/{resource.name}.json",
            params={"hero_id": hero_id},
        )
        for resource in HERO_SUBRESOURCES
    ]


def sync_heroes(
    client: ArenaClient,
    store: DataStore,
    *,
    limit: int | None = None,
    force: bool = False,
    page_size: int | None = None,
) -> SyncReport:
    """Download hero data, skipping anything already stored."""
    started = time.monotonic()
    report = SyncReport()

    index_records = sync_one(client, store, INDEX, report, force=force, page_size=page_size) or []
    heroes = index_records if limit is None else index_records[:limit]

    artifacts = (
        artifact for hero in heroes for artifact in hero_artifacts(*_identity_fields(hero))
    )
    sync_many(
        client,
        store,
        artifacts,
        report,
        force=force,
        page_size=page_size,
    )

    report.elapsed = time.monotonic() - started
    return report


def check_heroes(
    client: ArenaClient,
    store: DataStore,
    *,
    page_size: int | None = None,
) -> CheckReport:
    """Compare remote data against local artifacts.

    Work is proportional to what is stored locally: heroes never downloaded are
    reported as a count, not fetched item by item.
    """
    started = time.monotonic()
    report = CheckReport()

    index_records = check_one(client, store, INDEX, report, page_size=page_size) or []

    local_ids = local_entity_ids(store.manifest, INDEX_ENDPOINT)
    for hero in index_records:
        hero_id, _ = hero_identity(hero)
        if hero_id not in local_ids:
            report.not_downloaded += 1

    check_manifest(
        client,
        store,
        report,
        prefix=INDEX_ENDPOINT,
        skip={INDEX.key},
        page_size=page_size,
    )

    report.elapsed = time.monotonic() - started
    return report


def _identity_fields(record: dict) -> tuple[int | None, str]:
    hero_id, name = hero_identity(record)
    return hero_id, sanitize_component(name)
