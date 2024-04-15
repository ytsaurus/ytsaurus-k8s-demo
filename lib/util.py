import datetime


def deserialize_time(isotime: str) -> datetime.datetime:
    isotime = datetime.datetime.fromisoformat(isotime)
    if isotime.tzinfo is None:
        return isotime.replace(tzinfo=datetime.timezone.utc)
    return isotime


def serialize_time(time: datetime.datetime) -> str:
    return time.isoformat(timespec="minutes")
