import os

from sqlalchemy import (create_engine,
                        Column, Numeric, Text, ForeignKey)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DB_URL = os.environ["RSURF_DB"].replace("\\", "/")

# init
Base = declarative_base()
Session = sessionmaker()


# SQL Table Models


class Timeouts(Base):
    __tablename__ = "timeouts"

    user_id = Column(Numeric, primary_key=True)
    guild_id = Column(Numeric)

    expires = Column(Numeric)  # epoch when timeout is over
    roles = Column(Text)  # use text to record role id's, e.g., "1234545353453543|7693956806835636|4356346356"


# Engine
engine = create_engine(DB_URL)

Base.metadata.create_all(engine)  # ensure that all tables exist in database

Session.configure(bind=engine)
