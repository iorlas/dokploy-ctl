# tests/test_restart.py
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dokploy_ctl.cli import cli
from dokploy_ctl.dokploy import ComposeApp, ContainerInfo


def _mock_compose(app_name="myapp"):
    comp = MagicMock(spec=ComposeApp)
    comp.app_name = app_name
    return comp


def _mock_container(service, container_id="abc12345678", state="running"):
    c = MagicMock(spec=ContainerInfo)
    c.service = service
    c.container_id = container_id
    c.state = state
    c.health = "healthy"
    c.raw_status = "Up 5m (healthy)"
    return c


@patch("dokploy_ctl.restart_cmd.DokployClient")
def test_restart_redeploy_no_service(mock_client_cls):
    runner = CliRunner()
    result = runner.invoke(cli, ["restart", "test-id"])
    assert result.exit_code == 0
    assert "Redeploying" in result.output
    assert "Redeploy triggered" in result.output


@patch("dokploy_ctl.restart_cmd.DokployClient")
def test_restart_redeploy_error(mock_client_cls):
    mock_client_cls.return_value.redeploy_compose.side_effect = SystemExit(1)
    runner = CliRunner()
    result = runner.invoke(cli, ["restart", "test-id"])
    assert result.exit_code != 0


@patch("dokploy_ctl.restart_cmd.DokployClient")
def test_restart_specific_service(mock_client_cls):
    mock_client_cls.return_value.get_compose.return_value = _mock_compose("myapp")
    mock_client_cls.return_value.get_containers.return_value = [
        _mock_container("web", container_id="abc12345678"),
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["restart", "test-id", "--service", "web"])
    assert result.exit_code == 0
    assert "Restarting web" in result.output
    assert "Restarted 1 container(s)" in result.output


@patch("dokploy_ctl.restart_cmd.DokployClient")
def test_restart_service_not_found(mock_client_cls):
    mock_client_cls.return_value.get_compose.return_value = _mock_compose("myapp")
    mock_client_cls.return_value.get_containers.return_value = [
        _mock_container("db", container_id="abc12345678"),
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["restart", "test-id", "--service", "web"])
    assert result.exit_code != 0
