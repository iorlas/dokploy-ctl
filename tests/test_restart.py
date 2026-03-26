# tests/test_restart.py
from unittest.mock import MagicMock, patch

import httpx
from click.testing import CliRunner

from dokploy_ctl.cli import cli


def _mock_response(data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = data
    resp.is_error = status_code >= 400
    resp.status_code = status_code
    return resp


@patch("dokploy_ctl.restart_cmd.load_config", return_value=("https://example.com", "token"))
@patch("dokploy_ctl.restart_cmd.make_client")
@patch("dokploy_ctl.restart_cmd.api_call")
def test_restart_redeploy_no_service(mock_api, mock_client, mock_config):
    mock_api.return_value = _mock_response({})
    runner = CliRunner()
    result = runner.invoke(cli, ["restart", "test-id"])
    assert result.exit_code == 0
    assert "Redeploying" in result.output
    assert "Redeploy triggered" in result.output


@patch("dokploy_ctl.restart_cmd.load_config", return_value=("https://example.com", "token"))
@patch("dokploy_ctl.restart_cmd.make_client")
@patch("dokploy_ctl.restart_cmd.api_call")
def test_restart_redeploy_error(mock_api, mock_client, mock_config):
    mock_api.return_value = _mock_response({}, status_code=500)
    runner = CliRunner()
    result = runner.invoke(cli, ["restart", "test-id"])
    assert result.exit_code != 0


@patch("dokploy_ctl.restart_cmd.load_config", return_value=("https://example.com", "token"))
@patch("dokploy_ctl.restart_cmd.make_client")
@patch("dokploy_ctl.restart_cmd.api_call")
@patch("dokploy_ctl.restart_cmd.get_containers")
def test_restart_specific_service(mock_containers, mock_api, mock_client, mock_config):
    mock_api.side_effect = [
        _mock_response({"appName": "myapp"}),  # compose.one
        _mock_response({}),  # docker.restartContainer
    ]
    mock_containers.return_value = [
        {"name": "myapp-web-1", "containerId": "abc12345678", "state": "running", "status": "Up 5m"},
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["restart", "test-id", "--service", "web"])
    assert result.exit_code == 0
    assert "Restarting web" in result.output
    assert "Restarted 1 container(s)" in result.output


@patch("dokploy_ctl.restart_cmd.load_config", return_value=("https://example.com", "token"))
@patch("dokploy_ctl.restart_cmd.make_client")
@patch("dokploy_ctl.restart_cmd.api_call")
@patch("dokploy_ctl.restart_cmd.get_containers")
def test_restart_service_not_found(mock_containers, mock_api, mock_client, mock_config):
    mock_api.return_value = _mock_response({"appName": "myapp"})
    mock_containers.return_value = [
        {"name": "myapp-db-1", "containerId": "abc12345678", "state": "running", "status": "Up 5m"},
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["restart", "test-id", "--service", "web"])
    assert result.exit_code != 0
