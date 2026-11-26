from __future__ import annotations

from pathlib import Path

import pytest

from mlbb_downloader.adapters.paths import data_path
from mlbb_downloader.domain.layout import sanitize_component

ILLEGAL = set('<>:"/\\|?*')


def test_reserved_windows_names_are_prefixed() -> None:
    assert sanitize_component("CON") == "_CON"
    assert sanitize_component("com1") == "_com1"
    assert sanitize_component("LPT9") == "_LPT9"


def test_illegal_characters_are_replaced() -> None:
    cleaned = sanitize_component('a/b\\c:d*e?f"g<h>i|j')

    assert not (set(cleaned) & ILLEGAL)


def test_trailing_dots_and_spaces_are_stripped() -> None:
    assert sanitize_component("hero name. ") == "hero name"


def test_control_characters_are_removed() -> None:
    assert sanitize_component("mi\x00ya\x1f") == "miya"


def test_length_is_bounded() -> None:
    assert len(sanitize_component("x" * 300)) == 80


def test_empty_input_gets_a_placeholder() -> None:
    assert sanitize_component("   ") == "_"


def test_data_path_stays_inside_root(tmp_path: Path) -> None:
    resolved = data_path(tmp_path, "heroes", "miya", "detail.json")

    assert resolved == tmp_path / "heroes" / "miya" / "detail.json"


def test_data_path_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        data_path(tmp_path, "..", "escape.json")


def test_data_path_sanitizes_components(tmp_path: Path) -> None:
    resolved = data_path(tmp_path, "heroes", "a/b", "detail.json")

    assert resolved.parent.name == "a_b"
