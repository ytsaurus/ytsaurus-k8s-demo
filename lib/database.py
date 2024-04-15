import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

try:

    engine = create_engine(
        "postgresql://{}:{}@{}:{}/{}".format(
            os.environ["DB_USER"],
            os.environ["DB_PASS"],
            os.environ["DB_HOST"],
            os.environ["DB_PORT"],
            os.environ["DB_NAME"],
        ),
        pool_pre_ping=True,
    )

    db_session = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
    )

    Base = declarative_base()
    Base.query = db_session.query_property()
except:  # noqa

    def db_session():
        pass

    Base = type


def init_db():
    import lib.models  # noqa

    Base.metadata.create_all(bind=engine)
