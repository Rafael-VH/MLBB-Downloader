"""Command line interface."""

from __future__ import annotations

import functools
import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from mlbb_downloader.adapters.arena import ArenaClient
from mlbb_downloader.adapters.fsstore import DataStore
from mlbb_downloader.config import Settings, default_output_dir
from mlbb_downloader.errors import ApiError
from mlbb_downloader.usecases.academy import check_academy, sync_academy
from mlbb_downloader.usecases.addon import ip_location, win_rate_calculator
from mlbb_downloader.usecases.heroes import check_heroes, sync_heroes
from mlbb_downloader.usecases.images import check_images, sync_images

app = typer.Typer(help="Download Mobile Legends: Bang Bang data from the Rone Arena API.")
heroes_app = typer.Typer(help="Hero data: list, detail, stats, relations and wallpapers.")
academy_app = typer.Typer(
    help="Academy game data: items, spells, emblems, ranks and hero win rates."
)
addon_app = typer.Typer(help="One-shot utilities. Never part of a bulk download.")
images_app = typer.Typer(help="Image assets extracted from already-downloaded JSON artifacts.")
app.add_typer(heroes_app, name="heroes")
app.add_typer(academy_app, name="academy")
app.add_typer(addon_app, name="addon")
app.add_typer(images_app, name="images")

OutputOption = Annotated[Path | None, typer.Option("--output", "-o", help="Output directory.")]
BaseUrlOption = Annotated[str | None, typer.Option("--base-url", help="Override the API base URL.")]
DelayOption = Annotated[float | None, typer.Option("--delay", help="Seconds between requests.")]


def _guard(func: Callable[..., Any]) -> Callable[..., Any]:
    """Report API failures as one clean line instead of a traceback."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ApiError as exc:
            typer.secho(f"error: {exc.message}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1) from None
        except ValueError as exc:
            typer.secho(f"error: {exc}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1) from None

    return wrapper


def _build(
    output: Path | None,
    base_url: str | None,
    delay: float | None,
) -> tuple[Settings, ArenaClient, DataStore]:
    settings = Settings()
    if base_url:
        settings.base_url = base_url
    if delay is not None:
        settings.delay = delay
    settings.output_dir = Path(output) if output else default_output_dir()

    client = ArenaClient(
        settings.base_url,
        delay=settings.delay,
        timeout=settings.timeout,
        retries=settings.retries,
        page_size=settings.page_size,
    )
    store = DataStore(settings.output_dir, base_url=settings.base_url)
    return settings, client, store


@heroes_app.command("sync")
@_guard
def heroes_sync(
    output: OutputOption = None,
    hero_id: Annotated[
        int | None, typer.Option("--hero-id", help="Sync only this hero ID.")
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", help="Only sync the first N heroes.")
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Re-download everything.")] = False,
    images: Annotated[bool, typer.Option("--images", help="Also download image assets.")] = False,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Download hero data, skipping anything already stored."""
    _, client, store = _build(output, base_url, delay)
    with client:
        report = sync_heroes(client, store, hero_id=hero_id, limit=limit, force=force)
        img_report = sync_images(client, store, force=force) if images else None

    typer.echo(
        f"downloaded={report.downloaded} skipped={report.skipped} "
        f"failed={len(report.failed)} elapsed={report.elapsed:.1f}s"
    )
    if img_report is not None:
        typer.echo(
            f"images: downloaded={img_report.downloaded} skipped={img_report.skipped} "
            f"failed={len(img_report.failed)} elapsed={img_report.elapsed:.1f}s"
        )
    for failure in report.failed[:10]:
        typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)
    if img_report is not None:
        for failure in img_report.failed[:10]:
            typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)

    if report.failed or (img_report and img_report.failed):
        raise typer.Exit(code=1)


