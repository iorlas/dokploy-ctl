# tests/test_find.py
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dokploy_ctl.cli import cli
from dokploy_ctl.dokploy import ComposeApp


def _mock_app(project_name, compose_id, name, status):
    app = MagicMock(spec=ComposeApp)
    app.project_name = project_name
    app.compose_id = compose_id
    app.name = name
    app.status = status
    return app


@patch("dokploy_ctl.find_cmd.DokployClient")
def test_find_lists_all(mock_client_cls):
    mock_client_cls.return_value.list_compose_apps.return_value = [
        _mock_app("aggre", "abc", "aggre", "done"),
        _mock_app("reelm", "def", "reelm", "done"),
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["find"])
    assert result.exit_code == 0
    assert "aggre" in result.output
    assert "reelm" in result.output
    assert "abc" in result.output


@patch("dokploy_ctl.find_cmd.DokployClient")
def test_find_filters_by_name(mock_client_cls):
    mock_client_cls.return_value.list_compose_apps.return_value = [
        _mock_app("aggre", "abc", "aggre", "done"),
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["find", "aggre"])
    assert "aggre" in result.output
    assert "reelm" not in result.output


@patch("dokploy_ctl.find_cmd.DokployClient")
def test_find_no_results(mock_client_cls):
    mock_client_cls.return_value.list_compose_apps.return_value = []
    runner = CliRunner()
    result = runner.invoke(cli, ["find"])
    assert "No compose apps found" in result.output
