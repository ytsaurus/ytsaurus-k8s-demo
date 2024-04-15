import datetime
import os
import re
import sys

import click
from sqlalchemy import select

from lib import util

new_session = None
init_db = None
Slot = None


class SlotConflict(Exception):
    pass


@click.group()
@click.option("--user", envvar="DB_USER")
@click.option("--password", envvar="DB_PASS", prompt=True, hide_input=True)
@click.option("--host", envvar="DB_HOST")
@click.option("--port", envvar="DB_PORT")
@click.option("--name", envvar="DB_NAME")
def main(user, password, host, port, name):
    os.environ["DB_USER"] = user
    os.environ["DB_PASS"] = password
    os.environ["DB_HOST"] = host
    os.environ["DB_PORT"] = port
    os.environ["DB_NAME"] = name
    global new_session, Slot, init_db
    from lib.database import db_session as new_session_
    from lib.database import init_db as init_db_
    from lib.models import Slot as Slot_

    new_session = new_session_
    Slot = Slot_
    init_db = init_db_


@main.command()
def init():
    init_db()


@main.command()
def create_slots():
    slots = []
    with new_session() as session:
        for row in map(str.strip, sys.stdin.readlines()):
            if not row.strip():
                continue
            try:
                slots.append(create_slot(row, session))
            except SlotConflict as e:
                click.secho(
                    "Could not add slot at time [{}], it conflicts with existing slot(s): [{}]".format(
                        row, ", ".join(util.serialize_time(slot.time) for slot, in e.args[0])
                    ),
                    fg="red",
                    err=True,
                )
                print()

        session.commit()
        for slot in slots:
            print(slot.id)


def create_slot(isotime, session):
    if " " not in isotime:
        begin = util.deserialize_time(isotime)
        end = begin + datetime.timedelta(hours=1)
    else:
        begin, end = isotime.split(" ")
        begin = util.deserialize_time(begin)
        end = util.deserialize_time(end)

    slot = Slot(
        time=begin,
        end=end,
    )
    session.add(slot)
    return slot


def format_slot(slot):
    return " | ".join(
        [
            str(slot.id).ljust(4),
            util.serialize_time(slot.time),
            ("✅" if slot.enabled else "❌").ljust(len("enabled")),
            slot.namespace.ljust(32),
            slot.password.ljust(32),
            slot.email,
        ]
    )


table_header = " | ".join(
    [
        "id".ljust(4),
        "begin time".ljust(len(util.serialize_time(datetime.datetime.now(tz=datetime.timezone.utc)))),
        "enabled",
        "fqdn".ljust(32),
        "password".ljust(32),
        "email",
    ]
)


regex = re.compile(r"((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?")


def parse_time(time_str):
    if time_str is None:
        return

    parts = regex.match(time_str)
    if not parts:
        return

    return datetime.timedelta(**{name: int(param) for (name, param) in parts.groupdict().items() if param})


@main.command()
@click.option("-A", default=None, metavar="a")
@click.option("-B", default=None, metavar="b")
def list_slots(a, b):
    a = parse_time(a)
    b = parse_time(b)
    with new_session() as session:
        query = select(Slot)
        now = datetime.datetime.now(datetime.timezone.utc)
        if a is not None:
            query = query.where(Slot.time <= now + a)
        if b is not None:
            query = query.where(Slot.time > now - b)
        slots = list(session.execute(query))
        click.echo(table_header)
        for (slot,) in slots:
            click.echo(format_slot(slot))


@main.command()
def open_slots():
    with new_session() as session:
        for slot_id in map(int, sys.stdin.read().split()):
            slots = list(session.execute(select(Slot).with_for_update().where(Slot.id == slot_id)))
            if not slots:
                click.secho("No such slot {}".format(slot_id), fg="red", err=True)
                continue
            (
                [
                    slot,
                ],
            ) = slots
            if slot.email:
                click.secho("Slot is occupied, clear it first {}".format(slot_id), fg="red", err=True)
                continue
            slot.enabled = True
            session.add(slot)
        session.commit()


@main.command()
def close_slots():
    with new_session() as session:
        for slot_id in map(int, sys.stdin.read().split()):
            slots = list(session.execute(select(Slot).with_for_update().where(Slot.id == slot_id)))
            if not slots:
                click.secho("No such slot {}".format(slot_id), fg="red", err=True)
                continue
            (
                [
                    slot,
                ],
            ) = slots
            if not slot.enabled:
                click.secho("Slot is occupied, clear it first {}".format(slot_id), fg="red", err=True)
                continue
            slot.enabled = False
            session.add(slot)
        session.commit()


@main.command()
def clear_slots():
    with new_session() as session:
        for slot_id in map(int, sys.stdin.read().split()):
            slots = list(session.execute(select(Slot).with_for_update().where(Slot.id == slot_id)))
            if not slots:
                click.secho("No such slot {}".format(slot_id), fg="red", err=True)
                continue
            (
                [
                    slot,
                ],
            ) = slots
            slot.enabled = False
            slot.namespace = ""
            slot.password = ""
            slot.email = ""
            session.add(slot)
        session.commit()


@main.command()
def remove_slots():
    with new_session() as session:
        for slot_id in map(int, sys.stdin.read().split()):
            slots = list(session.execute(select(Slot).with_for_update().where(Slot.id == slot_id)))
            if not slots:
                click.secho("No such slot {}".format(slot_id), fg="red", err=True)
                continue
            (
                [
                    slot,
                ],
            ) = slots
            session.delete(slot)
        session.commit()


if __name__ == "__main__":
    main()
