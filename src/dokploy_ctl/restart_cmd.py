"""Restart command — restart a specific service or all services."""

import click

from dokploy_ctl.client import DOKPLOY_ID, _err, api_call, load_config, make_client
from dokploy_ctl.containers import get_containers
from dokploy_ctl.output import parse_service_name
from dokploy_ctl.timer import Timer


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("compose_id", type=DOKPLOY_ID)
@click.option("--service", "-s", default=None, help="Restart a specific service (by name)")
def restart(compose_id: str, service: str | None) -> None:
    """Restart containers. Without --service, redeploys the compose app."""
    timer = Timer()
    url, token = load_config()
    client = make_client(url, token)

    if service:
        # Find the container ID for this service
        app_resp = api_call(client, "GET", "compose.one", {"composeId": compose_id})
        if app_resp.is_error:
            _err(f"error: could not fetch compose app (HTTP {app_resp.status_code})")
            raise SystemExit(1)

        app_name = app_resp.json().get("appName", "")
        containers = get_containers(client, app_name)

        matching = [c for c in containers if service in parse_service_name(c.get("name", ""), app_name)]
        if not matching:
            _err(f"error: no container found matching service '{service}'")
            available = [parse_service_name(c.get("name", ""), app_name) for c in containers]
            if available:
                click.echo(f"Available services: {', '.join(sorted(set(available)))}")
            raise SystemExit(1)

        for c in matching:
            cid = c.get("containerId", "")
            svc = parse_service_name(c.get("name", ""), app_name)
            timer.log(f"Restarting {svc} (container: {cid[:8]})...")
            resp = api_call(client, "POST", "docker.restartContainer", {"containerId": cid})
            if resp.is_error:
                _err(f"error: restart failed for {svc} (HTTP {resp.status_code})")
                raise SystemExit(1)

        timer.summary(f"Restarted {len(matching)} container(s).")
    else:
        # Redeploy the whole compose app
        timer.log(f"Redeploying compose {compose_id}...")
        resp = api_call(client, "POST", "compose.redeploy", {"composeId": compose_id})
        if resp.is_error:
            _err(f"error: redeploy failed (HTTP {resp.status_code})")
            raise SystemExit(1)
        timer.summary("Redeploy triggered.")
        click.echo(f"\nHint: Monitor with: dokploy-ctl status {compose_id}")
