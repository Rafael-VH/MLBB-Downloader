"""Academy domain: game data for heroes, items and the progression system.

Expressed on top of the generic artifact engine. Two passes:

1. Collections and per-hero artifacts, including the ``lane`` artifact.
2. ``builds`` and ``win-rate`` for the lanes each hero actually plays, read
   back from the stored lane artifact.

User-generated content (``/recommended``) and endpoints that duplicate another
artifact (``/ranks/{rank_id}``) are catalogued in the registry but never
enumerated. See ``odd/tasks/academy-addon.md`` for the measurements behind that
decision.
"""

from __future__ import annotations

import time
from typing import Any

from mlbb_downloader.api.client import ArenaClient
from mlbb_downloader.domain.registry import (
    ACADEMY_CATALOG,
    ACADEMY_EMBLEMS,
    ACADEMY_EQUIPMENT,
    ACADEMY_EQUIPMENT_EXPANDED,
    ACADEMY_HERO_BUILDS,
    ACADEMY_HERO_COUNTERS,
    ACADEMY_HERO_FILTER,
    ACADEMY_HERO_LANE,
    ACADEMY_HERO_STATS,
    ACADEMY_HERO_TEAMMATES,
    ACADEMY_HERO_TRENDS,
    ACADEMY_HERO_WIN_RATE,
    ACADEMY_RANKS,
    ACADEMY_ROLES,
    ACADEMY_SPELLS,
    ACADEMY_VERSION,
    EndpointSpec,
)
from mlbb_downloader.domain.keying import hero_identity, item_key, local_entity_ids
from mlbb_downloader.downloaders.engine import (
    Artifact,
    CheckReport,
    SyncReport,
    check_manifest,
    check_one,
    load_records,
    sync_many,
    sync_one,
)
from mlbb_downloader.storage.store import DataStore
from mlbb_downloader.domain.layout import sanitize_component

ACADEMY_PREFIX = "/academy"


def _collection(spec: EndpointSpec, relative_path: str) -> Artifact:
    return Artifact(spec.path, relative_path)


VERSION = _collection(ACADEMY_VERSION, "academy/version.json")
CATALOG = _collection(ACADEMY_CATALOG, "academy/heroes/catalog.json")
ROLES = _collection(ACADEMY_ROLES, "academy/roles.json")
EQUIPMENT = _collection(ACADEMY_EQUIPMENT, "academy/equipment.json")
EQUIPMENT_EXPANDED = _collection(ACADEMY_EQUIPMENT_EXPANDED, "academy/equipment-expanded.json")
SPELLS = _collection(ACADEMY_SPELLS, "academy/spells.json")
EMBLEMS = _collection(ACADEMY_EMBLEMS, "academy/emblems.json")
RANKS = _collection(ACADEMY_RANKS, "academy/ranks.json")
HERO_FILTER = _collection(ACADEMY_HERO_FILTER, "academy/heroes/filter.json")

ACADEMY_COLLECTIONS: tuple[Artifact, ...] = (
    VERSION,
    CATALOG,
    ROLES,
    EQUIPMENT,
    EQUIPMENT_EXPANDED,
    SPELLS,
    EMBLEMS,
    RANKS,
    HERO_FILTER,
)

HERO_RESOURCE_SPECS: tuple[tuple[EndpointSpec, str], ...] = (
    (ACADEMY_HERO_LANE, "lane"),
    (ACADEMY_HERO_STATS, "stats"),
    (ACADEMY_HERO_COUNTERS, "counters"),
    (ACADEMY_HERO_TEAMMATES, "teammates"),
    (ACADEMY_HERO_TRENDS, "trends"),
)

LANE_RESOURCE_SPECS: tuple[tuple[EndpointSpec, str], ...] = (
    (ACADEMY_HERO_BUILDS, "builds"),
    (ACADEMY_HERO_WIN_RATE, "win-rate"),
)

LANE_SORT_IDS: dict[str, str] = {
    "1": "exp",
    "2": "mid",
    "3": "roam",
    "4": "jungle",
    "5": "gold",
}

LANE_TITLES: dict[str, str] = {
    "exp lane": "exp",
    "experience lane": "exp",
    "mid lane": "mid",
    "roam": "roam",
    "roam lane": "roam",
    "jungle": "jungle",
    "gold lane": "gold",
}


