"""Database engine and session setup.

Everything goes through SQLAlchemy, so switching from SQLite to Postgres
(or any other supported database) only means changing DATABASE_URL.
"""

from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from .config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Stores datetimes as naive UTC and returns them as timezone-aware UTC.

    SQLite has no timezone support, so storing plain UTC keeps behaviour
    identical across SQLite and Postgres.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


def create_db_engine(url: str) -> Engine:
    kwargs: dict = {"echo": settings.sql_echo}
    if url.startswith("sqlite"):
        # FastAPI may use a session from a different thread than the one that created it.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True

    db_engine = create_engine(url, **kwargs)

    if db_engine.dialect.name == "sqlite":
        # SQLite ignores foreign keys (and ON DELETE CASCADE) unless asked.
        @event.listens_for(db_engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return db_engine


engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
