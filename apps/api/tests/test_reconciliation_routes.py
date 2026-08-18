from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.api.routes as routes
from app.db.base import Base
from app.db.repositories import ReconciliationRepository
from app.db.session import get_session
from app.main import app


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_reconciliation_run_requires_explicit_reconcile_action(monkeypatch) -> None:
    with _session() as session:
        app.dependency_overrides[get_session] = lambda: session
        monkeypatch.setattr(
            routes,
            "run_cbk_odpc_reconciliation",
            lambda _: SimpleNamespace(
                cbk_snapshot_id="cbk-1",
                odpc_snapshot_id="odpc-1",
                finding_count=252,
            ),
            raising=False,
        )
        client = TestClient(app)
        try:
            forbidden = client.post("/api/v1/reconciliation/cbk-odpc/run")
            assert forbidden.status_code == 403

            response = client.post(
                "/api/v1/reconciliation/cbk-odpc/run",
                headers={"X-KDR-Local-Action": "reconcile"},
            )
            assert response.status_code == 200
            assert response.json()["finding_count"] == 252
        finally:
            app.dependency_overrides.clear()


def test_reconciliation_findings_endpoint_returns_auditable_source_keys() -> None:
    with _session() as session:
        finding = ReconciliationRepository(session).record(
            left_source_key="cbk-snapshot:1",
            right_source_key="odpc-snapshot:INST-1:data_controller",
            finding_type="candidate_match",
            confidence=0.96,
            summary="Candidate match — manual review required.",
        )
        session.commit()
        app.dependency_overrides[get_session] = lambda: session
        try:
            response = TestClient(app).get("/api/v1/reconciliation/findings")
            assert response.status_code == 200
            item = response.json()[0]
            assert item["id"] == finding.id
            assert item["left_source_key"] == "cbk-snapshot:1"
            assert item["right_source_key"].startswith("odpc-snapshot:")
            assert item["review_state"] == "pending"
        finally:
            app.dependency_overrides.clear()


def test_manual_review_requires_explicit_action_and_persists_decision() -> None:
    with _session() as session:
        finding = ReconciliationRepository(session).record(
            left_source_key="cbk-snapshot:2",
            right_source_key="odpc-snapshot:INST-2:data_controller",
            finding_type="candidate_match",
            confidence=0.91,
            summary="Candidate match — manual review required.",
        )
        session.commit()
        app.dependency_overrides[get_session] = lambda: session
        client = TestClient(app)
        try:
            forbidden = client.post(
                f"/api/v1/reconciliation/findings/{finding.id}/review",
                json={"decision": "confirmed"},
            )
            assert forbidden.status_code == 403

            response = client.post(
                f"/api/v1/reconciliation/findings/{finding.id}/review",
                headers={"X-KDR-Local-Action": "review"},
                json={"decision": "confirmed"},
            )
            assert response.status_code == 200
            assert response.json()["review_state"] == "confirmed"
            assert response.json()["reviewed_by"] == "local_user"
            session.expire_all()
            assert ReconciliationRepository(session).get(finding.id).review_state == "confirmed"
        finally:
            app.dependency_overrides.clear()


def test_manual_review_rejects_invalid_decision() -> None:
    with _session() as session:
        finding = ReconciliationRepository(session).record(
            left_source_key="cbk-snapshot:3",
            right_source_key=None,
            finding_type="not_located",
            confidence=1.0,
            summary="ODPC record not located in reviewed snapshot.",
        )
        session.commit()
        app.dependency_overrides[get_session] = lambda: session
        try:
            response = TestClient(app).post(
                f"/api/v1/reconciliation/findings/{finding.id}/review",
                headers={"X-KDR-Local-Action": "review"},
                json={"decision": "violation"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