@heroes_app.command("check")
@_guard
def heroes_check(
    output: OutputOption = None,
    hero_id: Annotated[
        int | None, typer.Option("--hero-id", help="Check only this hero ID.")
    ] = None,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Compare the remote data with the local manifest without writing anything."""
    _, client, store = _build(output, base_url, delay)
    with client:
        report = check_heroes(client, store, hero_id=hero_id)

    typer.echo(
        f"unchanged={report.unchanged} changed={len(report.changed)} "
        f"new={len(report.new)} missing={len(report.missing)} "
        f"corrupted={len(report.corrupted)} not_downloaded={report.not_downloaded} "
        f"failed={len(report.failed)} elapsed={report.elapsed:.1f}s"
    )
    groups = (
        ("CHANGED", report.changed),
        ("NEW", report.new),
        ("MISSING", report.missing),
        ("CORRUPTED", report.corrupted),
    )
    for label, items in groups:
        for item in items[:10]:
            typer.echo(f"  {label} {item}")


@academy_app.command("sync")
@_guard
def academy_sync(
    output: OutputOption = None,
    limit: Annotated[
        int | None, typer.Option("--limit", help="Only sync the first N heroes.")
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Re-download everything.")] = False,
    images: Annotated[bool, typer.Option("--images", help="Also download image assets.")] = False,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Download academy game data, skipping anything already stored."""
    _, client, store = _build(output, base_url, delay)
    with client:
        report = sync_academy(client, store, limit=limit, force=force)
        img_report = sync_images(client, store, force=force) if images else None

    typer.echo(
        f"downloaded={report.downloaded} skipped={report.skipped} "
        f"failed={len(report.failed)} unavailable={len(report.unavailable)} "
        f"elapsed={report.elapsed:.1f}s"
    )
    if img_report is not None:
        typer.echo(
            f"images: downloaded={img_report.downloaded} skipped={img_report.skipped} "
            f"failed={len(img_report.failed)} elapsed={img_report.elapsed:.1f}s"
        )
    for failure in report.failed[:10]:
        typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)
    for failure in report.unavailable[:5]:
        typer.echo(f"  UNAVAILABLE {failure.endpoint}: {failure.error}", err=True)
    if img_report is not None:
        for failure in img_report.failed[:10]:
            typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)

    if report.failed or (img_report and img_report.failed):
        raise typer.Exit(code=1)


