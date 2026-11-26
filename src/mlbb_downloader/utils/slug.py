"""Filesystem-safe naming for Windows."""

from __future__ import annotations

import re

MAX_COMPONENT_LENGTH = 80

RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_ILLEGAL = re.compile(r'[<>:"/\\|?*]')


def sanitize_component(value: str, *, max_length: int = MAX_COMPONENT_LENGTH) -> str:
    """Turn arbitrary text into a single safe path component."""
    text = _CONTROL.sub("", str(value))
    text = _ILLEGAL.sub("_", text).strip()
    text = text.rstrip(". ")
    if not text:
        return "_"
    if text.upper() in RESERVED_NAMES:
        text = f"_{text}"
    return text[:max_length].rstrip(". ") or "_"
