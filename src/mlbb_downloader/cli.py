"""Command line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from mlbb_downloader.api.client import ArenaClient
from mlbb_downloader.config import Settings, default_output_dir
from mlbb_downloader.downloaders.heroes import check_heroes, sync_heroes
from mlbb_downloader.storage.store import DataStore

app = typer.Typer(help="Download Mobile Legends: Bang Bang data from the Rone Arena API.")
heroes_app = typer.Typer(help="Hero data: list, detail, stats, relations and wallpapers.")
app.add_typer(heroes_app, name="heroes")

OutputOption = Annotated[Path | None, typer.Option("--output", "-o", help="Output directory.")]
BaseUrlOption = Annotated[str | None, typer.Option("--base-url", help="Override the API base URL.")]
DelayOption = Annotated[float | None, typer.Option("--delay", help="Seconds between requests.")]


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
def heroes_sync(
    output: OutputOption = None,
    limit: Annotated[
        int | None, typer.Option("--limit", help="Only sync the first N heroes.")
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Re-download everything.")] = False,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Download hero data, skipping anything already stored."""
    _, client, store = _build(output, base_url, delay)
    with client:
        report = sync_heroes(client, store, limit=limit, force=force)

    typer.echo(
        f"downloaded={report.downloaded} skipped={report.skipped} "
        f"failed={len(report.failed)} elapsed={report.elapsed:.1f}s"
    )
    for failure in report.failed[:10]:
        typer.echo(f"  FAILED {failure.endpoint}: {failure.error}", err=True)

    if report.failed:
        raise typer.Exit(code=1)


@heroes_app.command("check")
def heroes_check(
    output: OutputOption = None,
    limit: Annotated[
        int | None, typer.Option("--limit", help="Only check the first N heroes.")
    ] = None,
    base_url: BaseUrlOption = None,
    delay: DelayOption = None,
) -> None:
    """Compare the remote data with the local manifest without writing anything."""
    _, client, store = _build(output, base_url, delay)
    with client:
        report = check_heroes(client, store, limit=limit)

    typer.echo(
        f"unchanged={report.unchanged} changed={len(report.changed)} "
        f"new={len(report.new)} missing={len(report.missing)} "
        f"not_downloaded={report.not_downloaded} "
        f"failed={len(report.failed)} elapsed={report.elapsed:.1f}s"
    )
    groups = (
        ("CHANGED", report.changed),
        ("NEW", report.new),
        ("MISSING", report.missing),
    )
    for label, items in groups:
        for item in items[:10]:
            typer.echo(f"  {label} {item}")


@app.command()
def status(output: OutputOption = None) -> None:
    """Show what is already stored locally."""
    directory = Path(output) if output else default_output_dir()
    store = DataStore(directory)

    stored = sum(1 for key in store.manifest.items if store.exists(key))
    missing = len(store.manifest.items) - stored
    size = sum(item.size for item in store.manifest.items.values())

    typer.echo(f"output:   {directory}")
    typer.echo(f"items:    {len(store.manifest.items)}")
    typer.echo(f"on disk:  {stored}")
    typer.echo(f"missing:  {missing}")
    typer.echo(f"bytes:    {size}")
    typer.echo(f"last run: {store.manifest.generated_at.isoformat()}")


if __name__ == "__main__":
    app()
