from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.repositories import ReconciliationRepository


def test_reconciliation_repository_deduplicates_and_supports_manual_resolution() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repo = ReconciliationRepository(session)
        first = repo.record(
            left_source_key="cbk_dcp:1",
            right_source_key="odpc_registered:INST-ABC123:data_controller",
            finding_type="candidate_match",
            confidence=0.95,
            summary="Candidate match — review required",
        )
        second = repo.record(
            left_source_key="cbk_dcp:1",
            right_source_key="odpc_registered:INST-ABC123:data_controller",
            finding_type="candidate_match",
            confidence=0.95,
            summary="Candidate match — review required",
        )
        session.commit()
        assert first.id == second.id
        assert first.review_state == "pending"

        repo.resolve(first.id, decision="confirmed", reviewer="local_user")
        session.commit()
        assert repo.get(first.id).review_state == "confirmed"
        assert repo.get(first.id).reviewed_by == "local_user"
