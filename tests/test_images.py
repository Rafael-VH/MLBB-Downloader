from __future__ import annotations

from mlbb_downloader.domain.images import (
    extract_catalog_images,
    extract_hero_images,
    extract_index_images,
    extract_wallpaper_images,
)


def stored(payload_records: list[dict]) -> dict:
    return {"endpoint": "/x", "total": len(payload_records), "records": payload_records}


def test_extract_wallpaper_images_from_stored_payload() -> None:
    payload = stored(
        [
            {
                "id": 1,
                "data": {
                    "skinid": "skin01",
                    "pictures": [
                        {
                            "resolution": "1920x1080",
                            "url": "https://wsrv.nl/?url=https%3A%2F%2Fcdn.test%2Fa.jpg",
                        },
                        {
                            "resolution": "2560x1440",
                            "url": "https://wsrv.nl/?url=https%3A%2F%2Fcdn.test%2Fb.png",
                        },
                    ],
                },
            }
        ]
    )

    assets = extract_wallpaper_images(1, "Miya", payload)

    assert len(assets) == 2
    assert assets[0].canonical_url == "https://cdn.test/a.jpg"
    assert assets[0].relative_path == "heroes/Miya/wallpapers/skin01-1920x1080.jpg"
    assert assets[1].relative_path == "heroes/Miya/wallpapers/skin01-2560x1440.png"


def test_extract_hero_images_finds_head_painting_and_skill_icons() -> None:
    record = {
        "data": {
            "head": "https://cdn.test/head.jpg",
            "head_big": "https://cdn.test/head_big.jpg",
            "hero": {
                "data": {
                    "name": "Miya",
                    "head": "https://cdn.test/h.png",
                    "painting": "https://cdn.test/p.png",
                    "smallmap": "https://cdn.test/map.png",
                    "squarehead": "https://cdn.test/sq.jpg",
                    "squareheadbig": "https://cdn.test/sqb.jpg",
                    "roadsorticon1": "https://cdn.test/road.svg",
                    "sorticon1": "https://cdn.test/sort.png",
                    "heroskilllist": [
                        {
                            "skilllist": [
                                {
                                    "skillid": 140,
                                    "skillname": "Moon Blessing",
                                    "skillicon": "https://cdn.test/skill1.png",
                                }
                            ]
                        }
                    ],
                }
            },
        }
    }

    assets = extract_hero_images(1, "Miya", stored([record]))
    paths = {a.relative_path for a in assets}

    assert "heroes/Miya/images/head.jpg" in paths
    assert "heroes/Miya/images/painting.png" in paths
    assert "heroes/Miya/images/skills/140-Moon_Blessing.png" in paths
    assert "heroes/Miya/images/roadsorticon1.svg" in paths
    assert len(assets) == len(paths), "no duplicate paths/keys expected"


def test_extract_catalog_and_index_images() -> None:
    catalog = {
        "hero_id": 133,
        "data": {
            "head": "https://cdn.test/c-h.jpg",
            "head_big": "https://cdn.test/c-hb.jpg",
            "painting": "https://cdn.test/c-p.webp",
            "hero": {"data": {"name": "Hirara"}},
        },
    }
    index = {
        "hero_id": 133,
        "data": {
            "hero": {
                "data": {
                    "name": "Hirara",
                    "head": "https://cdn.test/i-h.png",
                    "smallmap": "https://cdn.test/i-m.png",
                }
            }
        },
    }

    cat = extract_catalog_images(catalog)
    idx = extract_index_images(index)

    assert {a.relative_path for a in cat} == {
        "academy/catalog/Hirara/images/head.jpg",
        "academy/catalog/Hirara/images/head_big.jpg",
        "academy/catalog/Hirara/images/painting.webp",
    }
    assert {a.relative_path for a in idx} == {
        "heroes/Hirara/images/head.png",
        "heroes/Hirara/images/smallmap.png",
    }


def test_dedupes_same_canonical_url() -> None:
    record = {
        "data": {
            "head": "https://wsrv.nl/?url=https%3A%2F%2Fcdn.test%2Fsame.png",
            "head_big": "https://cdn.test/same.png",
            "hero": {"data": {"name": "Miya"}},
        }
    }

    assets = extract_hero_images(1, "Miya", stored([record]))

    canonicals = [a.canonical_url for a in assets]
    assert canonicals.count("https://cdn.test/same.png") == 1
