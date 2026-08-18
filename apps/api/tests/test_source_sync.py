from pathlib import Path

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import SourceObservation, SourceSnapshot
from app.services.snapshot_store import SnapshotStore
from app.services.source_sync import sync_source
from app.services.sources import SourceDefinition


def test_odpc_sync_snapshots_and_versions_observations(tmp_path: Path) -> None:
    html = b"""
<table><tr><th>#</th><th>Name</th><th>Data Handler Type</th><th>Registration number</th><th>County</th><th>Country</th><th>Status</th><th>Status as at</th></tr>
<tr><td>1</td><td>Example Credit Limited</td><td>Data Controller</td><td>INST-ABC123</td><td>NAIROBI</td><td>Kenya</td><td>Active</td><td>7/9/2026</td></tr>
<tr><td>2</td><td>Example Credit Limited</td><td>Data Processor</td><td>INST-ABC123</td><td>NAIROBI</td><td>Kenya</td><td>Active</td><td>7/9/2026</td></tr></table>
"""
    source = SourceDefinition(
        id="odpc_registered",
        regulator="ODPC",
        url="https://www.odpc.go.ke/registered-data-handlers/",
        parser="odpc_handlers_v1",
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=html)
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        result = sync_source(
            source,
            store=SnapshotStore(tmp_path / "snapshots"),
            session=session,
            transport=transport,
        )
        session.commit()
        assert result.record_count == 2
        snapshots = list(session.scalars(select(SourceSnapshot)))
        observations = list(session.scalars(select(SourceObservation)))
        assert len(snapshots) == 1
        assert len(observations) == 2
        assert {item.external_id for item in observations} == {
            "INST-ABC123:data_controller",
            "INST-ABC123:data_processor",
        }

        sync_source(
            source,
            store=SnapshotStore(tmp_path / "snapshots"),
            session=session,
            transport=transport,
        )
        session.commit()
        assert len(list(session.scalars(select(SourceSnapshot)))) == 1
        assert len(list(session.scalars(select(SourceObservation)))) == 2
