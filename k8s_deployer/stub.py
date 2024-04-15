import base64
import logging
from pathlib import Path

import jinja2
from kubernetes import client, config

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
if root_logger.hasHandlers():
    root_handler = root_logger.handlers[0]
else:
    root_handler = logging.StreamHandler()
    root_logger.addHandler(root_handler)
root_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"))
base_logger = logging.getLogger("yt-demo")

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(Path(__file__).with_name("config_templates")))
jinja_env.filters["b64encode"] = base64.b64encode

DEMO_CONTOUR_FLAG = "yt-demo-contour"
MONITORING_DEFAULT_DEMAND_MARGIN = 5
MONITORING_DEFAULT_PING_MARGIN = 6

k8s_config_set = False


def setup_k8s_config(configuration=None):
    global k8s_config_set
    if configuration is not None:
        client.configuration.Configuration.set_default(configuration)
    elif not k8s_config_set:
        config.load_kube_config()
    k8s_config_set = True
