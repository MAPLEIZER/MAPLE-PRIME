from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Persist UTC datetimes and restore timezone awareness on SQLite reads.

    SQLite does not preserve timezone offsets for SQLAlchemy ``DateTime``
    values, even when ``timezone=True`` is requested. KDR compares marketplace
    observation timestamps in Python, so returning a naive datetime from SQLite
    can otherwise make a later aware UTC observation raise ``TypeError``.

    This decorator keeps the underlying SQL type unchanged while normalizing
    both bound and loaded values to aware UTC datetimes.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    @staticmethod
    def _normalize(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return self._normalize(value)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return self._normalize(value)
