"""Pure image extraction and normalization.

The domain decides *which* image assets exist and how they are named; adapters
download bytes and persist them. This module has no IO.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from mlbb_downloader.domain.keying import canonical_image_url
from mlbb_downloader.domain.layout import sanitize_component

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}


@dataclass(frozen=True, slots=True)
class ImageAsset:
    """A downloadable image discovered inside a JSON artifact."""

    key: str
    download_url: str
    canonical_url: str
    relative_path: str
    category: str
    hero_id: int | None = None


def ext_from_url(url: str) -> str:
    path = urlsplit(canonical_image_url(url)).path
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".jpeg":
        return ".jpg"
    if suffix in IMAGE_EXTENSIONS:
        return suffix
    return ".bin"


def _asset(
    url: Any, relative_path: str, category: str, hero_id: int | None = None
) -> ImageAsset | None:
    if not isinstance(url, str) or not url.strip():
        return None
    download_url = url.strip()
    canonical = canonical_image_url(download_url)
    if not canonical.startswith(("http://", "https://")):
        return None
    return ImageAsset(
        key=f"image::{canonical}",
        download_url=download_url,
        canonical_url=canonical,
        relative_path=relative_path,
        category=category,
        hero_id=hero_id,
    )


def _dedupe(assets: list[ImageAsset | None]) -> list[ImageAsset]:
    seen: set[str] = set()
    result: list[ImageAsset] = []
    for asset in assets:
        if asset is None or asset.key in seen:
            continue
        seen.add(asset.key)
        result.append(asset)
    return result


def payload_records(payload: Any) -> list[dict[str, Any]]:
    """Accept a stored artifact payload, a raw API envelope, or a record list."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    records = payload.get("records")
    if isinstance(records, list):
        return [r for r in records if isinstance(r, dict)]
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return [r for r in data["records"] if isinstance(r, dict)]
    return []


def extract_hero_images(
    hero_id: int, hero_folder: str, detail_payload: dict[str, Any] | list[dict[str, Any]]
) -> list[ImageAsset]:
    """Extract image assets from a ``/heroes/{id}`` detail record."""
    folder = sanitize_component(hero_folder)
    records = payload_records(detail_payload)
    detail_record = (
        records[0] if records else (detail_payload if isinstance(detail_payload, dict) else {})
    )
    data = (
        detail_record.get("data") if isinstance(detail_record.get("data"), dict) else detail_record
    )
    if not isinstance(data, dict):
        return []

    assets: list[ImageAsset | None] = []
    base = f"heroes/{folder}/images"

    for field in ("head", "head_big"):
        assets.append(
            _asset(
                data.get(field),
                f"{base}/{field}{ext_from_url(str(data.get(field, '')))}",
                "hero",
                hero_id,
            )
        )

    hero = data.get("hero")
    hero_data = (
        hero.get("data") if isinstance(hero, dict) and isinstance(hero.get("data"), dict) else {}
    )
    for field in ("head", "painting", "smallmap", "squarehead", "squareheadbig"):
        assets.append(
            _asset(
                hero_data.get(field),
                f"{base}/{field}{ext_from_url(str(hero_data.get(field, '')))}",
                "hero",
                hero_id,
            )
        )
    for field in ("roadsorticon1", "roadsorticon2", "sorticon1", "sorticon2"):
        assets.append(
            _asset(
                hero_data.get(field),
                f"{base}/{field}{ext_from_url(str(hero_data.get(field, '')))}",
                "hero",
                hero_id,
            )
        )

    skill_list = hero_data.get("heroskilllist")
    if isinstance(skill_list, list):
        for idx, skill_group in enumerate(skill_list):
            items = skill_group.get("skilllist") if isinstance(skill_group, dict) else None
            if not isinstance(items, list):
                continue
            for skill in items:
                if not isinstance(skill, dict):
                    continue
                skill_id = skill.get("skillid") or idx
                icon = skill.get("skillicon")
                name = sanitize_component(
                    str(skill.get("skillname") or f"skill-{skill_id}")
                ).replace(" ", "_")
                assets.append(
                    _asset(
                        icon,
                        f"{base}/skills/{skill_id}-{name}{ext_from_url(str(icon or ''))}",
                        "skill",
                        hero_id,
                    )
                )

    return _dedupe(assets)


def extract_wallpaper_images(
    hero_id: int, hero_folder: str, wallpaper_payload: dict[str, Any] | list[dict[str, Any]]
) -> list[ImageAsset]:
    """Extract wallpaper images from ``/heroes/{id}/wallpapers`` payload."""
    folder = sanitize_component(hero_folder)
    records = payload_records(wallpaper_payload)
    assets: list[ImageAsset | None] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        rec_data = record.get("data") if isinstance(record.get("data"), dict) else {}
        skinid = sanitize_component(
            str(rec_data.get("skinid") or record.get("caption") or record.get("id") or "wallpaper")
        )
        pictures = rec_data.get("pictures")
        if not isinstance(pictures, list):
            continue
        for pic in pictures:
            if not isinstance(pic, dict):
                continue
            url = pic.get("url")
            resolution = sanitize_component(str(pic.get("resolution") or "unknown"))
            ext = ext_from_url(str(url or ""))
            assets.append(
                _asset(
                    url,
                    f"heroes/{folder}/wallpapers/{skinid}-{resolution}{ext}",
                    "wallpaper",
                    hero_id,
                )
            )
    return _dedupe(assets)


def extract_catalog_images(record: dict[str, Any]) -> list[ImageAsset]:
    """Extract images from an academy catalog hero record."""
    data = record.get("data") if isinstance(record.get("data"), dict) else record
    if not isinstance(data, dict):
        return []
    hero_id = data.get("hero_id") or record.get("hero_id")
    hid = hero_id if isinstance(hero_id, int) else None
    hero = data.get("hero")
    hero_data = (
        hero.get("data") if isinstance(hero, dict) and isinstance(hero.get("data"), dict) else {}
    )
    name = sanitize_component(
        str(hero_data.get("name") or (f"hero-{hid}" if hid is not None else "unknown-hero"))
    )
    folder = name
    base = f"academy/catalog/{folder}/images"
    assets: list[ImageAsset | None] = []
    for field in ("head", "head_big", "painting"):
        value = data.get(field)
        assets.append(
            _asset(value, f"{base}/{field}{ext_from_url(str(value or ''))}", "catalog", hid)
        )
    return _dedupe(assets)


def extract_index_images(record: dict[str, Any]) -> list[ImageAsset]:
    """Extract images from a ``/heroes`` index record."""
    data = record.get("data") if isinstance(record.get("data"), dict) else record
    if not isinstance(data, dict):
        return []
    hero_id = record.get("hero_id") or data.get("hero_id")
    hid = hero_id if isinstance(hero_id, int) else None
    hero = data.get("hero")
    hero_data = (
        hero.get("data") if isinstance(hero, dict) and isinstance(hero.get("data"), dict) else {}
    )
    name = sanitize_component(
        str(hero_data.get("name") or (f"hero-{hid}" if hid is not None else "unknown-hero"))
    )
    base = f"heroes/{name}/images"
    assets: list[ImageAsset | None] = []
    for field in ("head", "smallmap"):
        value = hero_data.get(field)
        assets.append(
            _asset(value, f"{base}/{field}{ext_from_url(str(value or ''))}", "index", hid)
        )
    return _dedupe(assets)
