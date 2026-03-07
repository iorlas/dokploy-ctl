"""Status command."""

import click

from dokployctl.client import DOKPLOY_ID, api_call, load_config, make_client, print_response
from dokployctl.containers import get_containers


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("compose_id", type=DOKPLOY_ID)
@click.option("--live", "-l", is_flag=True, help="Show live container health")
def status(compose_id: str, live: bool) -> None:
    """Show compose app status."""
    url, token = load_config()
    client = make_client(url, token)

    resp = api_call(client, "GET", "compose.one", {"composeId": compose_id})
    if resp.is_error:
        print_response(resp)
        return

    data = resp.json()
    app_name = data.get("appName", "?")
    click.echo(f"Name:         {data.get('name', '?')}")
    click.echo(f"App name:     {app_name}")
    click.echo(f"Status:       {data.get('composeStatus', '?')}")
    click.echo(f"Source type:   {data.get('sourceType', '?')}")
    click.echo(f"Compose type:  {data.get('composeType', '?')}")
    compose_file = data.get("composeFile", "")
    click.echo(f"Compose len:  {len(compose_file)} chars")
    env = data.get("env", "")
    env_keys = [line.split("=")[0] for line in env.strip().splitlines() if "=" in line]
    click.echo(f"Env keys:     {', '.join(env_keys) if env_keys else '(none)'}")

    deployments = data.get("deployments", [])
    if deployments:
        latest = deployments[0]
        click.echo(f"\nLast deploy:  {latest.get('title', '?')} ({latest.get('status', '?')})")
        click.echo(f"  at:         {latest.get('createdAt', '?')}")
        if latest.get("errorMessage"):
            click.echo(f"  error:      {latest['errorMessage']}")

    if live:
        click.echo("\nContainers:")
        containers = get_containers(client, app_name)
        if not containers:
            click.echo("  (none found)")
        for c in containers:
            short = c.get("name", "?").replace(f"{app_name}-", "").rstrip("-1234567890")
            click.echo(f"  {short:30} {c.get('state', '?'):10} {c.get('status', '')}")
