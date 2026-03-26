"""Find command — list/search compose apps."""

import click

from dokploy_ctl.dokploy import DokployClient
from dokploy_ctl.timer import Timer


@click.command()
@click.argument("name", required=False)
def find(name: str | None) -> None:
    """List compose apps. Optionally filter by project name."""
    timer = Timer()
    client = DokployClient()

    timer.log("Searching projects...")
    apps = client.list_compose_apps(name_filter=name)

    if not apps:
        click.echo("No compose apps found." + (f" (filter: {name})" if name else ""))
        timer.summary("Done.")
        return

    click.echo(f"\n  {'PROJECT':<20} {'COMPOSE ID':<26} {'NAME':<20} {'STATUS'}")
    for app in apps:
        click.echo(f"  {app.project_name:<20} {app.compose_id:<26} {app.name:<20} {app.status}")

    timer.summary(f"\n{len(apps)} compose apps found.")
