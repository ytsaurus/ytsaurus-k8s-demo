import datetime
import json
import os

import click
import requests
from kubernetes import client
from sqlalchemy import func, select

from .stub import (
    DEMO_CONTOUR_FLAG,
    MONITORING_DEFAULT_DEMAND_MARGIN,
    MONITORING_DEFAULT_PING_MARGIN,
    base_logger,
    setup_k8s_config,
)

logger = base_logger.getChild("metrics")


class Metrics:
    def __init__(self, name, labels):
        self.name = name
        self.stored = []
        self.labels = labels

    def add(self, component, value, labels=None):
        if labels is None:
            labels = {}
        self.stored.append((component, value, labels))

    def to_list(self):
        return [
            {
                "name": self.name,
                "labels": {
                    **self.labels,
                    **labels,
                    "signal": component,
                },
                "value": value,
            }
            for (component, value, labels) in self.stored
        ]

    def push(self, folder, token):
        data = json.dumps({"metrics": self.to_list()})
        logger.info("Pushing metrics to %s/custom: %s", folder, data)
        response = requests.post(
            f"https://monitoring.api.cloud.yandex.net/monitoring/v2/data/write?folderId={folder}&service=custom",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            data=data,
        )
        logger.info(
            "Response code: %s, json: %s",
            response.status_code,
            json.dumps(response.json()),
        )


@click.group()
@click.option("--user", envvar="DB_USER")
@click.option("--password", envvar="DB_PASS")
@click.option("--host", envvar="DB_HOST")
@click.option("--port", envvar="DB_PORT")
@click.option("--name", envvar="DB_NAME")
@click.pass_context
def monitoring(ctx, user, password, host, port, name):
    os.environ["DB_USER"] = user
    os.environ["DB_PASS"] = password
    os.environ["DB_HOST"] = host
    os.environ["DB_PORT"] = port
    os.environ["DB_NAME"] = name
    from lib.database import init_db

    init_db()


@monitoring.command()
@click.pass_obj
def liveness(obj, metrics=None):
    from lib.database import db_session
    from lib.models import Slot

    now = datetime.datetime.now(datetime.timezone.utc)

    with db_session() as session:
        demand = session.scalars(
            select(func.count(Slot.id))
            .where(Slot.email != "")
            .where(Slot.time <= now + datetime.timedelta(minutes=MONITORING_DEFAULT_DEMAND_MARGIN))
            .where(Slot.end >= now)
        ).first()
        promised = session.scalars(select(func.count(Slot.id)).where(Slot.email != "").where(Slot.time <= now).where(Slot.end >= now)).first()

    logger.info("demand: %s, promised: %s", demand, promised)

    if metrics is not None:
        metrics.add("demand", demand)
        metrics.add("promised", promised)

    setup_k8s_config()
    k8s = client.CoreV1Api()
    namespaces = []
    continuation_token = None
    labels = {
        "yt-demo": "true",
    }
    if obj[DEMO_CONTOUR_FLAG] is not None:
        labels[DEMO_CONTOUR_FLAG] = obj[DEMO_CONTOUR_FLAG]

    while True:
        resp = k8s.list_namespace(
            label_selector=",".join(f"{key}={value}" for key, value in labels.items()),
            _continue=continuation_token,
        )
        namespaces += resp.items
        continuation_token = resp.metadata._continue
        if continuation_token is None:
            break
    existent = len([namespace for namespace in namespaces])

    logger.info("current existent: %s", existent)

    if metrics is not None:
        metrics.add("existent", existent)

    now = datetime.datetime.now(datetime.timezone.utc)

    with db_session() as session:
        demanded_slots = [
            (slot.namespace, slot.password)
            for slot in session.scalars(
                select(Slot)
                .where(Slot.email != "")
                .where(Slot.time <= now + datetime.timedelta(minutes=MONITORING_DEFAULT_PING_MARGIN))
                .where(Slot.end >= now)
            )
        ]
    ui_codes = {i: 0 for i in range(1, 6)}
    jupyter_codes = {i: 0 for i in range(1, 6)}
    for namespace, password in demanded_slots:
        ui_login_response = requests.post(
            f"https://yt-{namespace}.demo.ytsaurus.tech/api/yt/ytdemo/login",
            data=json.dumps({"username": "admin", "password": password}),
        )

        logger.info(
            "UI login response code: %s for demo: %s",
            ui_login_response.status_code,
            namespace,
        )
        ui_codes[ui_login_response.status_code // 100] += 1

        jupyter_response = requests.get(f"https://jupyter-{namespace}.demo.ytsaurus.tech")
        logger.info(
            "Jupyter response code: %s for demo: %s",
            jupyter_response.status_code,
            namespace,
        )

        jupyter_codes[jupyter_response.status_code // 100] += 1

    logger.info("UI codes: %s", str(ui_codes))
    logger.info("Jupyter codes: %s", str(jupyter_codes))
    if metrics is not None:
        for code in ui_codes:
            metrics.add("ui-response-code", ui_codes[code], {"code": f"{code}xx"})
        for code in jupyter_codes:
            metrics.add("jupyter-response-code", jupyter_codes[code], {"code": f"{code}xx"})

    metrics.add("not-allocated", demand - existent)
    metrics.add("no-ui-ping", demand - ui_codes[2])
    metrics.add("no-jupyter-ping", demand - jupyter_codes[2])


@monitoring.command()
def opened(metrics=None):
    from lib.database import db_session
    from lib.models import Slot

    now = datetime.datetime.now(datetime.timezone.utc)

    with db_session() as session:
        opened_1d = session.scalars(
            select(func.count(Slot.id)).where(Slot.enabled).where(Slot.time > now).where(Slot.time <= now + datetime.timedelta(days=1))
        ).first()

        opened_4d = session.scalars(
            select(func.count(Slot.id)).where(Slot.enabled).where(Slot.time > now).where(Slot.time <= now + datetime.timedelta(days=4))
        ).first()

        opened_after_4d = session.scalars(select(func.count(Slot.id)).where(Slot.enabled).where(Slot.time > now + datetime.timedelta(days=4))).first()

    logger.info(
        "opened_1d: %s, opened_4d: %s, opened_after_4d: %s",
        opened_1d,
        opened_4d,
        opened_after_4d,
    )

    if metrics is not None:
        metrics.add("opened", opened_1d, {"interval": "1d"})
        metrics.add("opened", opened_4d, {"interval": "4d"})
        metrics.add("opened", opened_after_4d, {"interval": "afeter_4d"})


@monitoring.command("all")
@click.option("--folder", required=True)
@click.option("--token", required=True)
@click.pass_context
def all_monitorings(ctx, folder, token):
    metrics = Metrics(
        name="demo-manager",
        labels={
            DEMO_CONTOUR_FLAG: ctx.obj[DEMO_CONTOUR_FLAG],
        },
    )

    for check in [
        liveness,
        opened,
    ]:
        try:
            ctx.invoke(check, metrics=metrics)
        except Exception as e:
            logger.exception(e)

    metrics.push(folder, token)
