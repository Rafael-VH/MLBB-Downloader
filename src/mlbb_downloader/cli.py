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
from mlbb_downloader.adapters.progress import ProgressTracker, progress_path
from mlbb_downloader.config import Settings, default_output_dir
from mlbb_downloader.errors import ApiError
from mlbb_downloader.reporting import write_report
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
ReportOption = Annotated[
    Path | None, typer.Option("--report", help="Write run report to .json or .md file.")
]


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
    report: ReportOption = None,
) -> None:
    """Download hero data, skipping anything already stored."""
    settings, client, store = _build(output, base_url, delay)
    tracker = ProgressTracker(progress_path(settings.output_dir), "heroes-sync")
    tracker.save()
    try:
        with client:
            rep = sync_heroes(
                client, store, hero_id=hero_id, limit=limit, force=force, progress=tracker
            )
            img_report = (
                sync_images(client, store, force=force, progress=tracker) if images else None
            )
    except Exception as exc:
        tracker.fail(str(exc))
        raise

    reports: dict[str, Any] = {"heroes": rep}
    if img_report is not None:
        reports["images"] = img_report
    if report:
        write_report(report, "heroes-sync", reports)
        typer.echo(f"report: {report}")
    tracker.finish(counters={"downloaded": rep.downloaded, "failed": len(rep.failed)})

    typer.echo(
        f"downloaded={rep.downloaded} skipped={rep.skipped} "
        f"failed={len(rep.failed)} elapsed={rep.elapsed:.1f}s"
    )
    if img_report is not None:
        typer.echo(
            f"images: downloaded={img_report.downloaded} skipped={img_report.skipped} "
            f"failed={len(img_report.failed)} elapsed={img_report.elapsed:.1f}s"
        )
    for failure in rep.failed[:10]:
        typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)
    if img_report is not None:
        for failure in img_report.failed[:10]:
            typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)

    if rep.failed or (img_report and img_report.failed):
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
    report: ReportOption = None,
) -> None:
    """Compare the remote data with the local manifest without writing anything."""
    settings, client, store = _build(output, base_url, delay)
    tracker = ProgressTracker(progress_path(settings.output_dir), "heroes-check")
    tracker.save()
    try:
        with client:
            rep = check_heroes(client, store, hero_id=hero_id, progress=tracker)
    except Exception as exc:
        tracker.fail(str(exc))
        raise

    if report:
        write_report(report, "heroes-check", {"heroes": rep})
        typer.echo(f"report: {report}")
    tracker.finish(counters={"unchanged": rep.unchanged, "failed": len(rep.failed)})

    typer.echo(
        f"unchanged={rep.unchanged} changed={len(rep.changed)} "
        f"new={len(rep.new)} missing={len(rep.missing)} "
        f"corrupted={len(rep.corrupted)} not_downloaded={rep.not_downloaded} "
        f"failed={len(rep.failed)} elapsed={rep.elapsed:.1f}s"
    )
    groups = (
        ("CHANGED", rep.changed),
        ("NEW", rep.new),
        ("MISSING", rep.missing),
        ("CORRUPTED", rep.corrupted),
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
    report: ReportOption = None,
) -> None:
    """Download academy game data, skipping anything already stored."""
    settings, client, store = _build(output, base_url, delay)
    tracker = ProgressTracker(progress_path(settings.output_dir), "academy-sync")
    tracker.save()
    try:
        with client:
            rep = sync_academy(client, store, limit=limit, force=force, progress=tracker)
            img_report = (
                sync_images(client, store, force=force, progress=tracker) if images else None
            )
    except Exception as exc:
        tracker.fail(str(exc))
        raise

    reports: dict[str, Any] = {"academy": rep}
    if img_report is not None:
        reports["images"] = img_report
    if report:
        write_report(report, "academy-sync", reports)
        typer.echo(f"report: {report}")
    tracker.finish(counters={"downloaded": rep.downloaded, "failed": len(rep.failed)})

    typer.echo(
        f"downloaded={rep.downloaded} skipped={rep.skipped} "
        f"failed={len(rep.failed)} unavailable={len(rep.unavailable)} "
        f"elapsed={rep.elapsed:.1f}s"
    )
    if img_report is not None:
        typer.echo(
            f"images: downloaded={img_report.downloaded} skipped={img_report.skipped} "
            f"failed={len(img_report.failed)} elapsed={img_report.elapsed:.1f}s"
        )
    for failure in rep.failed[:10]:
        typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)
    for failure in rep.unavailable[:5]:
        typer.echo(f"  UNAVAILABLE {failure.endpoint}: {failure.error}", err=True)
    if img_report is not None:
        for failure in img_report.failed[:10]:
            typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)

    if rep.failed or (img_report and img_report.failed):
        raise typer.Exit(code=1)


