import datetime
import os
from pprint import pformat

import click
from kubernetes import client
from sqlalchemy import desc, select
from steps import create, remove
from stub import base_logger, main, setup_k8s_config

logger = base_logger.getChild("db_watcher")


@main.group()
@click.option("--user", envvar="DB_USER")
@click.option("--password", envvar="DB_PASS")
@click.option("--host", envvar="DB_HOST")
@click.option("--port", envvar="DB_PORT")
@click.option("--name", envvar="DB_NAME")
# @click.option('--slack-time', type=int, default=1)
def db_driven(user, password, host, port, name):
    os.environ["DB_USER"] = user
    os.environ["DB_PASS"] = password
    os.environ["DB_HOST"] = host
    os.environ["DB_PORT"] = port
    os.environ["DB_NAME"] = name
    from lib.database import init_db

    init_db()


@db_driven.command()
@click.option("--prep-time", type=int, default=15)
@click.pass_context
def create_pending(ctx, prep_time):
    from lib.database import db_session
    from lib.models import KuberState, Slot

    now = datetime.datetime.now(datetime.timezone.utc)
    pre_deploy_time = now - datetime.timedelta(minutes=prep_time)
    post_deploy_time = now + datetime.timedelta(minutes=prep_time)

    with db_session() as session:
        pending_slots = list(
            session.scalars(
                select(Slot)
                .with_for_update()
                .where(Slot.email != "")
                .where(Slot.time >= pre_deploy_time)
                .where(Slot.time < post_deploy_time)
                .where(Slot.kuber_state == KuberState.Empty)
            )
        )
        logger.info("Pending slots: %s", str(pending_slots))
        for slot in pending_slots:
            try:
                ctx.invoke(create, name=slot.namespace, password=slot.password)
                slot.kuber_state = KuberState.Published
            except Exception:  # noqa
                logger.exception("Exception occurred")
                slot.kuber_state = KuberState.Excepted
            session.add(slot)
        session.commit()


@db_driven.command()
@click.pass_context
def check_published(ctx):
    from lib.database import db_session
    from lib.models import KuberState, Mail, MailReason, Slot

    setup_k8s_config()
    k8s = client.CoreV1Api()
    now = datetime.datetime.now(datetime.timezone.utc)

    with db_session() as session:
        pending_slots = list(session.scalars(select(Slot).with_for_update().where(Slot.kuber_state == KuberState.Published)))
        logger.info("Published slots: %s", str(pending_slots))
        for slot in pending_slots:
            try:
                upload_demo_data = False
                ready = True
                for pod in k8s.list_namespaced_pod(namespace=slot.namespace).items:
                    if pod.metadata.owner_references[0].kind in ("StatefulSet", "ReplicaSet") and pod.status.phase != "Running":
                        logger.info(pformat(f"Pod {pod.metadata.name} is in state {pod.status.phase}"))
                        ready = False
                    if (
                        pod.metadata.owner_references[0].kind == "Job"
                        and pod.metadata.name.startswith("upload-demo-data")
                        and pod.status.phase == "Succeeded"
                    ):
                        upload_demo_data = True

                if not upload_demo_data:
                    logger.info(pformat("Job upload-demo-data has not Succeeded"))
                    ready = False
                if ready:
                    slot.kuber_state = KuberState.Running

                    session.add(
                        Mail(
                            time_to_send=now,
                            email=slot.email,
                            reason=MailReason.Reminder,
                            locale=slot.locale,
                            data=dict(
                                jupyter_url=f"https://jupyter-{slot.namespace}.demo.ytsaurus.tech",
                                ytsaurus_url=f"https://yt-{slot.namespace}.demo.ytsaurus.tech/ytdemo",
                                datalens_url=f"https://datalens-{slot.namespace}.demo.ytsaurus.tech/ytdemo",
                                button_url=f"https://jupyter-{slot.namespace}.demo.ytsaurus.tech/lab/tree/About%20this%20demo.ipynb?token={slot.password}",  # noqa
                                user="admin",
                                password=slot.password,
                                namespace=slot.namespace,
                                **slot.locale.time_format(slot.time),
                            ),
                        )
                    )
                    session.add(slot)
            except Exception as e:  # noqa
                logger.info(pformat(e))
        session.commit()


@db_driven.command()
@click.option("--slack-time", type=int, default=1)
@click.pass_context
def remove_expired(ctx, slack_time):
    from lib.database import db_session
    from lib.models import KuberState, Slot

    now = datetime.datetime.now(datetime.timezone.utc)

    with db_session() as session:
        pending_slots = list(
            session.scalars(
                select(Slot)
                .with_for_update()
                .where(Slot.kuber_state != None)  # noqa: E711
                .where(Slot.kuber_state != KuberState.Removed)
                .where(Slot.end < now - datetime.timedelta(minutes=slack_time))
            )
        )
        logger.info("Expired slots: %s", str(pending_slots))
        for slot in pending_slots:
            try:
                ctx.invoke(remove, namespace=slot.namespace)
                slot.kuber_state = KuberState.Removed
                session.add(slot)
            except Exception as e:  # noqa
                logger.info(pformat(e))
        session.commit()


@db_driven.command()
@click.option("--reserve-days", type=int, default=7)
@click.option("--interval-minutes", type=int, default=30)
@click.option("--size-minutes", type=int, default=120)
def create_slots(reserve_days, interval_minutes, size_minutes):
    from lib.database import db_session
    from lib.models import Slot

    interval = datetime.timedelta(minutes=interval_minutes)
    size = datetime.timedelta(minutes=size_minutes)

    now = datetime.datetime.now(datetime.timezone.utc)
    end_reserve = now + datetime.timedelta(days=reserve_days)

    with db_session() as session:
        last_slot = session.scalars(select(Slot).order_by(desc(Slot.time)).limit(1)).first()

        begin = last_slot.time + interval
        while begin < end_reserve:
            slot = Slot(
                time=begin,
                end=begin + size,
                enabled=True,
            )
            session.add(slot)
            begin += interval
        session.commit()


@db_driven.command()
@click.option("--slack-time", type=int, default=1)
@click.option("--prep-time", type=int, default=15)
@click.pass_context
def all(ctx, prep_time, slack_time):
    ctx.invoke(create_pending, prep_time=prep_time)
    ctx.invoke(check_published)
    ctx.invoke(remove_expired, slack_time=slack_time)
    ctx.invoke(create_slots)
