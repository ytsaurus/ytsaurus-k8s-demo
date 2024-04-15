import os

import click

from .db_watcher import db_driven
from .images import refresh_images
from .monitoring import monitoring
from .steps import steps
from .stub import DEMO_CONTOUR_FLAG


@click.group()
@click.pass_context
def main(ctx):
    ctx.obj = {
        DEMO_CONTOUR_FLAG: os.environ.get("CONTOUR"),
    }


main.add_command(db_driven)
main.add_command(refresh_images)
main.add_command(monitoring)
main.add_command(steps)

# db_watcher
# images
# monitoring
# steps
