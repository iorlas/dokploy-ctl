"""Tests for smart deploy polling — event-driven container transitions."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dokploy_ctl.cli import cli
from dokploy_ctl.dokploy import ContainerInfo, Deployment


def _container(cid, service, state="running", health="healthy", raw_status="Up 1m (healthy)"):
    return ContainerInfo(
        container_id=cid,
        service=service,
        state=state,
        health=health,
        image="img",
        uptime="1m",
        raw_status=raw_status,
    )


def _deployment(dep_id, status="done", error_message="", log_path=""):
    dep = MagicMock(spec=Deployment)
    dep.deployment_id = dep_id
    dep.status = status
    dep.error_message = error_message
    dep.log_path = log_path
    return dep


def test_deploy_shows_transitions_not_dumb_status(tmp_path):
    """Deploy should show container transitions, not 'status=running' repeated."""
    compose = tmp_path / "docker-compose.prod.yml"
    compose.write_text("version: '3'\nservices:\n  web:\n    image: nginx")

    with patch("dokploy_ctl.deploy.DokployClient") as mock_client_cls:
        client = mock_client_cls.return_value
        client.url = "https://example.com"
        client.token = "tok"

        # update_compose
        mock_compose_updated = MagicMock()
        mock_compose_updated.compose_file = "x" * 100
        mock_compose_updated.env = ""
        client.update_compose.return_value = mock_compose_updated

        # get_compose for app_name
        mock_compose_app = MagicMock()
        mock_compose_app.app_name = "test-app"
        client.get_compose.return_value = mock_compose_app

        # get_latest_deployment: snapshot (old), then poll returns new=done
        old_dep = _deployment("old")
        new_dep = _deployment("new", status="done")
        client.get_latest_deployment.side_effect = [old_dep, new_dep]

        # trigger_deploy
        client.trigger_deploy.return_value = None

        # get_containers: pre-deploy (empty), then poll returns web container healthy
        new_container = _container("c1", "web")
        client.get_containers.side_effect = [
            [],  # pre-deploy snapshot
            [new_container],  # poll cycle 1
        ]

        with patch("time.sleep"):
            runner = CliRunner()
            result = runner.invoke(cli, ["deploy", "test-id", str(compose)])

    assert "status=running" not in result.output, "Old dumb polling output found"
    assert "[00:00]" in result.output, "Expected timestamps in output"
    assert result.exit_code == 0, f"Expected success, got exit_code={result.exit_code}\n{result.output}"


def test_deploy_shows_phase_labels(tmp_path):
    """Deploy output includes phase labels when containers transition."""
    compose = tmp_path / "docker-compose.prod.yml"
    compose.write_text("version: '3'\nservices:\n  worker:\n    image: myapp")

    with patch("dokploy_ctl.deploy.DokployClient") as mock_client_cls:
        client = mock_client_cls.return_value
        client.url = "https://example.com"
        client.token = "tok"

        mock_updated = MagicMock()
        mock_updated.compose_file = "x" * 100
        mock_updated.env = ""
        client.update_compose.return_value = mock_updated

        mock_app = MagicMock()
        mock_app.app_name = "test-app"
        client.get_compose.return_value = mock_app

        old_dep = _deployment("old")
        # Poll cycle 1: deploy running, containers empty (image pull)
        # Poll cycle 2: deploy done, new container healthy
        client.get_latest_deployment.side_effect = [
            old_dep,  # snapshot
            _deployment("new", status="running"),
            _deployment("new", status="done"),
        ]
        client.trigger_deploy.return_value = None

        old_container = _container("old1", "worker")
        new_container = _container("new1", "worker")
        client.get_containers.side_effect = [
            [old_container],  # pre-deploy snapshot
            [],  # poll 1: all stopped (image pull phase)
            [new_container],  # poll 2: new container healthy
        ]

        with patch("time.sleep"):
            runner = CliRunner()
            result = runner.invoke(cli, ["deploy", "test-id", str(compose)])

    assert "Phase:" in result.output, f"Expected phase labels\n{result.output}"
    assert result.exit_code == 0, f"Expected success\n{result.output}"


def test_deploy_error_shows_transition_history(tmp_path):
    """On deploy error, output includes transition history."""
    compose = tmp_path / "docker-compose.prod.yml"
    compose.write_text("version: '3'\nservices:\n  worker:\n    image: myapp")

    with (
        patch("dokploy_ctl.deploy.DokployClient") as mock_client_cls,
        patch("dokploy_ctl.deploy.show_deploy_log"),
        patch("dokploy_ctl.deploy.show_problem_logs"),
    ):
        client = mock_client_cls.return_value
        client.url = "https://example.com"
        client.token = "tok"

        mock_updated = MagicMock()
        mock_updated.compose_file = "x" * 100
        mock_updated.env = ""
        client.update_compose.return_value = mock_updated

        mock_app = MagicMock()
        mock_app.app_name = "test-app"
        client.get_compose.return_value = mock_app

        old_dep = _deployment("old")
        # Poll: new deployment with error
        error_dep = _deployment("new", status="error", error_message="exit code 1", log_path="/logs/x")
        client.get_latest_deployment.side_effect = [old_dep, error_dep]
        client.trigger_deploy.return_value = None

        old_container = _container("old1", "worker", state="running")
        exited_container = _container("old1", "worker", state="exited", health="\u2014", raw_status="Exited (1) 5s ago")
        client.get_containers.side_effect = [
            [old_container],  # pre-deploy snapshot
            [exited_container],  # poll 1: worker exited (non-zero)
        ]

        with patch("time.sleep"):
            runner = CliRunner()
            result = runner.invoke(cli, ["deploy", "test-id", str(compose)])

    assert result.exit_code != 0, "Expected failure"
    assert "deploy=error" in result.output or "Deploy failed" in result.output
    assert "[00:" in result.output


def test_deploy_success_shows_total_time(tmp_path):
    """Deploy success message must include total time."""
    compose = tmp_path / "docker-compose.prod.yml"
    compose.write_text("version: '3'\nservices:\n  web:\n    image: nginx")

    with patch("dokploy_ctl.deploy.DokployClient") as mock_client_cls:
        client = mock_client_cls.return_value
        client.url = "https://example.com"
        client.token = "tok"

        mock_updated = MagicMock()
        mock_updated.compose_file = "x" * 100
        mock_updated.env = ""
        client.update_compose.return_value = mock_updated

        mock_app = MagicMock()
        mock_app.app_name = "test-app"
        client.get_compose.return_value = mock_app

        old_dep = _deployment("old")
        new_dep = _deployment("new", status="done")
        client.get_latest_deployment.side_effect = [old_dep, new_dep]
        client.trigger_deploy.return_value = None

        # Pre-deploy empty, poll returns healthy new container
        new_container = _container("c1", "web")
        client.get_containers.side_effect = [[], [new_container]]

        with patch("time.sleep"):
            runner = CliRunner()
            result = runner.invoke(cli, ["deploy", "test-id", str(compose)])

    assert "Deploy succeeded" in result.output
    assert "total)" in result.output
    assert result.exit_code == 0


def test_deploy_no_dumb_polling_output(tmp_path):
    """Verify the deploy loop does not emit repeated 'Polling...' or 'status=running' lines."""
    compose = tmp_path / "docker-compose.prod.yml"
    compose.write_text("version: '3'\nservices:\n  api:\n    image: myapi")

    with patch("dokploy_ctl.deploy.DokployClient") as mock_client_cls:
        client = mock_client_cls.return_value
        client.url = "https://example.com"
        client.token = "tok"

        mock_updated = MagicMock()
        mock_updated.compose_file = "x" * 100
        mock_updated.env = ""
        client.update_compose.return_value = mock_updated

        mock_app = MagicMock()
        mock_app.app_name = "myapp"
        client.get_compose.return_value = mock_app

        # Simulate 3 "running" polls then done — old code would emit 3 "status=running" lines
        old_dep = _deployment("old")
        client.get_latest_deployment.side_effect = [
            old_dep,
            _deployment("new", status="running"),
            _deployment("new", status="running"),
            _deployment("new", status="running"),
            _deployment("new", status="done"),
        ]
        client.trigger_deploy.return_value = None

        new_container = _container("c1", "api")
        client.get_containers.side_effect = [
            [],  # pre-deploy
            [],  # poll 1
            [],  # poll 2
            [],  # poll 3
            [new_container],  # poll 4: healthy
        ]

        with patch("time.sleep"):
            runner = CliRunner()
            result = runner.invoke(cli, ["deploy", "test-id", str(compose)])

    # Should not have "status=running" repeated (old dumb polling pattern)
    running_count = result.output.count("status=running")
    assert running_count == 0, f"Found {running_count} dumb 'status=running' lines\n{result.output}"
    assert result.exit_code == 0


def test_deploy_done_but_unhealthy_auto_diagnoses(tmp_path):
    """When deploy=done but containers aren't healthy after grace period, auto-fetch logs and fail."""
    compose = tmp_path / "docker-compose.prod.yml"
    compose.write_text("version: '3'\nservices:\n  api:\n    image: myapi")

    elapsed_time = 0.0

    def fake_sleep(_):
        nonlocal elapsed_time
        elapsed_time += 6.0

    with (
        patch("dokploy_ctl.deploy.DokployClient") as mock_client_cls,
        patch("dokploy_ctl.deploy.show_deploy_log"),
        patch("dokploy_ctl.deploy.show_problem_logs") as mock_problem_logs,
    ):
        client = mock_client_cls.return_value
        client.url = "https://example.com"
        client.token = "tok"

        mock_updated = MagicMock()
        mock_updated.compose_file = "x" * 100
        mock_updated.env = ""
        client.update_compose.return_value = mock_updated

        mock_app = MagicMock()
        mock_app.app_name = "test-app"
        client.get_compose.return_value = mock_app

        old_dep = _deployment("old")
        done_dep = _deployment("new", status="done", log_path="/logs/build.log")
        client.get_latest_deployment.side_effect = [old_dep] + [done_dep] * 20
        client.trigger_deploy.return_value = None

        # Container stays unhealthy — running but not healthy (e.g. app error)
        unhealthy = _container("c1", "api", state="running", health="unhealthy", raw_status="Up 30s (unhealthy)")
        client.get_containers.side_effect = [
            [],  # pre-deploy
        ] + [[unhealthy]] * 20  # every poll: still unhealthy

        with (
            patch("time.sleep", side_effect=fake_sleep),
            patch("dokploy_ctl.timer.time.monotonic", side_effect=lambda: elapsed_time),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["deploy", "test-id", str(compose)])

    assert result.exit_code != 0, f"Expected failure, got:\n{result.output}"
    assert "Auto-diagnosing" in result.output, f"Expected auto-diagnose message:\n{result.output}"
    assert "Deploy failed" in result.output
    # Should have called show_problem_logs
    assert mock_problem_logs.called, "Expected show_problem_logs to be called"


