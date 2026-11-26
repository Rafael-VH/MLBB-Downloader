"""Hand-written endpoint descriptors.

These are the contract the future OpenAPI generator has to reproduce. They are
validated against three real shapes observed on the live API:

1. Collection with envelope and pagination  -> GET /heroes
2. Fixed single resource                    -> GET /academy/meta/version (total == 1)
3. Path-parameterized per-entity resource   -> GET /heroes/{hero_id}/stats

Deliberately absent: response payload models. The API returns raw records whose
shape differs between the list and the detail of the same entity, so modeling
payloads would be a maintenance liability. Only the envelope is described.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Shape = Literal["paged", "raw"]
IdKind = Literal["numeric", "slug"]


@dataclass(frozen=True, slots=True)
class EndpointSpec:
    id: str
    path: str
    shape: Shape = "paged"
    method: str = "GET"
    params: tuple[str, ...] = ()
    enumerated_by: str | None = None
    id_kind: IdKind | None = None
    total_expected: int | None = None

    @property
    def paginated(self) -> bool:
        return self.shape == "paged"


HEROES_INDEX = EndpointSpec(
    id="heroes.index",
    path="/heroes",
    params=("size", "index", "lang"),
)

ACADEMY_VERSION = EndpointSpec(
    id="academy.version",
    path="/academy/meta/version",
    params=("size", "index", "lang"),
    total_expected=1,
)

HERO_STATS = EndpointSpec(
    id="heroes.stats",
    path="/heroes/{hero_id}/stats",
    params=("hero_identifier", "rank", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

DESCRIPTORS: dict[str, EndpointSpec] = {
    spec.id: spec for spec in (HEROES_INDEX, ACADEMY_VERSION, HERO_STATS)
}
