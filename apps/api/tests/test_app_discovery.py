import json
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import SourceObservation, SourceSnapshot
from app.services.app_discovery import build_cbk_discovery_seeds


def test_cbk_discovery_seeds_preserve_snapshot_and_published_contacts() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        snapshot = SourceSnapshot(
            source_id="cbk_dcp",
            source_url="https://www.centralbank.go.ke/dcp.pdf",
            sha256="a" * 64,
            media_type="application/pdf",
            retrieved_at=datetime(2026, 8, 19, tzinfo=UTC),
            storage_path="snapshots/a.pdf",
        )
        session.add(snapshot)
        session.flush()
        session.add(
            SourceObservation(
                snapshot_id=snapshot.id,
                regulator="CBK",
                external_id="1",
                status="licensed",
                payload_json=json.dumps(
                    {
                        "sequence": 1,
                        "legal_name": "Example Credit Limited",
                        "trading_name": "Example Cash",
                        "website": "https://www.example.co.ke",
                        "emails": ["support@example.co.ke", "INFO@EXAMPLE.CO.KE"],
                        "phones": [],
                    }
                ),
            )
        )
        session.flush()

        result = build_cbk_discovery_seeds(session)
        assert result["snapshot_id"] == snapshot.id
        assert len(result["records"]) == 1
        seed = result["records"][0]
        assert seed["legal_name"] == "Example Credit Limited"
        assert seed["trading_name"] == "Example Cash"
        assert seed["website_domain"] == "example.co.ke"
        assert seed["emails"] == ["support@example.co.ke", "info@example.co.ke"]
        assert "Example Cash" in seed["search_terms"]
        assert "example.co.ke" in seed["search_terms"]