def test_deploy_done_healthy_within_grace_succeeds(tmp_path):
    """When deploy=done and containers become healthy within grace period, succeed."""
    compose = tmp_path / "docker-compose.prod.yml"
    compose.write_text("version: '3'\nservices:\n  api:\n    image: myapi")

    with patch("dokploy_ctl.deploy.DokployClient") as mock_client_cls:
        client = mock_client_cls.return_value
        client.url = "https://example.com"
        client.token = "tok"

        mock_updated = MagicMock()
        mock_updated.compose_file = "x" * 100
        mock_updated.env = ""
        client.update_compose.return_value = mock_updated

        mock_app = MagicMock()
        mock_app.app_name = "test-app"
        client.get_compose.return_value = mock_app

        old_dep = _deployment("old")
        done_dep = _deployment("new", status="done")
        client.get_latest_deployment.side_effect = [old_dep, done_dep, done_dep]
        client.trigger_deploy.return_value = None

        # Poll 1: starting, Poll 2: healthy
        starting = _container("c1", "api", state="running", health="starting", raw_status="Up 5s (health: starting)")
        healthy = _container("c1", "api", state="running", health="healthy", raw_status="Up 15s (healthy)")
        client.get_containers.side_effect = [
            [],  # pre-deploy
            [starting],  # poll 1: starting
            [healthy],  # poll 2: healthy
        ]

        with patch("time.sleep"):
            runner = CliRunner()
            result = runner.invoke(cli, ["deploy", "test-id", str(compose)])

    assert result.exit_code == 0, f"Expected success:\n{result.output}"
    assert "Deploy succeeded" in result.output
