# tests/test_find_fix.py
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dokploy_ctl.cli import cli
from dokploy_ctl.dokploy import ComposeApp, DokployClient


def test_find_returns_compose_apps_from_environments():
    """find must traverse environments[].compose, not project.compose"""
    with patch("dokploy_ctl.find_cmd.DokployClient") as mock_client_cls:
        mock_app = MagicMock(spec=ComposeApp)
        mock_app.project_name = "aggre"
        mock_app.compose_id = "c1"
        mock_app.name = "aggre"
        mock_app.status = "done"
        mock_client_cls.return_value.list_compose_apps.return_value = [mock_app]

        runner = CliRunner()
        result = runner.invoke(cli, ["find"])

    assert "aggre" in result.output
    assert "c1" in result.output


def test_list_compose_apps_traverses_environments():
    """DokployClient.list_compose_apps must read project.environments[].compose, not project.compose"""
    client = DokployClient.__new__(DokployClient)
    client._http = MagicMock()
    client._url = "https://example.com"
    client._token = "tok"

    mock_resp = MagicMock()
    mock_resp.is_error = False
    mock_resp.json.return_value = [
        {
            "name": "aggre",
            "projectId": "p1",
            # Old (buggy) path: project.compose — should be ignored
            "compose": [],
            "environments": [
                {
                    "name": "production",
                    "compose": [
                        {"composeId": "c1", "name": "aggre", "appName": "app-aggre", "composeStatus": "done"},
                        {"composeId": "c2", "name": "browserless", "appName": "app-bl", "composeStatus": "idle"},
                    ],
                }
            ],
        }
    ]
    client._http.get.return_value = mock_resp

    apps = client.list_compose_apps()
    assert len(apps) == 2
    assert apps[0].compose_id == "c1"
    assert apps[0].project_name == "aggre"
    assert apps[1].compose_id == "c2"


def test_list_compose_apps_filter():
    """name_filter matches against project or app name."""
    client = DokployClient.__new__(DokployClient)
    client._http = MagicMock()
    client._url = "https://example.com"
    client._token = "tok"

    mock_resp = MagicMock()
    mock_resp.is_error = False
    mock_resp.json.return_value = [
        {
            "name": "aggre",
            "projectId": "p1",
            "environments": [
                {
                    "name": "production",
                    "compose": [
                        {"composeId": "c1", "name": "aggre", "appName": "app-aggre", "composeStatus": "done"},
                    ],
                }
            ],
        },
        {
            "name": "reelm",
            "projectId": "p2",
            "environments": [
                {
                    "name": "production",
                    "compose": [
                        {"composeId": "c2", "name": "reelm", "appName": "app-reelm", "composeStatus": "done"},
                    ],
                }
            ],
        },
    ]
    client._http.get.return_value = mock_resp

    apps = client.list_compose_apps(name_filter="aggre")
    assert len(apps) == 1
    assert apps[0].compose_id == "c1"