@academy_app.command("check")
@_guard
def academy_check(
    output: OutputOption = None,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
    report: ReportOption = None,
) -> None:
    """Compare remote academy data with the local manifest without writing anything."""
    settings, client, store = _build(output, base_url, delay)
    tracker = ProgressTracker(progress_path(settings.output_dir), "academy-check")
    tracker.save()
    try:
        with client:
            rep = check_academy(client, store, progress=tracker)
    except Exception as exc:
        tracker.fail(str(exc))
        raise

    if report:
        write_report(report, "academy-check", {"academy": rep})
        typer.echo(f"report: {report}")
    tracker.finish(counters={"unchanged": rep.unchanged, "failed": len(rep.failed)})

    typer.echo(
        f"unchanged={rep.unchanged} changed={len(rep.changed)} "
        f"new={len(rep.new)} missing={len(rep.missing)} "
        f"corrupted={len(rep.corrupted)} not_downloaded={rep.not_downloaded} "
        f"failed={len(rep.failed)} elapsed={rep.elapsed:.1f}s"
    )
    groups = (
        ("CHANGED", rep.changed),
        ("NEW", rep.new),
        ("MISSING", rep.missing),
        ("CORRUPTED", rep.corrupted),
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
    report: ReportOption = None,
) -> None:
    """Download image assets discovered in locally stored JSON artifacts."""
    settings, client, store = _build(output, base_url, delay)
    tracker = ProgressTracker(progress_path(settings.output_dir), "images-sync")
    tracker.save()
    try:
        with client:
            rep = sync_images(client, store, force=force, progress=tracker)
    except Exception as exc:
        tracker.fail(str(exc))
        raise

    if report:
        write_report(report, "images-sync", {"images": rep})
        typer.echo(f"report: {report}")
    tracker.finish(counters={"downloaded": rep.downloaded, "failed": len(rep.failed)})

    typer.echo(
        f"downloaded={rep.downloaded} skipped={rep.skipped} "
        f"failed={len(rep.failed)} elapsed={rep.elapsed:.1f}s"
    )
    for failure in rep.failed[:10]:
        typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)
    if rep.failed:
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
    report: ReportOption = None,
) -> None:
    """Check local image presence and optionally compare remote hashes."""
    settings, client, store = _build(output, base_url, delay)
    tracker = ProgressTracker(progress_path(settings.output_dir), "images-check")
    tracker.save()
    try:
        with client:
            rep = check_images(client, store, local_only=local_only, progress=tracker)
    except Exception as exc:
        tracker.fail(str(exc))
        raise

    if report:
        write_report(report, "images-check", {"images": rep})
        typer.echo(f"report: {report}")
    tracker.finish(counters={"unchanged": rep.unchanged, "failed": len(rep.failed)})

    typer.echo(
        f"unchanged={rep.unchanged} changed={len(rep.changed)} "
        f"new={len(rep.new)} missing={len(rep.missing)} "
        f"corrupted={len(rep.corrupted)} failed={len(rep.failed)} "
        f"elapsed={rep.elapsed:.1f}s"
    )
    groups = (
        ("CHANGED", rep.changed),
        ("NEW", rep.new),
        ("MISSING", rep.missing),
        ("CORRUPTED", rep.corrupted),
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
    report: ReportOption = None,
) -> None:
    """Download all public data: heroes, academy, and image assets."""
    settings, client, store = _build(output, base_url, delay)
    tracker = ProgressTracker(progress_path(settings.output_dir), "sync")
    tracker.save()
    try:
        with client:
            heroes = sync_heroes(client, store, force=force, progress=tracker)
            academy = sync_academy(client, store, force=force, progress=tracker)
            img = sync_images(client, store, force=force, progress=tracker) if images else None
    except Exception as exc:
        tracker.fail(str(exc))
        raise

    reports: dict[str, Any] = {"heroes": heroes, "academy": academy}
    if img is not None:
        reports["images"] = img
    if report:
        write_report(report, "sync", reports)
        typer.echo(f"report:   {report}")

    tracker.finish(
        counters={
            "heroes_downloaded": heroes.downloaded,
            "academy_downloaded": academy.downloaded,
            "images_downloaded": img.downloaded if img else 0,
        }
    )

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
    for label, rep in (("heroes", heroes), ("academy", academy)):
        for failure in rep.failed[:10]:
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
    report: ReportOption = None,
) -> None:
    """Check all public data against local artifacts without writing anything."""
    settings, client, store = _build(output, base_url, delay)
    tracker = ProgressTracker(progress_path(settings.output_dir), "check")
    tracker.save()
    try:
        with client:
            heroes = check_heroes(client, store, progress=tracker)
            academy = check_academy(client, store, progress=tracker)
            img = (
                check_images(client, store, local_only=local_only, progress=tracker)
                if images
                else None
            )
    except Exception as exc:
        tracker.fail(str(exc))
        raise

    reports: dict[str, Any] = {"heroes": heroes, "academy": academy}
    if img is not None:
        reports["images"] = img
    if report:
        write_report(report, "check", reports)
        typer.echo(f"report:   {report}")

    tracker.finish(
        counters={
            "heroes_unchanged": heroes.unchanged,
            "academy_unchanged": academy.unchanged,
            "images_unchanged": img.unchanged if img else 0,
        }
    )

    def line(label: str, rep: Any) -> str:
        base = (
            f"{label:<8} unchanged={rep.unchanged} changed={len(rep.changed)} "
            f"new={len(rep.new)} missing={len(rep.missing)} "
            f"corrupted={len(rep.corrupted)}"
        )
        nd = getattr(rep, "not_downloaded", None)
        if nd is not None:
            base += f" not_downloaded={nd}"
        base += f" failed={len(rep.failed)} elapsed={rep.elapsed:.1f}s"
        return base

    typer.echo(line("heroes:", heroes))
    typer.echo(line("academy:", academy))
    if img is not None:
        typer.echo(line("images:", img))
    for label, rep in (("heroes", heroes), ("academy", academy), ("images", img)):
        if rep is None:
            continue
        for name, items in (
            ("CHANGED", rep.changed),
            ("NEW", rep.new),
            ("MISSING", rep.missing),
            ("CORRUPTED", rep.corrupted),
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
