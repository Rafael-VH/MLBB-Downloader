"""Manifest models describing every downloaded artifact.

Pure data: no filesystem access lives here. Persistence is an adapter concern.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ManifestItem(BaseModel):
    endpoint: str
    params: dict[str, Any] = Field(default_factory=dict)
    path: str
    sha256: str
    size: int
    downloaded_at: datetime
    total: int | None = None


class Manifest(BaseModel):
    schema_version: int = 1
    base_url: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: dict[str, ManifestItem] = Field(default_factory=dict)
