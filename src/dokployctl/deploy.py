"""Deploy and sync commands."""

import os
import sys
import time
from pathlib import Path

import click

from dokployctl.client import DOKPLOY_ID, _err, api_call, load_config, make_client, print_response
from dokployctl.containers import get_containers, show_deploy_log, show_problem_logs, verify_container_health
from dokployctl.env import resolve_env


def _do_sync(client, compose_id: str, compose_file: str, env_file: str | None, env_flag: bool = False) -> None:
    """Shared sync logic used by both sync and deploy commands."""
    compose_content = Path(compose_file).read_text()

    payload: dict = {
        "composeId": compose_id,
        "composeFile": compose_content,
        "sourceType": "raw",
        "composePath": "./docker-compose.yml",
    }

    env_content = resolve_env(env_flag, env_file, compose_content)
    if env_content is not None:
        payload["env"] = env_content

    resp = api_call(client, "POST", "compose.update", payload)
    if resp.is_error:
        print_response(resp)
        sys.exit(1)

    result = resp.json()
    stored_len = len(result.get("composeFile", ""))

    if stored_len < 10:
        _err(f"error: compose.update did not persist composeFile (got {stored_len} chars, sent {len(compose_content)})")
        sys.exit(1)

    click.echo(f"Synced: {stored_len} chars persisted, sourceType={result.get('sourceType', '?')}")

    if env_content is not None:
        click.echo(f"Env: {len(result.get('env', ''))} chars persisted")


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("compose_id", type=DOKPLOY_ID)
@click.argument("compose_file")
@click.option("--env-file", "-e", default=None, help="Path to .env file")
@click.option("--env", "env_flag", is_flag=True, default=False, help="Resolve ${VAR} refs from environment")
def sync(compose_id: str, compose_file: str, env_file: str | None, env_flag: bool) -> None:
    """Sync compose file + env to Dokploy."""
    url, token = load_config()
    client = make_client(url, token)
    _do_sync(client, compose_id, compose_file, env_file, env_flag)


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("compose_id", type=DOKPLOY_ID)
@click.argument("compose_file")
@click.option("--env-file", "-e", default=None, help="Path to .env file")
@click.option("--env", "env_flag", is_flag=True, default=False, help="Resolve ${VAR} refs from environment")
@click.option("--timeout", "-t", default=300, help="Deploy timeout in seconds (default: 300)")
def deploy(compose_id: str, compose_file: str, env_file: str | None, env_flag: bool, timeout: int) -> None:
    """Sync + deploy + poll + verify container health."""
    url, token = load_config()
    client = make_client(url, token)

    # Step 1: sync
    _do_sync(client, compose_id, compose_file, env_file, env_flag)

    # Step 2: snapshot previous deployment ID
    pre_resp = api_call(client, "GET", "deployment.allByCompose", {"composeId": compose_id})
    prev_deploy_id = None
    if not pre_resp.is_error:
        pre_deps = pre_resp.json()
        if pre_deps and isinstance(pre_deps, list):
            prev_deploy_id = pre_deps[0].get("deploymentId")

    # Step 3: trigger deploy
    image_tag = os.environ.get("IMAGE_TAG", "")
    title = f"Deploy {image_tag}" if image_tag else "Deploy via dokployctl"

    sys.stdout.flush()
    click.echo(f"\nTriggering deploy ({title})...")
    deploy_resp = api_call(
        client,
        "POST",
        "compose.deploy",
        {
            "composeId": compose_id,
            "title": title,
        },
    )
    if deploy_resp.is_error:
        print_response(deploy_resp)
        return

    click.echo("Deploy triggered. Polling status...")

    # Step 4: poll for NEW deployment
    max_attempts = timeout // 5
    for i in range(1, max_attempts + 1):
        time.sleep(5)
        status_resp = api_call(client, "GET", "deployment.allByCompose", {"composeId": compose_id})
        if status_resp.is_error:
            status_resp = api_call(client, "GET", "deployment.all", {"composeId": compose_id})

        if status_resp.is_error:
            click.echo(f"  [{i}/{max_attempts}] Failed to fetch status (HTTP {status_resp.status_code})")
            continue

        deployments = status_resp.json()
        if not deployments:
            click.echo(f"  [{i}/{max_attempts}] No deployments found")
            continue

        latest = deployments[0] if isinstance(deployments, list) else deployments

        if prev_deploy_id and latest.get("deploymentId") == prev_deploy_id:
            click.echo(f"  [{i}/{max_attempts}] Waiting for new deployment to appear...")
            continue

        dep_status = latest.get("status", "unknown")
        click.echo(f"  [{i}/{max_attempts}] status={dep_status}")

        if dep_status == "done":
            sys.stdout.flush()
            click.echo("\nDokploy reports deploy done.")
            break
        if dep_status == "error":
            _err("\nerror: Deploy failed")
            if latest.get("errorMessage"):
                _err(latest["errorMessage"])
            show_deploy_log(url, token, latest.get("logPath", ""))
            app_resp = api_call(client, "GET", "compose.one", {"composeId": compose_id})
            if not app_resp.is_error:
                app_name = app_resp.json().get("appName", "")
                containers = get_containers(client, app_name)
                if containers:
                    show_problem_logs(url, token, containers, app_name)
            sys.exit(1)
    else:
        _err(f"\nerror: Deploy timed out after {timeout}s")
        sys.exit(1)

    # Step 5: verify container health
    click.echo("Verifying container health...")
    app_resp = api_call(client, "GET", "compose.one", {"composeId": compose_id})
    if app_resp.is_error:
        _err("warning: could not fetch app info for health check")
        return

    app_name = app_resp.json().get("appName", "")
    if not app_name:
        _err("warning: no appName found, skipping health check")
        return

    healthy = verify_container_health(client, app_name, timeout=120)
    if healthy:
        sys.stdout.flush()
        click.echo("\nDeploy succeeded. All containers healthy.")
    else:
        _err("\nwarning: Deploy done but not all containers healthy.")
        containers = get_containers(client, app_name)
        show_problem_logs(url, token, containers, app_name)
        sys.exit(1)