@academy_app.command("check")
@_guard
def academy_check(
    output: OutputOption = None,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Compare remote academy data with the local manifest without writing anything."""
    _, client, store = _build(output, base_url, delay)
    with client:
        report = check_academy(client, store)

    typer.echo(
        f"unchanged={report.unchanged} changed={len(report.changed)} "
        f"new={len(report.new)} missing={len(report.missing)} "
        f"corrupted={len(report.corrupted)} not_downloaded={report.not_downloaded} "
        f"failed={len(report.failed)} elapsed={report.elapsed:.1f}s"
    )
    groups = (
        ("CHANGED", report.changed),
        ("NEW", report.new),
        ("MISSING", report.missing),
        ("CORRUPTED", report.corrupted),
    )
    for label, items in groups:
        for item in items[:10]:
            typer.echo(f"  {label} {item}")


@addon_app.command("win-rate")
@_guard
def addon_win_rate(
    match_now: Annotated[int, typer.Option("--match-now", help="Matches played so far.")],
    wr_now: Annotated[float, typer.Option("--wr-now", help="Current win rate in percent.")],
    wr_future: Annotated[float, typer.Option("--wr-future", help="Target win rate in percent.")],
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Consecutive wins needed to reach a target win rate."""
    _, client, _ = _build(None, base_url, delay)
    with client:
        payload = win_rate_calculator(
            client,
            matches_now=match_now,
            win_rate_now=wr_now,
            win_rate_future=wr_future,
        )

    typer.echo(f"required_no_lose_matches={payload.get('required_no_lose_matches')}")
    if payload.get("message"):
        typer.echo(str(payload["message"]))


@addon_app.command("ip")
@_guard
def addon_ip(base_url: BaseUrlOption = None, delay: DelayOption = None) -> None:
    """Show the location the API resolves for the caller's IP."""
    _, client, _ = _build(None, base_url, delay)
    with client:
        payload = ip_location(client)

    data = payload.get("data") or {}
    typer.echo(
        f"city={data.get('city')} state={data.get('state')} "
        f"country={data.get('country')} lang={data.get('lang')}"
    )


@images_app.command("sync")
@_guard
def images_sync(
    output: OutputOption = None,
    force: Annotated[bool, typer.Option("--force", help="Re-download all images.")] = False,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Download image assets discovered in locally stored JSON artifacts."""
    _, client, store = _build(output, base_url, delay)
    with client:
        report = sync_images(client, store, force=force)

    typer.echo(
        f"downloaded={report.downloaded} skipped={report.skipped} "
        f"failed={len(report.failed)} elapsed={report.elapsed:.1f}s"
    )
    for failure in report.failed[:10]:
        typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)
    if report.failed:
        raise typer.Exit(code=1)


@images_app.command("check")
@_guard
def images_check(
    output: OutputOption = None,
    local_only: Annotated[
        bool, typer.Option("--local-only", help="Only rehash local files; skip remote downloads.")
    ] = False,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Check local image presence and optionally compare remote hashes."""
    _, client, store = _build(output, base_url, delay)
    with client:
        report = check_images(client, store, local_only=local_only)

    typer.echo(
        f"unchanged={report.unchanged} changed={len(report.changed)} "
        f"new={len(report.new)} missing={len(report.missing)} "
        f"corrupted={len(report.corrupted)} failed={len(report.failed)} "
        f"elapsed={report.elapsed:.1f}s"
    )
    groups = (
        ("CHANGED", report.changed),
        ("NEW", report.new),
        ("MISSING", report.missing),
        ("CORRUPTED", report.corrupted),
    )
    for label, items in groups:
        for item in items[:10]:
            typer.echo(f"  {label} {item}")


@app.command("sync")
@_guard
def sync(
    output: OutputOption = None,
    force: Annotated[bool, typer.Option("--force", help="Re-download everything.")] = False,
    images: Annotated[
        bool, typer.Option("--images/--no-images", help="Include image assets.")
    ] = True,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Download all public data: heroes, academy, and image assets."""
    _, client, store = _build(output, base_url, delay)
    with client:
        heroes = sync_heroes(client, store, force=force)
        academy = sync_academy(client, store, force=force)
        img = sync_images(client, store, force=force) if images else None

    typer.echo(
        f"heroes:   downloaded={heroes.downloaded} skipped={heroes.skipped} "
        f"failed={len(heroes.failed)} elapsed={heroes.elapsed:.1f}s"
    )
    typer.echo(
        f"academy:  downloaded={academy.downloaded} skipped={academy.skipped} "
        f"failed={len(academy.failed)} unavailable={len(academy.unavailable)} "
        f"elapsed={academy.elapsed:.1f}s"
    )
    if img is not None:
        typer.echo(
            f"images:   downloaded={img.downloaded} skipped={img.skipped} "
            f"failed={len(img.failed)} elapsed={img.elapsed:.1f}s"
        )
    for label, report in (("heroes", heroes), ("academy", academy)):
        for failure in report.failed[:10]:
            typer.echo(f"  FAILED [{label}] {failure.endpoint}: {failure.error}", err=True)
    for failure in academy.unavailable[:5]:
        typer.echo(f"  UNAVAILABLE [academy] {failure.endpoint}: {failure.error}", err=True)
    if img is not None:
        for failure in img.failed[:10]:
            typer.echo(f"  FAILED [images] {failure.endpoint}: {failure.error}", err=True)

    if heroes.failed or academy.failed or (img and img.failed):
        raise typer.Exit(code=1)


@app.command("check")
@_guard
def check(
    output: OutputOption = None,
    images: Annotated[
        bool, typer.Option("--images/--no-images", help="Include image assets.")
    ] = True,
    local_only: Annotated[
        bool,
        typer.Option("--local-only", help="For images, only rehash local files; skip remote."),
    ] = False,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Check all public data against local artifacts without writing anything."""
    _, client, store = _build(output, base_url, delay)
    with client:
        heroes = check_heroes(client, store)
        academy = check_academy(client, store)
        img = check_images(client, store, local_only=local_only) if images else None

    def line(label: str, report: Any) -> str:
        base = (
            f"{label:<8} unchanged={report.unchanged} changed={len(report.changed)} "
            f"new={len(report.new)} missing={len(report.missing)} "
            f"corrupted={len(report.corrupted)}"
        )
        nd = getattr(report, "not_downloaded", None)
        if nd is not None:
            base += f" not_downloaded={nd}"
        base += f" failed={len(report.failed)} elapsed={report.elapsed:.1f}s"
        return base

    typer.echo(line("heroes:", heroes))
    typer.echo(line("academy:", academy))
    if img is not None:
        typer.echo(line("images:", img))
    for label, report in (("heroes", heroes), ("academy", academy), ("images", img)):
        if report is None:
            continue
        for name, items in (
            ("CHANGED", report.changed),
            ("NEW", report.new),
            ("MISSING", report.missing),
            ("CORRUPTED", report.corrupted),
        ):
            for item in items[:10]:
                typer.echo(f"  {name} [{label}] {item}")


@app.command()
@_guard
def status(
    output: OutputOption = None,
    verify: Annotated[
        bool, typer.Option("--verify", help="Rehash local files to detect corruption.")
    ] = False,
) -> None:
    """Show what is already stored locally."""
    directory = Path(output) if output else default_output_dir()
    store = DataStore(directory)

    stored = 0
    missing = 0
    corrupted = 0
    for _key, item in store.manifest.items.items():
        target = store.root / item.path
        if not target.exists():
            missing += 1
            continue
        stored += 1
        if verify:
            disk_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            if disk_hash != item.sha256:
                corrupted += 1

    size = sum(item.size for item in store.manifest.items.values())

    typer.echo(f"output:    {directory}")
    typer.echo(f"items:     {len(store.manifest.items)}")
    typer.echo(f"on disk:   {stored}")
    typer.echo(f"missing:   {missing}")
    if verify:
        typer.echo(f"corrupted: {corrupted}")
    typer.echo(f"bytes:     {size}")
    typer.echo(f"last run:  {store.manifest.generated_at.isoformat()}")


if __name__ == "__main__":
    app()
