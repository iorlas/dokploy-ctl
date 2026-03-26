"""Tests for status command v2 — always shows containers, rich output, hints."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dokploy_ctl.cli import cli
from dokploy_ctl.dokploy import ComposeApp, ContainerInfo, Deployment


def _mock_compose(
    name="test",
    app_name="test-app",
    status="done",
    compose_file="x" * 100,
    env="",
    deployments=None,
):
    comp = MagicMock(spec=ComposeApp)
    comp.name = name
    comp.app_name = app_name
    comp.status = status
    comp.compose_file = compose_file
    comp.env = env
    comp.deployments = deployments or []
    return comp


def _mock_container(
    name,
    state="running",
    health="healthy",
    raw_status="Up 2h (healthy)",
    image="nginx:latest",
    uptime="2h",
    container_id="abc123def4",
):
    c = MagicMock(spec=ContainerInfo)
    c.service = name
    c.state = state
    c.health = health
    c.raw_status = raw_status
    c.image = image
    c.uptime = uptime
    c.container_id = container_id
    return c


def _mock_deployment(title="Deploy v1", status="done", created_at="2026-03-24T19:30:00Z", error_message=""):
    dep = MagicMock(spec=Deployment)
    dep.title = title
    dep.status = status
    dep.created_at = created_at
    dep.error_message = error_message
    return dep


@patch("dokploy_ctl.status.DokployClient")
def test_status_always_shows_containers(mock_client_cls):
    mock_client_cls.return_value.get_compose.return_value = _mock_compose(deployments=[_mock_deployment()])
    mock_client_cls.return_value.get_containers.return_value = [_mock_container("web")]

    runner = CliRunner()
    result = runner.invoke(cli, ["status", "test-id"])
    assert result.exit_code == 0
    assert "Containers:" in result.output or "SERVICE" in result.output
    assert "[00:00]" in result.output
    assert "total)" in result.output


@patch("dokploy_ctl.status.DokployClient")
def test_status_hints_for_unhealthy(mock_client_cls):
    mock_client_cls.return_value.get_compose.return_value = _mock_compose(env="")
    mock_client_cls.return_value.get_containers.return_value = [
        _mock_container("worker", health="unhealthy", raw_status="Up 2h (unhealthy)"),
    ]

    runner = CliRunner()
    result = runner.invoke(cli, ["status", "test-id"])
    assert "Hint:" in result.output
    assert "worker" in result.output


@patch("dokploy_ctl.status.DokployClient")
def test_status_no_containers_shows_hint(mock_client_cls):
    mock_client_cls.return_value.get_compose.return_value = _mock_compose(status="stopped")
    mock_client_cls.return_value.get_containers.return_value = []

    runner = CliRunner()
    result = runner.invoke(cli, ["status", "test-id"])
    assert result.exit_code == 0
    assert "Hint:" in result.output


@patch("dokploy_ctl.status.DokployClient")
def test_status_summary_counts_containers(mock_client_cls):
    mock_client_cls.return_value.get_compose.return_value = _mock_compose(
        name="aggre",
        app_name="compose-aggre-abc",
        compose_file="x" * 2847,
        env="IMAGE_TAG=v1\nDB_PASSWORD=secret",
        deployments=[_mock_deployment(title="Deploy main-a1b2c3d")],
    )
    mock_client_cls.return_value.get_containers.return_value = [
        _mock_container("worker", container_id="a1b2c3d4e5f6", image="ghcr.io/iorlas/aggre:main"),
        _mock_container("db", container_id="i9j0k1l2m3n4", image="postgres:16"),
    ]

    runner = CliRunner()
    result = runner.invoke(cli, ["status", "IWcYWttLzI"])
    assert result.exit_code == 0
    assert "2" in result.output
    assert "healthy" in result.output.lower()


@patch("dokploy_ctl.status.DokployClient")
def test_status_deprecated_live_flag_accepted(mock_client_cls):
    """--live flag should be accepted (backward compat) but deprecated."""
    mock_client_cls.return_value.get_compose.return_value = _mock_compose()
    mock_client_cls.return_value.get_containers.return_value = []

    runner = CliRunner()
    result = runner.invoke(cli, ["status", "test-id", "--live"])
    assert result.exit_code == 0
    assert "deprecated" in result.output.lower()
