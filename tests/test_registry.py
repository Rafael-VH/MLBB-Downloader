from __future__ import annotations

from mlbb_downloader.domain.registry import (
    ACADEMY_ENDPOINTS,
    ADDON_ENDPOINTS,
    DESCRIPTORS,
    HEROES_ENDPOINTS,
)


def test_registry_ids_are_unique() -> None:
    specs = [*HEROES_ENDPOINTS, *ACADEMY_ENDPOINTS, *ADDON_ENDPOINTS]
    ids = [s.id for s in specs]
    assert len(ids) == len(set(ids))


def test_descriptors_cover_all_specs() -> None:
    specs = [*HEROES_ENDPOINTS, *ACADEMY_ENDPOINTS, *ADDON_ENDPOINTS]
    assert set(DESCRIPTORS.keys()) == {s.id for s in specs}
    for spec in specs:
        assert DESCRIPTORS[spec.id] is spec


def test_paths_are_normalized() -> None:
    for spec in DESCRIPTORS.values():
        assert spec.path.startswith("/")
        assert " " not in spec.path
