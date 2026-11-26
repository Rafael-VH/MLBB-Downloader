"""Image sync/check use case.

Images are discovered from JSON artifacts already present in the store. This keeps
image extraction pure and makes image downloads resumable through the manifest.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.adapters.fsstore import DataStore
from mlbb_downloader.domain.images import (
    ImageAsset,
    extract_catalog_images,
    extract_hero_images,
    extract_index_images,
    extract_wallpaper_images,
)
from mlbb_downloader.errors import ApiError
from mlbb_downloader.usecases.engine import CheckReport, Failure, SyncReport

HEROES_PREFIX = "/heroes"
ACADEMY_CATALOG_ENDPOINT = "/academy/heroes/catalog"


def _hero_folder_from_path(path: str) -> str | None:
    parts = Path(path).parts
    if len(parts) >= 3 and parts[0] == "heroes":
        return parts[1]
    return None


def collect_image_assets(store: DataStore) -> list[ImageAsset]:
    """Discover image assets from JSON artifacts already in the store."""
    assets: list[ImageAsset] = []
    for key, item in store.manifest.items.items():
        if item.kind != "json":
            continue
        payload = store.load_json(key)
        if payload is None:
            continue

        endpoint = item.endpoint
        if endpoint == "/heroes":
            records = payload.get("records") or []
            if isinstance(records, list):
                for record in records:
                    if isinstance(record, dict):
                        assets.extend(extract_index_images(record))
            continue

        if endpoint == "/academy/heroes/catalog":
            records = payload.get("records") or []
            if isinstance(records, list):
                for record in records:
                    if isinstance(record, dict):
                        assets.extend(extract_catalog_images(record))
            continue

        if endpoint.startswith(HEROES_PREFIX + "/"):
            hero_id = item.params.get("hero_id")
            folder = _hero_folder_from_path(item.path)
            if not isinstance(hero_id, int) or not folder:
                continue
            if endpoint.endswith("/wallpapers"):
                assets.extend(extract_wallpaper_images(hero_id, folder, payload))
            elif endpoint == f"/heroes/{hero_id}":
                assets.extend(extract_hero_images(hero_id, folder, payload))

    deduped: list[ImageAsset] = []
    seen: set[str] = set()
    for asset in assets:
        if asset.key in seen:
            continue
        seen.add(asset.key)
        deduped.append(asset)
    return deduped


def sync_images(
    client: ArenaClient,
    store: DataStore,
    *,
    force: bool = False,
    flush_every: int = 25,
) -> SyncReport:
    started = time.monotonic()
    report = SyncReport()
    assets = collect_image_assets(store)

    for index, asset in enumerate(assets, start=1):
        if not force and store.exists(asset.key):
            report.skipped += 1
            continue
        try:
            result = client.get_bytes(asset.download_url)
        except ApiError as exc:
            report.failed.append(
                Failure(key=asset.key, endpoint=asset.download_url, error=str(exc))
            )
            continue

        store.save_bytes(
            asset.key,
            asset.relative_path,
            result.data,
            source_url=asset.canonical_url,
            content_type=result.content_type,
        )
        report.downloaded += 1
        if index % flush_every == 0:
            store.flush()

    store.flush()
    report.elapsed = time.monotonic() - started
    return report


def check_images(
    client: ArenaClient,
    store: DataStore,
) -> CheckReport:
    """Check image presence/integrity by re-downloading and comparing hashes.

    The API provides no ETag/Last-Modified; hash comparison is the only remote
    change signal, same as JSON artifacts.
    """
    started = time.monotonic()
    report = CheckReport()
    assets = collect_image_assets(store)

    for asset in assets:
        item = store.manifest.items.get(asset.key)
        if item is None:
            report.new.append(asset.key)
            continue
        target = store.root / item.path
        if not target.exists():
            report.missing.append(asset.key)
            continue

        disk_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if disk_hash != item.sha256:
            report.corrupted.append(asset.key)
            continue

        try:
            result = client.get_bytes(asset.download_url)
        except ApiError as exc:
            report.failed.append(
                Failure(key=asset.key, endpoint=asset.download_url, error=str(exc))
            )
            continue
        remote_hash = hashlib.sha256(result.data).hexdigest()
        if remote_hash != item.sha256:
            report.changed.append(asset.key)
        else:
            report.unchanged += 1

    report.elapsed = time.monotonic() - started
    return report
