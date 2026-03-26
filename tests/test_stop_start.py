# tests/test_stop_start.py
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dokploy_ctl.cli import cli
from dokploy_ctl.dokploy import ComposeApp, ContainerInfo


def _mock_compose(app_name="test-app"):
    comp = MagicMock(spec=ComposeApp)
    comp.app_name = app_name
    return comp


def _mock_container(service, state="running", health="healthy", raw_status="Up 2h (healthy)"):
    c = MagicMock(spec=ContainerInfo)
    c.service = service
    c.state = state
    c.health = health
    c.raw_status = raw_status
    c.container_id = "abc123"
    c.image = "img:tag"
    c.uptime = "2h"
    return c


@patch("dokploy_ctl.stop_cmd.DokployClient")
def test_stop_succeeds(mock_client_cls):
    runner = CliRunner()
    result = runner.invoke(cli, ["stop", "test-id"])
    assert result.exit_code == 0
    assert "Stopping" in result.output
    assert "Stopped" in result.output
    assert "dokploy-ctl start test-id" in result.output


@patch("dokploy_ctl.stop_cmd.DokployClient")
def test_stop_api_error(mock_client_cls):
    mock_client_cls.return_value.stop_compose.side_effect = SystemExit(1)
    runner = CliRunner()
    result = runner.invoke(cli, ["stop", "test-id"])
    assert result.exit_code != 0


@patch("dokploy_ctl.start_cmd.DokployClient")
def test_start_succeeds(mock_client_cls):
    mock_client_cls.return_value.get_compose.return_value = _mock_compose("test-app")
    mock_client_cls.return_value.get_containers.return_value = [_mock_container("web")]

    runner = CliRunner()
    result = runner.invoke(cli, ["start", "test-id"])
    assert result.exit_code == 0
    assert "Starting" in result.output
