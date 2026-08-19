from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from app.core.config import get_settings

SQLITE_BUSY_TIMEOUT_MS = 30_000


def configure_sqlite_connection(engine: Engine) -> Engine:
    """Apply local-alpha SQLite pragmas to every pooled connection.

    WAL allows readers to continue while a short write transaction commits, while
    busy_timeout makes concurrent local actions wait briefly instead of failing
    immediately with ``database is locked``.  These settings do not make SQLite a
    multi-writer database; long write transactions should still be avoided.
    """

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()

    return engine


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {
            "check_same_thread": False,
            "timeout": SQLITE_BUSY_TIMEOUT_MS / 1000,
        }
    engine = create_engine(settings.database_url, **kwargs)
    if settings.database_url.startswith("sqlite"):
        configure_sqlite_connection(engine)
    return engine


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
