from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Institution, SourceObservation, SourceSnapshot
from app.services.cbk_dcp import DcpDirectoryRecord
from app.services.fetcher import SourceFetchError
from app.services.snapshot_store import SnapshotStore
from app.services.source_sync import sync_source
from app.services.sources import SourceDefinition


def _odpc_source() -> SourceDefinition:
    return SourceDefinition(
        id="odpc_registered",
        regulator="ODPC",
        url="https://www.odpc.go.ke/registered-data-handlers/",
        parser="odpc_handlers_v1",
    )


def _cbk_source() -> SourceDefinition:
    return SourceDefinition(
        id="cbk_dcp",
        regulator="CBK",
        url="https://www.centralbank.go.ke/example-dcp.pdf",
        parser="cbk_dcp_pdf_v1",
    )


def test_odpc_sync_snapshots_and_versions_observations(tmp_path: Path) -> None:
    html = b"""
<table><tr><th>#</th><th>Name</th><th>Data Handler Type</th><th>Registration number</th><th>County</th><th>Country</th><th>Status</th><th>Status as at</th></tr>
<tr><td>1</td><td>Example Credit Limited</td><td>Data Controller</td><td>INST-ABC123</td><td>NAIROBI</td><td>Kenya</td><td>Active</td><td>7/9/2026</td></tr>
<tr><td>2</td><td>Example Credit Limited</td><td>Data Processor</td><td>INST-ABC123</td><td>NAIROBI</td><td>Kenya</td><td>Active</td><td>7/9/2026</td></tr></table>
"""
    source = _odpc_source()
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


def test_cbk_sync_materializes_canonical_dcp_entity_and_links_source_observation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = _cbk_source()
    record = DcpDirectoryRecord(
        sequence=1,
        legal_name="Example Credit Limited",
        trading_name="Example Cash",
        website="https://example.co.ke",
        emails=("support@example.co.ke",),
        phones=("+254700000000",),
        postal_address=None,
        physical_address="Nairobi",
        licensed_date="2026-01-01",
    )
    monkeypatch.setattr("app.services.source_sync._parse", lambda source, body: [record])
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"fixture")
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        sync_source(
            source,
            store=SnapshotStore(tmp_path / "snapshots"),
            session=session,
            transport=transport,
        )
        session.commit()
        institutions = list(session.scalars(select(Institution)))
        observations = list(session.scalars(select(SourceObservation)))
        assert len(institutions) == 1
        assert institutions[0].legal_name == "Example Credit Limited"
        assert institutions[0].trading_name == "Example Cash"
        assert institutions[0].website == "https://example.co.ke"
        assert institutions[0].category == "digital_credit_provider"
        assert observations[0].institution_id == institutions[0].id

        sync_source(
            source,
            store=SnapshotStore(tmp_path / "snapshots"),
            session=session,
            transport=transport,
        )
        session.commit()
        assert len(list(session.scalars(select(Institution)))) == 1


def test_odpc_sync_classifies_http_200_challenge_page_as_access_restricted(tmp_path: Path) -> None:
    source = _odpc_source()
    challenge = b"<html><body><h1>Checking your browser</h1><p>Verify you are human</p></body></html>"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=challenge)
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        with pytest.raises(SourceFetchError) as raised:
            sync_source(
                source,
                store=SnapshotStore(tmp_path / "snapshots"),
                session=session,
                transport=transport,
            )
    assert raised.value.code == "source_access_restricted"
