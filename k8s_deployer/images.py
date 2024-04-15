import click

from .image_config import images
from .image_config import repo as cloud_repo


@click.command()
def refresh_images():
    import docker

    c = docker.client.from_env()

    for name, image in images.items():
        click.secho(f"Pulling {image.img}:{image.tag}", fg="yellow")
        img = c.images.pull(image.img, tag=image.tag)
        img.tag(f"{cloud_repo}/{image.img}", tag=image.tag)
        click.secho(f"Pushing {cloud_repo}/{image.img}:{image.tag}", fg="yellow")
        c.images.push(f"{cloud_repo}/{image.img}", tag=image.tag)
        click.secho(f"Refreshed {name}", fg="green")
