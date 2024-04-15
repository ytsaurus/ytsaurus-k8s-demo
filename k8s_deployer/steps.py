import os
import tempfile
from pprint import pformat

import click
import yaml
from datalens_connection import make_datalens_cypher
from image_config import images
from kubernetes import client
from kubernetes.utils import create_from_yaml
from stub import DEMO_CONTOUR_FLAG
from stub import base_logger as logger
from stub import jinja_env, main, setup_k8s_config

plural_makers = [
    lambda kind: kind.lower(),
    lambda kind: kind.lower() + "s",
    lambda kind: kind.lower() + "es",
]


def parse_spec_from_file(file, **kwargs):
    text = jinja_env.get_template(file).render(**kwargs)
    spec = yaml.load(text, yaml.FullLoader)
    return spec


def create_custom_object_from_spec(namespace, body):
    setup_k8s_config()
    customObjectApi = client.CustomObjectsApi()
    group, version = body["apiVersion"].split("/")
    for plural_maker in plural_makers:
        try:
            logger.info("Attempting plural: %s", plural_maker(body["kind"]))
            return customObjectApi.create_namespaced_custom_object(
                group,
                version,
                namespace,
                plural_maker(body["kind"]),
                body,
            )
        except client.exceptions.ApiException as e:
            logger.info("Error")
            exception = e
    raise exception


def create_object(
    creator,
    filename,
    namespace=None,
    **kwargs,
):
    if namespace is None:
        return creator(
            body=parse_spec_from_file(
                filename,
                **kwargs,
            ),
        )
    kwargs["namespace"] = namespace
    return creator(
        namespace=namespace,
        body=parse_spec_from_file(
            filename,
            **kwargs,
        ),
    )


@main.group()
def steps():
    pass


@steps.command()
@click.option("-n", "--name", required=True)
@click.option("--manual", default=False, is_flag=True)
@click.pass_context
def create_namespace(ctx, name, manual):
    setup_k8s_config()
    api_response = create_object(
        client.CoreV1Api().create_namespace,
        "namespace.yaml",
        name=name,
        contour="manual" if manual else ctx.obj[DEMO_CONTOUR_FLAG],
    )
    logger.info(pformat(api_response))


@steps.command()
@click.option("-n", "--namespace", required=True)
def remove(namespace):
    setup_k8s_config()
    k8s = client.CoreV1Api()

    if namespace not in [ns.metadata.name for ns in k8s.list_namespace().items]:
        logger.info("Namespace does not exist")
        return

    api_response = k8s.delete_namespace(namespace)
    logger.info(pformat(api_response))


class NamespaceCreator:
    def __init__(self, ctx, name, manual):
        self.ctx = ctx
        self.name = name
        self.manual = manual

    def __enter__(self):
        self.ctx.invoke(create_namespace, name=self.name, manual=self.manual)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.ctx.invoke(remove, namespace=self.name)


def list_templates():
    return jinja_env.list_templates(
        filter_func=lambda name: name.endswith(".yaml")
        and name
        not in {
            "namespace.yaml",
            "gateway.yaml",
        }
    )


def list_template_files(dir, priority):
    paths = []
    for root, _, filenames in os.walk(dir):
        paths.extend((root, filename) for filename in filenames)
    return [os.path.join(*parts) for parts in sorted(paths, key=lambda parts: priority.get(parts[-1], 0))]


@steps.command()
@click.option("-n", "--name", required=True)
@click.option("-p", "--password", required=True)
@click.option("--persistent", type=bool)
@click.option("--manual", default=False, is_flag=True)
@click.pass_context
def create(ctx, name, password, manual, persistent):
    priority = {
        "secret.yaml": 1000,
    }

    setup_k8s_config()
    k8s_client = client.ApiClient()

    with NamespaceCreator(ctx, name, manual):
        with tempfile.TemporaryDirectory() as dir:
            for template in list_templates():
                os.makedirs(os.path.join(dir, os.path.dirname(template)), exist_ok=True)
                with open(os.path.join(dir, template), "w") as f:
                    f.write(
                        jinja_env.get_template(template).render(
                            namespace=name,
                            password=password,
                            persistent=persistent,
                            images=images,
                            str=str,
                            datalens_cypher_text=make_datalens_cypher(password),
                        )
                    )

            for file in list_template_files(dir, priority):
                logger.info("Applying %s", file)

                try:
                    create_from_yaml(
                        k8s_client,
                        file,
                        verbose=True,
                        namespace=name,
                    )
                except Exception:
                    logger.exception("Will attempt to create as custom resource for %s instead", file)
                    with open(file, "r") as text:
                        create_custom_object_from_spec(namespace=name, body=yaml.load(text, yaml.FullLoader))
                logger.info("Successfully applied %s", file)
    logger.info("Everything is OK, eta 3min")


@steps.command("list-templates")
def list_templates_command():
    click.echo("\n".join(list_templates()))
