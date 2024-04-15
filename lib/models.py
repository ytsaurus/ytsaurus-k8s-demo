import enum
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    TypeDecorator,
)

from lib.database import Base


class TimeStamp(TypeDecorator):
    cache_ok = True
    impl = DateTime
    LOCAL_TIMEZONE = datetime.utcnow().astimezone().tzinfo

    def process_bind_param(self, value: datetime, dialect):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)

        return value.replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value


class KuberState(enum.Enum):
    Empty = "Empty"
    Published = "Published"
    Excepted = "Excepted"
    Running = "Running"
    Removed = "Removed"


class MailReason(enum.Enum):
    Greeting = "Greeting"
    Reminder = "Reminder"

    def to_template_path(self):
        return {
            MailReason.Greeting: "greeting.jinja2",
            MailReason.Reminder: "reminder.jinja2",
        }[self]

    def ru_subject(self):
        return {
            MailReason.Greeting: "Ваш доступ к онлайн-демонстрации",
            MailReason.Reminder: "Ваш демо-кластер развернут и ждёт вас",
        }[self]

    def en_subject(self):
        return {
            MailReason.Greeting: "Your access to a YTsaurus demo cluster",
            MailReason.Reminder: "Your demo cluster has deployed",
        }[self]


class Locale(enum.Enum):
    RU = "RU"
    EN = "EN"

    @classmethod
    def from_front_value(cls, val):
        return {
            "ru": cls.RU,
            "en": cls.EN,
        }[val]

    def to_template_path(self):
        return {
            type(self).RU: "ru",
            type(self).EN: "en",
        }[self]

    def to_docs_path(self):
        return self.to_template_path()

    def to_subject(self, reason):
        return {
            type(self).RU: reason.ru_subject(),
            type(self).EN: reason.en_subject(),
        }[self]

    def time_format_zone(self, obj):
        return {
            type(self).RU: obj.astimezone(timezone(timedelta(hours=3))),
            type(self).EN: obj.astimezone(timezone.utc),
        }[self]

    def time_format(self, obj):
        padded_obj = self.time_format_zone(obj)

        date = padded_obj.date()
        time = padded_obj.time()
        tz = padded_obj.tzinfo

        return dict(
            time=time.strftime("%H:%M"),
            date={
                type(self).RU: date.strftime("%d.%m.%Y"),
                type(self).EN: date.strftime("%Y-%m-%d"),
            }[self],
            zone=str(tz),
        )


class JsonSerializable:
    _sub_serializers = {
        datetime: lambda o: o.isoformat(),
        KuberState: lambda o: o.value,
        MailReason: lambda o: o.value,
        Locale: lambda o: o.value,
    }

    def as_dict(self):
        return {c.name: self._sub_serializers.get(type(getattr(self, c.name)), lambda o: o)(getattr(self, c.name)) for c in self.__table__.columns}


class Slot(Base, JsonSerializable):
    __tablename__ = "slot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(TimeStamp)
    end = Column(TimeStamp)
    enabled = Column(Boolean, default=False)
    email = Column(String, default="")
    namespace = Column(String(50), default="")
    password = Column(String(50), default="")
    kuber_state = Column(Enum(KuberState))
    locale = Column(Enum(Locale))
    company = Column(Text)

    def __repr__(self):
        return f"Slot(id={self.id}, time={self.time}, enabled={self.enabled}, email={self.email}, namespace={self.namespace}, password={self.password}, kuber_state={self.kuber_state}, locale={self.locale})"  # noqa


class Mail(Base, JsonSerializable):
    __tablename__ = "mail"

    time_to_send = Column(TimeStamp, primary_key=True)
    email = Column(String, primary_key=True)
    reason = Column(Enum(MailReason), primary_key=True)
    locale = Column(Enum(Locale), primary_key=True)
    data = Column(JSON)
    sent = Column(Boolean, default=False)
