from __future__ import annotations

from typer.testing import CliRunner

from mlbb_downloader import cli
from mlbb_downloader.errors import ApiError

runner = CliRunner()


def test_api_errors_are_reported_without_a_traceback(monkeypatch) -> None:
    def explode(*args, **kwargs):
        raise ApiError("The target win rate must be greater")

    monkeypatch.setattr(cli, "win_rate_calculator", explode)

    result = runner.invoke(
        cli.app,
        [
            "addon",
            "win-rate",
            "--match-now",
            "1",
            "--wr-now",
            "60",
            "--wr-future",
            "50",
        ],
    )

    assert result.exit_code == 1
    assert "error: The target win rate must be greater" in result.output


def test_commands_are_registered() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    for name in ("sync", "check", "status", "heroes", "academy", "addon", "images"):
        assert name in result.output


def test_status_verify_reports_corruption(tmp_path) -> None:
    from mlbb_downloader.adapters.fsstore import DataStore

    store = DataStore(tmp_path, base_url="https://api.test/api")
    store.save_json(
        store.manifest_key_for("/heroes", {}),
        "heroes/index.json",
        {"ok": True},
        endpoint="/heroes",
    )
    store.flush()
    (tmp_path / "heroes" / "index.json").write_text("broken", encoding="utf-8")

    result = runner.invoke(cli.app, ["status", "--output", str(tmp_path), "--verify"])

    assert result.exit_code == 0
    assert "corrupted: 1" in result.output
