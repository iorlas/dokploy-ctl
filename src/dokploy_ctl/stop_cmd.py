"""Stop command."""

import click

from dokploy_ctl.client import DOKPLOY_ID
from dokploy_ctl.dokploy import DokployClient
from dokploy_ctl.hints import hint_restart
from dokploy_ctl.timer import Timer


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("compose_id", type=DOKPLOY_ID)
def stop(compose_id: str) -> None:
    """Stop a running compose app."""
    timer = Timer()
    client = DokployClient()

    timer.log(f"Stopping compose {compose_id}...")
    client.stop_compose(compose_id)

    click.echo(hint_restart(compose_id))
    timer.summary("Stopped.")
