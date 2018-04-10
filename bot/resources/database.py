import os

from sqlalchemy import (create_engine,
                        Column, Numeric, Text, Interval, DateTime)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ["RSURF_DB"].replace("\\", "/")

# init
Base = declarative_base()
Session = sessionmaker()


# SQL Table Models


class Timeout(Base):
    __tablename__ = "timeouts"

    user_id = Column(Numeric, primary_key=True)
    guild_id = Column(Numeric)

    expires = Column(Numeric)  # epoch when timeout is over
    roles = Column(Text)  # use text to record role id's, e.g., "1234545353453543|7693956806835636|4356346356"

    reason = Column(Text)


class TimeoutLog(Base):
    __tablename__ = "timeout_log"

    id = Column(Numeric, primary_key=True)
    user_id = Column(Numeric)

    given_at = Column(DateTime)

    length = Column(Interval)

    reason = Column(Text)

    def __repr__(self):
        return "<TimeoutLog user_id={!r} given_at={!r}>".format(self.user_id, self.given_at)


class PrivateServer(Base):
    __tablename__ = "private_servers"

    id = Column(Numeric, primary_key=True)

    url = Column(Text)

    recommends = Column(Numeric, default=0)
    reports = Column(Numeric, default=0)

    message_id = Column(Numeric)

    submitter_id = Column(Numeric)

    name = Column(Text, default="")


# Engine
engine = create_engine(DB_URL)

Base.metadata.create_all(engine)  # ensure that all tables exist in database

Session.configure(bind=engine)
