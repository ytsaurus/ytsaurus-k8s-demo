import base64
import json
import os
from pathlib import Path

from click.testing import CliRunner
from kubernetes import client

from .cli import main
from .stub import base_logger as logger
from .stub import setup_k8s_config


def configure_k8s(token):
    configuration = client.configuration.Configuration()
    configuration.api_key["authorization"] = token
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.host = os.environ["K8S_HOST"]

    certificate_file_name = "certificate_authority"
    p = Path(__file__).with_name(certificate_file_name)
    with open(p, "w") as f:
        f.write(os.environ["K8S_SSL_CERTIFICATE"])

    configuration.ssl_ca_cert = str(p)

    logger.info("Setting k8s config: %s", str(configuration))
    setup_k8s_config(configuration)
    logger.info("Configuration done")


def run_cli(command):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, command, catch_exceptions=True)
    logger.info("Result of a command (stdout): {}".format(result.stdout))
    logger.exception("Result of a command (stderr): {}".format(result.stderr))
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "isBase64Encoded": False,
        "body": {
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    }


def db_watcher_function(event, context):
    configure_k8s(context.token["access_token"])
    return run_cli(["db-driven", "all", "--prep-time", "10", "--slack-time", "3"])


def parse_event(event):
    try:
        json.loads(base64.b64decode(event["body"]).decode())
    except Exception:
        return event


def create_function(event, context):
    data = parse_event(event)
    name = data["name"]
    password = data["password"]
    persistent = data.get("persistent", False)

    configure_k8s(context.token["access_token"])
    return run_cli(["steps", "create", "-n", name, "-p", password, "--manual", "--persistent", str(persistent)])


def remove_function(event, context):
    data = parse_event(event)
    name = data["name"]

    configure_k8s(context.token["access_token"])
    return run_cli(["steps", "remove", "-n", name])


def send_monitoring_metrics(event, context):
    configure_k8s(context.token["access_token"])
    return run_cli(
        [
            "monitoring",
            "all",
            "--folder",
            "b1grh7kscp81dtkgs4rk",
            "--token",
            context.token["access_token"],
        ]
    )


if __name__ == "__main__":
    main()
