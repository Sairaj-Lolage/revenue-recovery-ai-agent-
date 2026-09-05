"""
backend/tests/test_events.py
=============================
Regression tests for local event-driven payment failure ingestion endpoint.

Tests verify:
1. Valid payment failure event processing.
2. Missing payment rejection (404).
3. Invalid event type rejection (400).
4. Missing event ID or invalid payload rejection (422).
5. Duplicate/repeated event handling without duplicate recovery actions.
6. Already recovered payment protection.
7. Opted-out customer protection.
8. Persistence integrity across RecoveryCase, RecoveryAction, and AuditLog tables.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.runner import run_recovery_agent
from app.db.database import Base, get_db
from app.db.models import AuditLog, Customer, Payment, RecoveryAction, RecoveryCase
from app.db.seed import seed
from app.main import app
from app.agent.graph import create_recovery_graph


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Return a fresh seeded in-memory DB session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    seed(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(db_session: Session):
    """FastAPI TestClient with DB dependency overridden."""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def mock_retry_reasoner(payment_data: dict, customer_data: dict, **kwargs) -> dict:
    """Deterministic mock LLM reasoner that chooses retry_payment."""
    return {
        "decision": "retry_payment",
        "reason": "Automatic retry recommended for event test.",
    }


# ── Event Trigger Unit Tests ──────────────────────────────────────────────────

def test_1_valid_payment_failure_event(client: TestClient, db_session: Session, monkeypatch) -> None:
    """Test 1: Valid payment failure event triggers recovery and updates RecoveryCase."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    # Find a failed payment in EASY_RECOVERY scenario
    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    assert easy_payment is not None

    payload = {
        "event_type": "payment.failed",
        "payment_id": easy_payment.id,
        "event_id": "evt_001",
    }

    response = client.post("/api/events/payment-failed", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["event_id"] == "evt_001"
    assert data["event_type"] == "payment.failed"
    assert data["payment_id"] == easy_payment.id
    assert data["status"] == "processed"
    assert "recovery_result" in data

    rec_res = data["recovery_result"]
    assert rec_res["payment_id"] == easy_payment.id
    assert rec_res["final_status"] == "success"

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    assert case is not None
    assert case.status == "RECOVERED"


def test_2_missing_payment_event(client: TestClient, db_session: Session) -> None:
    """Test 2: Event for nonexistent payment returns 404 and creates no case."""
    payload = {
        "event_type": "payment.failed",
        "payment_id": 99999,
        "event_id": "evt_002",
    }

    response = client.post("/api/events/payment-failed", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == 99999).first()
    assert case is None


def test_3_invalid_event_type(client: TestClient, db_session: Session) -> None:
    """Test 3: Event with unsupported event_type returns 400 and does not trigger recovery."""
    payload = {
        "event_type": "payment.success",
        "payment_id": 4,
        "event_id": "evt_003",
    }

    response = client.post("/api/events/payment-failed", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "unsupported event_type" in data["detail"].lower()


def test_4_missing_event_id(client: TestClient, db_session: Session) -> None:
    """Test 4: Payload with missing event_id fails Pydantic validation (422)."""
    payload = {
        "event_type": "payment.failed",
        "payment_id": 4,
    }

    response = client.post("/api/events/payment-failed", json=payload)
    assert response.status_code == 422


def test_5_duplicate_repeated_event(client: TestClient, db_session: Session, monkeypatch) -> None:
    """Test 5: Sending the same event twice does not cause unsafe duplicate recovery actions."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    payload = {
        "event_type": "payment.failed",
        "payment_id": easy_payment.id,
        "event_id": "evt_005",
    }

    # First delivery
    res1 = client.post("/api/events/payment-failed", json=payload)
    assert res1.status_code == 200

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    actions_after_first = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()

    # Second delivery with identical event_id
    res2 = client.post("/api/events/payment-failed", json=payload)
    assert res2.status_code == 200

    actions_after_second = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()
    assert actions_after_second == actions_after_first


def test_6_already_recovered_payment_event(client: TestClient, db_session: Session, monkeypatch) -> None:
    """Test 6: Failure event for an already recovered payment executes 0 recovery actions."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    # Pre-recover payment
    run_recovery_agent(payment_id=easy_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)

    payload = {
        "event_type": "payment.failed",
        "payment_id": easy_payment.id,
        "event_id": "evt_006",
    }

    res = client.post("/api/events/payment-failed", json=payload)
    assert res.status_code == 200
    data = res.json()
    rec_res = data["recovery_result"]

    assert rec_res["actions"] == []
    assert rec_res["final_status"] == "success"


def test_7_opted_out_customer_event(client: TestClient, db_session: Session, monkeypatch) -> None:
    """Test 7: Failure event for an opted-out customer results in STOPPED status and 0 recovery actions."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    opted_out_payment = (
        db_session.query(Payment)
        .join(Customer)
        .filter(Customer.opted_out == True)
        .first()
    )
    assert opted_out_payment is not None

    payload = {
        "event_type": "payment.failed",
        "payment_id": opted_out_payment.id,
        "event_id": "evt_007",
    }

    res = client.post("/api/events/payment-failed", json=payload)
    assert res.status_code == 200
    data = res.json()
    rec_res = data["recovery_result"]

    assert rec_res["decision"] == "stop"
    assert rec_res["final_status"] == "stopped"

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == opted_out_payment.id).first()
    assert case.status == "STOPPED"
    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    assert len(actions) == 0


def test_8_persistence_integrity_on_event(client: TestClient, db_session: Session, monkeypatch) -> None:
    """Test 8: Valid event creates entries in recovery_cases, recovery_actions, and audit_logs."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )

    payload = {
        "event_type": "payment.failed",
        "payment_id": easy_payment.id,
        "event_id": "evt_008",
    }

    res = client.post("/api/events/payment-failed", json=payload)
    assert res.status_code == 200

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    assert case is not None

    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    assert len(actions) >= 1

    audit_logs = db_session.query(AuditLog).filter(AuditLog.recovery_case_id == case.id).all()
    assert len(audit_logs) >= 3
