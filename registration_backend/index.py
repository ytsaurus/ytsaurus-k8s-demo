import base64
import datetime
import functools
import json
import logging
import traceback
import uuid

import click
import psycopg2
from sqlalchemy import select

from lib import util
from lib.database import db_session, init_db
from lib.models import KuberState, Locale, Mail, MailReason, Slot

DEBUG_MODE = True
PG_RETRY_COUNT = 3

if __name__ == "__main__":

    @click.group()
    def main():
        pass


def make_response(code, result=None, exception=None, version="unversioned"):
    body = {"code": code, "version": version}
    if result is not None:
        body["result"] = result

    if exception is not None and DEBUG_MODE:
        body["error"] = traceback.format_exc()

    return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "isBase64Encoded": False, "body": body}


def make_cloud_function(f):
    if __name__ == "__main__":

        @main.command()
        @click.option("--data")
        @functools.wraps(f)
        def callback(data):
            code, result = f(dict(body=data), None)
            response = make_response(code, result=result, version="cmd")
            click.echo(json.dumps(response))

        return callback

    @functools.wraps(f)
    def callback(event, context):
        if event["httpMethod"] == "OPTIONS":
            return dict(
                statusCode=200,
                headers={
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST,OPTIONS",
                },
            )
        try:
            for i in range(PG_RETRY_COUNT):
                try:
                    code, result = f(event, context)
                    return make_response(code, result=result, version=context.function_version)
                except psycopg2.OperationalError:
                    logging.exception("psycopg exception")
        except Exception as e:
            logging.exception("Got an exception in function")
            return make_response(500, exception=e, version=context.function_version)

    return callback


def get_time_boundary():
    time_from = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    time_to = time_from + datetime.timedelta(days=4)
    time_to = time_to.replace(hour=0, minute=0, second=0, microsecond=0)
    return time_from, time_to


@make_cloud_function
def timeslots(event, context):
    time_from, time_to = get_time_boundary()
    with db_session() as session:
        query = select(Slot)
        if time_from is not None:
            query = query.where(Slot.time >= time_from)
        if time_to is not None:
            query = query.where(Slot.time < time_to)
        query = query.order_by(Slot.time)

        return (
            200,
            [dict(id=slot.id, time=util.serialize_time(slot.time), enabled=slot.enabled) for slot in session.scalars(query)],
        )


def parse_event(event):
    try:
        return json.loads(base64.b64decode(event["body"]).decode())
    except Exception:
        raise Exception(event)


@make_cloud_function
def register(event, context):
    time_from, time_to = get_time_boundary()
    with db_session() as session:
        body = parse_event(event)
        try:
            slot_id = body["slot_id"]
            email = body["email"]
            locale = body["locale"]
            company = body.get("company", "")
        except KeyError:
            return 400, {}

        slot = session.get(Slot, slot_id, with_for_update=True)
        if slot is None or slot.time > time_to or slot.time < time_from:
            return 404, {}
        if not slot.enabled:
            return 409, {}

        now = datetime.datetime.now(datetime.timezone.utc)

        slot.email = email
        slot.enabled = False
        slot.namespace = uuid.uuid4().hex[:8]
        slot.password = f"{uuid.uuid4().hex}"
        slot.locale = Locale.from_front_value(locale)
        slot.kuber_state = KuberState.Empty
        slot.company = company

        slot.time = slot.time

        session.add(
            Mail(
                time_to_send=now,
                email=email,
                reason=MailReason.Greeting,
                locale=Locale.from_front_value(locale),
                data=dict(
                    url=f"https://jupyter-{slot.namespace}.demo.ytsaurus.tech",
                    user="admin",
                    password=slot.password,
                    namespace=slot.namespace,
                    **Locale.from_front_value(locale).time_format(slot.time),
                ),
            )
        )
        session.add(slot)
        session.commit()
        return 200, {}


if __name__ == "__main__":
    init_db()
    main()
