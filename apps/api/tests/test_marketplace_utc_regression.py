from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.repositories import AppRegistryRepository
from app.schemas.apps import PlayAppImportItem


def _item(observed_at: datetime, *, name: str = "Example Loan") -> PlayAppImportItem:
    return PlayAppImportItem(
        package_name="ke.co.example.utc",
        app_name=name,
        developer_name="Example Finance Limited",
        store_url="https://play.google.com/store/apps/details?id=ke.co.example.utc",
        source_provider="fixture",
        source_url="https://play.google.com/store/apps/details?id=ke.co.example.utc",
        observed_at=observed_at,
    )


def test_sqlite_marketplace_timestamps_remain_utc_aware_after_reload_and_reingest() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    first_seen = datetime(2026, 8, 19, 20, 0, tzinfo=UTC)
    later = first_seen + timedelta(hours=1)

    with Session(engine) as session:
        repository = AppRegistryRepository(session)
        app = repository.ingest_play(_item(first_seen))
        app_id = app.id
        session.commit()

        # Force the values to round-trip through SQLite. Vanilla
        # DateTime(timezone=True) returns naive datetimes on SQLite, which used
        # to make the repository's later comparisons raise TypeError.
        session.expire_all()
        loaded = repository.get(app_id)
        assert loaded is not None
        assert loaded.first_seen_at.tzinfo is not None
        assert loaded.last_seen_at.tzinfo is not None

        again = repository.ingest_play(_item(later, name="Example Loan Updated"))
        assert again.id == app_id
        assert again.first_seen_at == first_seen
        assert again.last_seen_at == later
        assert repository.latest_observation(app_id) is not None
        assert repository.latest_observation(app_id).observed_at.tzinfo is not None