def hero_lanes(records: list[dict[str, Any]]) -> list[str]:
    """Lanes a hero actually plays, in upstream order, without duplicates."""
    lanes: list[str] = []
    for record in records:
        data = record.get("data") if isinstance(record, dict) else None
        hero = data.get("hero") if isinstance(data, dict) else None
        hero_data = hero.get("data") if isinstance(hero, dict) else None
        roads = hero_data.get("roadsort") if isinstance(hero_data, dict) else None

        for road in roads or []:
            road_data = road.get("data") if isinstance(road, dict) else None
            if not isinstance(road_data, dict):
                continue
            lane = LANE_SORT_IDS.get(str(road_data.get("road_sort_id")))
            if lane is None:
                title = str(road_data.get("road_sort_title") or "").strip().lower()
                lane = LANE_TITLES.get(title)
            if lane is not None and lane not in lanes:
                lanes.append(lane)

    return lanes


def lane_key(hero_id: int) -> str:
    endpoint = ACADEMY_HERO_LANE.path.format(hero_identifier=hero_id)
    return item_key(endpoint, {"hero_id": hero_id})


def hero_artifacts(hero_id: int, folder: str) -> list[Artifact]:
    return [
        Artifact(
            endpoint=spec.path.format(hero_identifier=hero_id),
            relative_path=f"academy/heroes/{folder}/{name}.json",
            params={"hero_id": hero_id},
        )
        for spec, name in HERO_RESOURCE_SPECS
    ]


def lane_artifacts(hero_id: int, folder: str, lanes: list[str]) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for spec, name in LANE_RESOURCE_SPECS:
        for lane in lanes:
            artifacts.append(
                Artifact(
                    endpoint=spec.path.format(hero_identifier=hero_id),
                    relative_path=f"academy/heroes/{folder}/{name}-{lane}.json",
                    params={"hero_id": hero_id, "lane": lane},
                )
            )
    return artifacts


def _identities(
    catalog_records: list[dict[str, Any]],
    limit: int | None,
) -> list[tuple[int, str]]:
    heroes = catalog_records if limit is None else catalog_records[:limit]
    identities: list[tuple[int, str]] = []
    for record in heroes:
        hero_id, name = hero_identity(record)
        if hero_id is None:
            continue
        identities.append((hero_id, sanitize_component(name)))
    return identities


def sync_academy(
    client: ArenaClient,
    store: DataStore,
    *,
    limit: int | None = None,
    force: bool = False,
    page_size: int | None = None,
) -> SyncReport:
    """Download academy game data, skipping anything already stored."""
    started = time.monotonic()
    report = SyncReport()

    catalog_records = (
        sync_one(client, store, CATALOG, report, force=force, page_size=page_size) or []
    )
    sync_many(
        client,
        store,
        (artifact for artifact in ACADEMY_COLLECTIONS if artifact is not CATALOG),
        report,
        force=force,
        page_size=page_size,
    )

    identities = _identities(catalog_records, limit)
    sync_many(
        client,
        store,
        (
            artifact
            for hero_id, folder in identities
            for artifact in hero_artifacts(hero_id, folder)
        ),
        report,
        force=force,
        page_size=page_size,
    )

    lane_tasks: list[Artifact] = []
    for hero_id, folder in identities:
        lanes = hero_lanes(load_records(store, lane_key(hero_id)))
        lane_tasks.extend(lane_artifacts(hero_id, folder, lanes))

    if lane_tasks:
        sync_many(
            client,
            store,
            lane_tasks,
            report,
            force=force,
            page_size=page_size,
        )

    store.flush()
    report.elapsed = time.monotonic() - started
    return report


def check_academy(
    client: ArenaClient,
    store: DataStore,
    *,
    page_size: int | None = None,
) -> CheckReport:
    """Compare remote academy data against local artifacts.

    Only the catalog is fetched to count heroes never downloaded; everything
    else is checked from the manifest, so cost tracks the local dataset.
    """
    started = time.monotonic()
    report = CheckReport()

    catalog_records = check_one(client, store, CATALOG, report, page_size=page_size) or []

    local_ids = local_entity_ids(store.manifest, ACADEMY_PREFIX)
    for record in catalog_records:
        hero_id, _ = hero_identity(record)
        if hero_id not in local_ids:
            report.not_downloaded += 1

    check_manifest(
        client,
        store,
        report,
        prefix=ACADEMY_PREFIX,
        skip={CATALOG.key},
        page_size=page_size,
    )

    report.elapsed = time.monotonic() - started
    return report
