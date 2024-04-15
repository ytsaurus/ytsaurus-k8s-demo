import dataclasses
import datetime
import enum


class MailReason(enum.Enum):
    Greeting = "Greeting"
    Reminder = "Reminder"


@dataclasses.dataclass
class MailSpec:
    id: int
    email: str
    time: datetime.datetime
    fqdn: str
    login: str
    password: str
    reason: MailReason
