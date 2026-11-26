"""Hand-written endpoint descriptors (pure catalogue).

These are the contract the future OpenAPI generator has to reproduce. They are
validated against real shapes observed on the live API:

1. Collection with envelope and pagination  -> GET /heroes
2. Fixed single resource                    -> GET /academy/meta/version (total == 1)
3. Path-parameterized per-entity resource   -> GET /heroes/{hero_id}/stats

Deliberately absent: response payload models. The API returns raw records whose
shape differs between the list and the detail of the same entity, so modeling
payloads would be a maintenance liability. Only the envelope is described.

``kind`` records the download policy, not just the shape:

- ``collection``: paged top-level resource, stored whole.
- ``per_entity``: requires an entity identifier; enumerated from a parent.
- ``discontinued``: the upstream answers HTTP 200 with an error code; never fatal.
- ``redundant``: fully contained in another artifact; catalogued, not enumerated.
- ``ugc``: user-generated content; catalogued, excluded from bulk sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Shape = Literal["paged", "raw"]
IdKind = Literal["numeric", "slug"]
Kind = Literal["collection", "per_entity", "discontinued", "redundant", "ugc"]
Category = Literal["heroes", "academy"]


@dataclass(frozen=True, slots=True)
class EndpointSpec:
    id: str
    path: str
    category: Category = "heroes"
    kind: Kind = "collection"
    shape: Shape = "paged"
    method: str = "GET"
    params: tuple[str, ...] = ()
    enumerated_by: str | None = None
    id_kind: IdKind | None = None
    total_expected: int | None = None
    note: str = ""

    @property
    def paginated(self) -> bool:
        return self.shape == "paged"


# -- heroes -------------------------------------------------------------------

HEROES_INDEX = EndpointSpec(
    id="heroes.index",
    path="/heroes",
    params=("size", "index", "lang"),
)

HEROES_RANK = EndpointSpec(
    id="heroes.rank",
    path="/heroes/rank",
    params=("size", "index", "lang", "days", "rank", "sort_field", "sort_order"),
    note="ranked hero list; upstream can be transiently unavailable",
)

HEROES_POSITIONS = EndpointSpec(
    id="heroes.positions",
    path="/heroes/positions",
    params=("size", "index", "lang", "role", "lane"),
    note="hero position/filter list",
)

HEROES_WALLPAPERS = EndpointSpec(
    id="heroes.wallpapers",
    path="/heroes/wallpapers",
    params=("size", "index", "lang"),
    note="global wallpapers gallery",
)

HERO_DETAIL = EndpointSpec(
    id="heroes.detail",
    path="/heroes/{hero_id}",
    kind="per_entity",
    params=("hero_id", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

HERO_STATS = EndpointSpec(
    id="heroes.stats",
    path="/heroes/{hero_id}/stats",
    kind="per_entity",
    params=("hero_identifier", "rank", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

HERO_SKILL_COMBOS = EndpointSpec(
    id="heroes.skill-combos",
    path="/heroes/{hero_id}/skill-combos",
    kind="per_entity",
    params=("hero_id", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

HERO_TRENDS = EndpointSpec(
    id="heroes.trends",
    path="/heroes/{hero_id}/trends",
    kind="per_entity",
    params=("hero_id", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

HERO_RELATIONS = EndpointSpec(
    id="heroes.relations",
    path="/heroes/{hero_id}/relations",
    kind="per_entity",
    params=("hero_id", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

HERO_COUNTERS = EndpointSpec(
    id="heroes.counters",
    path="/heroes/{hero_id}/counters",
    kind="per_entity",
    params=("hero_id", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

HERO_COMPATIBILITY = EndpointSpec(
    id="heroes.compatibility",
    path="/heroes/{hero_id}/compatibility",
    kind="per_entity",
    params=("hero_id", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

HERO_WALLPAPERS = EndpointSpec(
    id="heroes.wallpapers",
    path="/heroes/{hero_id}/wallpapers",
    kind="per_entity",
    params=("hero_id", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

# -- academy: collections ------------------------------------------------------

ACADEMY_VERSION = EndpointSpec(
    id="academy.version",
    path="/academy/meta/version",
    category="academy",
    total_expected=1,
)

ACADEMY_CATALOG = EndpointSpec(
    id="academy.catalog",
    path="/academy/heroes/catalog",
    category="academy",
    note="133 records; provides hero id, name, head and painting",
)

ACADEMY_ROLES = EndpointSpec(
    id="academy.roles",
    path="/academy/roles",
    category="academy",
    note="7 records",
)

ACADEMY_EQUIPMENT = EndpointSpec(
    id="academy.equipment",
    path="/academy/equipment",
    category="academy",
    note="184 records",
)

ACADEMY_EQUIPMENT_EXPANDED = EndpointSpec(
    id="academy.equipment-expanded",
    path="/academy/equipment/expanded",
    category="academy",
    note="152 records; includes full skill text",
)

ACADEMY_SPELLS = EndpointSpec(
    id="academy.spells",
    path="/academy/spells",
    category="academy",
    note="12 records",
)

ACADEMY_EMBLEMS = EndpointSpec(
    id="academy.emblems",
    path="/academy/emblems",
    category="academy",
    note="26 records",
)

ACADEMY_RANKS = EndpointSpec(
    id="academy.ranks",
    path="/academy/ranks",
    category="academy",
    note="29 records; each covers a rankid_start..rankid_end range",
)

ACADEMY_HERO_FILTER = EndpointSpec(
    id="academy.heroes",
    path="/academy/heroes",
    category="academy",
    params=("role", "lane", "order", "size", "index", "lang"),
    note="unfiltered (133) is stored once; filters are query-time",
)

ACADEMY_RECOMMENDED = EndpointSpec(
    id="academy.recommended",
    path="/academy/recommended",
    category="academy",
    kind="ugc",
    params=("order", "size", "index", "lang"),
    note="total 10000 user-generated records; detail payload is byte-identical "
    "to the list record, so it is catalogued but not bulk-synced",
)

# -- academy: per entity -------------------------------------------------------

ACADEMY_RANK_DETAIL = EndpointSpec(
    id="academy.rank-detail",
    path="/academy/ranks/{rank_id}",
    category="academy",
    kind="redundant",
    params=("rank_id", "lang"),
    enumerated_by="rank_id",
    id_kind="numeric",
    total_expected=1,
    note="rank_id is a rank number 1..9999; the detail record duplicates the "
    "covering entry of /academy/ranks",
)

ACADEMY_RECOMMENDED_DETAIL = EndpointSpec(
    id="academy.recommended-detail",
    path="/academy/recommended/{recommended_id}",
    category="academy",
    kind="ugc",
    params=("recommended_id", "size", "index", "lang"),
    enumerated_by="recommended_id",
    id_kind="numeric",
    total_expected=1,
    note="same payload as the list record",
)

ACADEMY_HERO_STATS = EndpointSpec(
    id="academy.hero-stats",
    path="/academy/heroes/{hero_identifier}/stats",
    category="academy",
    kind="per_entity",
    params=("hero_identifier", "rank", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
    note="rank filter defaults to all",
)

ACADEMY_HERO_LANE = EndpointSpec(
    id="academy.hero-lane",
    path="/academy/heroes/{hero_identifier}/lane",
    category="academy",
    kind="per_entity",
    params=("hero_identifier", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
    note="source of truth for the lanes a hero actually plays",
)

ACADEMY_HERO_WIN_RATE = EndpointSpec(
    id="academy.hero-win-rate",
    path="/academy/heroes/{hero_identifier}/win-rate/timeline",
    category="academy",
    kind="per_entity",
    params=("hero_identifier", "lane", "rank", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
    note="lane is required",
)

ACADEMY_HERO_BUILDS = EndpointSpec(
    id="academy.hero-builds",
    path="/academy/heroes/{hero_identifier}/builds",
    category="academy",
    kind="per_entity",
    params=("hero_identifier", "lane", "rank", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
    note="lane is required; one record per lane",
)

ACADEMY_HERO_COUNTERS = EndpointSpec(
    id="academy.hero-counters",
    path="/academy/heroes/{hero_identifier}/counters",
    category="academy",
    kind="per_entity",
    params=("hero_identifier", "rank", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
)

ACADEMY_HERO_TEAMMATES = EndpointSpec(
    id="academy.hero-teammates",
    path="/academy/heroes/{hero_identifier}/teammates",
    category="academy",
    kind="per_entity",
    params=("hero_identifier", "rank", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
    note="the live path is /teammates; /matchups does not exist",
)

ACADEMY_HERO_TRENDS = EndpointSpec(
    id="academy.hero-trends",
    path="/academy/heroes/{hero_identifier}/trends",
    category="academy",
    kind="per_entity",
    params=("hero_identifier", "days", "rank", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    total_expected=1,
    note="days 7/15/30 defaults to 7",
)

ACADEMY_HERO_RECOMMENDED = EndpointSpec(
    id="academy.hero-recommended",
    path="/academy/heroes/{hero_identifier}/recommended",
    category="academy",
    kind="ugc",
    params=("hero_identifier", "order", "size", "index", "lang"),
    enumerated_by="hero_id",
    id_kind="numeric",
    note="204 user-generated records for hero 1",
)

# -- academy: discontinued -----------------------------------------------------

ACADEMY_HERO_RATINGS = EndpointSpec(
    id="academy.hero-ratings",
    path="/academy/heroes/ratings",
    category="academy",
    kind="discontinued",
    params=("lang",),
    note="HTTP 200 with code 10407 and message 接口下线",
)

ACADEMY_HERO_RATINGS_SUBJECT = EndpointSpec(
    id="academy.hero-ratings-subject",
    path="/academy/heroes/ratings/{subject}",
    category="academy",
    kind="discontinued",
    params=("subject", "lang"),
    note="HTTP 422 while the ratings index is offline",
)

ACADEMY_ENDPOINTS: tuple[EndpointSpec, ...] = (
    ACADEMY_VERSION,
    ACADEMY_CATALOG,
    ACADEMY_ROLES,
    ACADEMY_EQUIPMENT,
    ACADEMY_EQUIPMENT_EXPANDED,
    ACADEMY_SPELLS,
    ACADEMY_EMBLEMS,
    ACADEMY_RANKS,
    ACADEMY_HERO_FILTER,
    ACADEMY_RECOMMENDED,
    ACADEMY_RANK_DETAIL,
    ACADEMY_RECOMMENDED_DETAIL,
    ACADEMY_HERO_STATS,
    ACADEMY_HERO_LANE,
    ACADEMY_HERO_WIN_RATE,
    ACADEMY_HERO_BUILDS,
    ACADEMY_HERO_COUNTERS,
    ACADEMY_HERO_TEAMMATES,
    ACADEMY_HERO_TRENDS,
    ACADEMY_HERO_RECOMMENDED,
    ACADEMY_HERO_RATINGS,
    ACADEMY_HERO_RATINGS_SUBJECT,
)

HEROES_ENDPOINTS: tuple[EndpointSpec, ...] = (
    HEROES_INDEX,
    HEROES_RANK,
    HEROES_POSITIONS,
    HEROES_WALLPAPERS,
    HERO_DETAIL,
    HERO_STATS,
    HERO_SKILL_COMBOS,
    HERO_TRENDS,
    HERO_RELATIONS,
    HERO_COUNTERS,
    HERO_COMPATIBILITY,
    HERO_WALLPAPERS,
)

DESCRIPTORS: dict[str, EndpointSpec] = {
    spec.id: spec for spec in (*HEROES_ENDPOINTS, *ACADEMY_ENDPOINTS)
}
