"""Generic artifact engine.

Domains describe *what* to download as :class:`Artifact` values; this module
owns the mechanics that must not be duplicated per domain: verified pagination,
manifest-driven resume, atomic persistence, hashing and comparison.

Design notes:
- ``sync`` never re-fetches an artifact whose file and manifest entry both
  exist, unless ``force`` is set.
- ``check`` is manifest-driven: it re-fetches exactly the artifacts recorded
  locally, so its cost is proportional to the local dataset.
- The manifest is flushed every ``flush_every`` artifacts. A crash therefore
  loses at most one window of manifest entries; those artifacts are fetched
  again on resume, which costs time but never correctness.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from mlbb_downloader.api.client import ArenaClient
from mlbb_downloader.api.errors import ApiError, IncompletePageError
from mlbb_downloader.domain.keying import item_key
from mlbb_downloader.storage.store import DataStore, serialize_json

DEFAULT_FLUSH_EVERY = 25


def artifact_payload(
    endpoint: str,
    records: list[dict[str, Any]],
    total: int | None,
) -> dict[str, Any]:
    return {"endpoint": endpoint, "total": total, "records": records}


@dataclass(frozen=True, slots=True)
class Artifact:
    """One logical artifact: where it comes from and where it is stored."""

    endpoint: str
    relative_path: str
    params: dict[str, Any] = field(default_factory=dict)
    optional: bool = False

    @property
    def key(self) -> str:
        return item_key(self.endpoint, self.params)


@dataclass(slots=True)
class Failure:
    key: str
    endpoint: str
    error: str


@dataclass(slots=True)
class SyncReport:
    downloaded: int = 0
    skipped: int = 0
    failed: list[Failure] = field(default_factory=list)
    unavailable: list[Failure] = field(default_factory=list)
    elapsed: float = 0.0


@dataclass(slots=True)
class CheckReport:
    unchanged: int = 0
    changed: list[str] = field(default_factory=list)
    new: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    not_downloaded: int = 0
    failed: list[Failure] = field(default_factory=list)
    unavailable: list[Failure] = field(default_factory=list)
    elapsed: float = 0.0


def load_records(store: DataStore, key: str) -> list[dict[str, Any]]:
    """Return the records of a stored artifact, or an empty list."""
    payload = store.load_json(key)
    records = payload.get("records") if isinstance(payload, dict) else None
    return records if isinstance(records, list) else []


def _record_failure(
    report: SyncReport | CheckReport,
    artifact: Artifact,
    exc: Exception,
) -> None:
    failure = Failure(key=artifact.key, endpoint=artifact.endpoint, error=str(exc))
    if artifact.optional:
        report.unavailable.append(failure)
    else:
        report.failed.append(failure)


def _fetch(
    client: ArenaClient,
    artifact: Artifact,
    page_size: int | None,
):
    return client.get_paged(artifact.endpoint, artifact.params or None, size=page_size)


def _sync(
    client: ArenaClient,
    store: DataStore,
    artifact: Artifact,
    report: SyncReport,
    *,
    force: bool,
    page_size: int | None,
) -> list[dict[str, Any]] | None:
    if not force and store.exists(artifact.key):
        report.skipped += 1
        return load_records(store, artifact.key)

    try:
        fetched = _fetch(client, artifact, page_size)
    except (ApiError, IncompletePageError) as exc:
        _record_failure(report, artifact, exc)
        return None

    store.save_json(
        artifact.key,
        artifact.relative_path,
        artifact_payload(artifact.endpoint, fetched.records, fetched.total),
        endpoint=artifact.endpoint,
        params=artifact.params,
        total=fetched.total,
    )
    report.downloaded += 1
    return fetched.records


def _check(
    client: ArenaClient,
    store: DataStore,
    artifact: Artifact,
    report: CheckReport,
    *,
    page_size: int | None,
) -> list[dict[str, Any]] | None:
    try:
        fetched = _fetch(client, artifact, page_size)
    except (ApiError, IncompletePageError) as exc:
        _record_failure(report, artifact, exc)
        return None

    payload = artifact_payload(artifact.endpoint, fetched.records, fetched.total)
    item = store.manifest.items.get(artifact.key)

    if item is None:
        report.new.append(artifact.key)
    elif not (store.root / item.path).exists():
        report.missing.append(artifact.key)
    elif hashlib.sha256(serialize_json(payload)).hexdigest() != item.sha256:
        report.changed.append(artifact.key)
    else:
        report.unchanged += 1

    return fetched.records


def sync_one(
    client: ArenaClient,
    store: DataStore,
    artifact: Artifact,
    report: SyncReport | None = None,
    *,
    force: bool = False,
    page_size: int | None = None,
) -> list[dict[str, Any]] | None:
    """Ensure one artifact is stored and return its records.

    Records come from the network on a real download and from disk on a resume,
    so callers can plan dependent work without a second read.
    """
    report = report if report is not None else SyncReport()
    started = time.monotonic()
    records = _sync(client, store, artifact, report, force=force, page_size=page_size)
    store.flush()
    report.elapsed += time.monotonic() - started
    return records


def sync_many(
    client: ArenaClient,
    store: DataStore,
    artifacts: Iterable[Artifact],
    report: SyncReport | None = None,
    *,
    force: bool = False,
    page_size: int | None = None,
    flush_every: int = DEFAULT_FLUSH_EVERY,
) -> SyncReport:
    report = report if report is not None else SyncReport()
    started = time.monotonic()
    for index, artifact in enumerate(artifacts, start=1):
        _sync(client, store, artifact, report, force=force, page_size=page_size)
        if index % flush_every == 0:
            store.flush()
    store.flush()
    report.elapsed += time.monotonic() - started
    return report


def check_one(
    client: ArenaClient,
    store: DataStore,
    artifact: Artifact,
    report: CheckReport | None = None,
    *,
    page_size: int | None = None,
) -> list[dict[str, Any]] | None:
    report = report if report is not None else CheckReport()
    started = time.monotonic()
    records = _check(client, store, artifact, report, page_size=page_size)
    report.elapsed += time.monotonic() - started
    return records


def check_many(
    client: ArenaClient,
    store: DataStore,
    artifacts: Iterable[Artifact],
    report: CheckReport | None = None,
    *,
    page_size: int | None = None,
) -> CheckReport:
    report = report if report is not None else CheckReport()
    started = time.monotonic()
    for artifact in artifacts:
        _check(client, store, artifact, report, page_size=page_size)
    report.elapsed += time.monotonic() - started
    return report


def check_manifest(
    client: ArenaClient,
    store: DataStore,
    report: CheckReport | None = None,
    *,
    prefix: str | None = None,
    skip: frozenset[str] | set[str] = frozenset(),
    page_size: int | None = None,
) -> CheckReport:
    """Re-fetch and compare exactly the artifacts recorded in the manifest."""
    report = report if report is not None else CheckReport()
    started = time.monotonic()
    for key in sorted(store.manifest.items):
        if key in skip:
            continue
        item = store.manifest.items[key]
        if prefix is not None and not item.endpoint.startswith(prefix):
            continue
        artifact = Artifact(
            endpoint=item.endpoint,
            relative_path=item.path,
            params=dict(item.params),
        )
        _check(client, store, artifact, report, page_size=page_size)
    report.elapsed += time.monotonic() - started
    return report
