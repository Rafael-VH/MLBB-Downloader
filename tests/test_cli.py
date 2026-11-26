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
