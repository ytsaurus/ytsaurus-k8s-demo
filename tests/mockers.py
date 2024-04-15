import logging

logger = logging.getLogger(__name__)


def templates_without_crd():
    from k8s_deployer.stub import jinja_env

    return jinja_env.list_templates(
        filter_func=lambda name: name.endswith(".yaml")
        and name
        not in {
            "namespace.yaml",
            "gateway.yaml",
            "grafana-route.yaml",
            "jupyter-route.yaml",
            "prometheus-route.yaml",
            "prometheus-service-monitor.yaml",
            "prometheus.yaml",
            "ui-route.yaml",
            "datalens/datalens-ui-route.yaml",
        }
    )


class NotNamespaceCreator:
    def __init__(self, ctx, name, manual):
        self.ctx = ctx
        self.name = name
        self.manual = manual

    def __enter__(self):
        logger.info("In testing NameSpaceCreator. Will not create namespace")
        return

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.exception(f"Got exception in Testing NamespaceCreator. Will remove namespace: ({exc_type}) {exc_tb}")


def run_cli_without_runner(command):
    from k8s_deployer.cli import main

    with main.make_context("main", command) as ctx:
        main.invoke(ctx)
