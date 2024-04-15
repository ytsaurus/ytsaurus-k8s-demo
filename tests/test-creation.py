import logging
import os
import time
from pprint import pformat

from kubernetes import client

from k8s_deployer.main import configure_k8s

from .mockers import NotNamespaceCreator, run_cli_without_runner, templates_without_crd

NAMESPACE_PASSWORD = "test-cluster-password"

logger = logging.getLogger(__name__)


def prepare_env():
    env_file_path = os.path.join("/tmp", "os-demo-env.txt")
    cert_file_path = os.path.join("/tmp", "os-demo-certificate_authority")
    try:
        # to hide some envs from GH action logs, we use file
        with open(env_file_path, "r") as f:
            for s in f.readlines():
                key, value = s.strip().split("=")
                os.environ[key] = value
        with open(cert_file_path, "r") as f:
            os.environ["K8S_SSL_CERTIFICATE"] = f.read()
    except Exception:
        logger.exception("Exception while reading files")


def validate_env():

    assert os.environ.get("K8S_HOST") is not None, "K8S_HOST is not set"
    assert os.environ.get("IAM_TOKEN") is not None, "IAM_TOKEN is not set"
    assert os.environ.get("K8S_SSL_CERTIFICATE") is not None, "K8S_SSL_CERTIFICATE is not set"
    assert os.environ.get("NAMESPACE_NAME") is not None, "NAMESPACE_NAME is not set"


def is_cluster_ok():
    k8s = client.CoreV1Api()
    upload_demo_data = False
    ready = True
    for pod in k8s.list_namespaced_pod(namespace=os.environ.get("NAMESPACE_NAME")).items:
        if pod.metadata.owner_references[0].kind in ("StatefulSet", "ReplicaSet") and pod.status.phase != "Running":
            logger.info(pformat(f"Pod {pod.metadata.name} is in state {pod.status.phase}"))
            ready = False
            break
        if pod.metadata.owner_references[0].kind == "Job" and pod.metadata.name.startswith("upload-demo-data") and pod.status.phase == "Succeeded":
            upload_demo_data = True

    if not upload_demo_data:
        logger.info(pformat("Job upload-demo-data has not Succeeded"))
        ready = False

    return ready


def test_create_cluster(mocker):
    mocker.patch("k8s_deployer.steps.list_templates", templates_without_crd)
    mocker.patch("k8s_deployer.steps.NamespaceCreator", NotNamespaceCreator)
    mocker.patch("k8s_deployer.image_config.repo", "cr.yandex/crptkkbc0947ickrtnp7")
    mocker.patch("k8s_deployer.main.run_cli", run_cli_without_runner)

    prepare_env()
    validate_env()
    configure_k8s(os.environ["IAM_TOKEN"])
    logger.warning(f"Will create cluster in namespace: {os.environ.get('NAMESPACE_NAME')}")
    run_cli_without_runner(["steps", "create", "-n", os.environ.get("NAMESPACE_NAME"), "-p", NAMESPACE_PASSWORD, "--persistent", str(False)])
    times_tried = 0
    is_ok = False
    while times_tried < 30:
        try:
            is_ok = is_cluster_ok()
            assert is_ok
            logger.info("Cluster is ready")
            break
        except Exception:
            times_tried += 1
            logger.info("Cluster is not ready yet. Waiting...")
            time.sleep(60)
    assert is_ok
