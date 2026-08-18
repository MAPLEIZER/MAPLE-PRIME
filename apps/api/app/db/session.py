from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.database_url, **kwargs)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
