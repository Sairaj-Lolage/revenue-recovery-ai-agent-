"""
backend/tests/test_event_simulation.py
======================================
Automated End-to-End Regression Tests for the Local Payment Failure Event Simulator.

Tests cover:
1. test_simulated_failure_triggers_recovery
2. test_easy_recovery_end_to_end (Scenario A)
3. test_payment_link_recovery_end_to_end (Scenario B)
4. test_follow_up_escalates_unpaid_case (Scenario C)
5. test_follow_up_recovers_completed_payment (Scenario D)
6. test_opted_out_event_does_not_recover (Scenario E)
7. test_already_recovered_event_is_idempotent (Scenario F)
8. test_duplicate_event_is_safe (Scenario G)
9. test_unknown_payment_event_fails_cleanly (Scenario H)
10. test_recovery_actions_and_audit_logs_are_persisted (Scenario I)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import AuditLog, Customer, Payment, RecoveryAction, RecoveryCase
from app.db.seed import seed
from app.events.simulator import simulate_payment_completion, simulate_payment_failure
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
    """Deterministic mock LLM reasoner choosing retry_payment."""
    return {
        "decision": "retry_payment",
        "reason": "Automatic retry recommended for simulation test.",
    }


def mock_evaluation_reasoner(payment_data: dict, customer_data: dict, actions_history: list = None, **kwargs) -> dict:
    """Adaptive evaluation reasoner matching standard multi-step recovery policy."""
    history_tools = [a["tool"] for a in (actions_history or [])]
    if "retry_payment" not in history_tools:
        return {"decision": "retry_payment", "reason": "Attempting payment retry."}
    elif "create_payment_link" not in history_tools:
        return {"decision": "create_payment_link", "reason": "Retry failed; generating payment link."}
    elif "send_recovery_message" not in history_tools:
        return {"decision": "send_recovery_message", "reason": "Sending payment link to customer."}
    return {"decision": "stop", "reason": "All recovery actions attempted."}


# ── End-to-End Event Simulation Tests ────────────────────────────────────────

def test_1_simulated_failure_triggers_recovery(db_session: Session, monkeypatch) -> None:
    """Test 1: Simulator generates payment.failed event and triggers recovery flow."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    result = simulate_payment_failure(payment_id=4, db=db_session, event_id="evt_test_01")
    assert result["event_id"] == "evt_test_01"
    assert result["event_type"] == "payment.failed"
    assert result["payment_id"] == 4
    assert result["status"] == "processed"
    assert "recovery_result" in result


def test_2_easy_recovery_end_to_end(db_session: Session, monkeypatch) -> None:
    """Test 2 (Scenario A): Failure event on EASY_RECOVERY payment recovers full amount."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    assert easy_payment is not None

    result = simulate_payment_failure(payment_id=easy_payment.id, db=db_session)
    rec = result["recovery_result"]

    assert rec["final_status"] == "success"
    assert rec["amount_recovered_paise"] == easy_payment.amount_paise

    # Verify DB persistence
    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    assert case is not None
    assert case.status == "RECOVERED"
    assert case.amount_recovered_paise == easy_payment.amount_paise

    # Verify payment status updated to success
    payment_in_db = db_session.get(Payment, easy_payment.id)
    assert payment_in_db.status == "success"


def test_3_payment_link_recovery_end_to_end(db_session: Session, monkeypatch) -> None:
    """Test 3 (Scenario B): Failure event on PAYMENT_LINK_RECOVERY payment creates link & message."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_evaluation_reasoner)

    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    assert link_payment is not None

    result = simulate_payment_failure(payment_id=link_payment.id, db=db_session)
    rec = result["recovery_result"]

    assert rec["final_status"] == "in_progress"
    assert rec["amount_recovered_paise"] == 0

    actions_executed = [a.get("tool") or a.get("action_type") for a in rec["actions"]]
    assert "create_payment_link" in actions_executed
    assert "send_recovery_message" in actions_executed

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    assert case.status == "IN_PROGRESS"
    assert case.amount_recovered_paise == 0


def test_4_follow_up_escalates_unpaid_case(db_session: Session, monkeypatch) -> None:
    """Test 4 (Scenario C): Second simulated event on IN_PROGRESS unpaid payment escalates case."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_evaluation_reasoner)

    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )

    # Initial event run
    res1 = simulate_payment_failure(payment_id=link_payment.id, db=db_session)
    assert res1["recovery_result"]["final_status"] == "in_progress"

    # Second event run (follow-up check)
    res2 = simulate_payment_failure(payment_id=link_payment.id, db=db_session)
    rec2 = res2["recovery_result"]

    assert rec2["final_status"] == "escalated"
    assert rec2["execution_result"]["action"] == "follow_up"

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    assert case.status == "ESCALATED"


def test_5_follow_up_recovers_completed_payment(db_session: Session, monkeypatch) -> None:
    """Test 5 (Scenario D): Payment completed via link transitions IN_PROGRESS case to RECOVERED."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_evaluation_reasoner)

    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )

    # 1. Initial event -> link created
    res1 = simulate_payment_failure(payment_id=link_payment.id, db=db_session)
    assert res1["recovery_result"]["final_status"] == "in_progress"

    # 2. Simulate customer completing payment via link
    comp_res = simulate_payment_completion(payment_id=link_payment.id, db=db_session)
    assert comp_res["success"] is True

    # 3. Subsequent event / follow-up run
    res2 = simulate_payment_failure(payment_id=link_payment.id, db=db_session)
    rec2 = res2["recovery_result"]

    assert rec2["final_status"] == "success"
    assert rec2["amount_recovered_paise"] == link_payment.amount_paise

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    assert case.status == "RECOVERED"
    assert case.amount_recovered_paise == link_payment.amount_paise


def test_6_opted_out_event_does_not_recover(db_session: Session, monkeypatch) -> None:
    """Test 6 (Scenario E): Simulated event for opted-out customer results in STOPPED and 0 actions."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    opted_out_payment = (
        db_session.query(Payment)
        .join(Customer)
        .filter(Customer.opted_out == True)
        .first()
    )
    assert opted_out_payment is not None

    result = simulate_payment_failure(payment_id=opted_out_payment.id, db=db_session)
    rec = result["recovery_result"]

    assert rec["decision"] == "stop"
    assert rec["final_status"] == "stopped"
    assert rec["actions"] == []

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == opted_out_payment.id).first()
    assert case.status == "STOPPED"
    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    assert len(actions) == 0


def test_7_already_recovered_event_is_idempotent(db_session: Session, monkeypatch) -> None:
    """Test 7 (Scenario F): Event for already successful payment does not re-execute actions."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )

    # Initial recovery
    simulate_payment_failure(payment_id=easy_payment.id, db=db_session)

    # Repeat event on recovered payment
    res2 = simulate_payment_failure(payment_id=easy_payment.id, db=db_session)
    rec2 = res2["recovery_result"]

    assert rec2["final_status"] == "success"
    assert rec2["actions"] == []


def test_8_duplicate_event_is_safe(db_session: Session, monkeypatch) -> None:
    """Test 8 (Scenario G): Duplicate delivery of event_id does not cause duplicate recovery actions."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )

    # Event delivery 1
    simulate_payment_failure(payment_id=easy_payment.id, db=db_session, event_id="evt_dup_99")
    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    actions_count1 = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()

    # Event delivery 2 (duplicate event_id)
    simulate_payment_failure(payment_id=easy_payment.id, db=db_session, event_id="evt_dup_99")
    actions_count2 = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()

    assert actions_count2 == actions_count1


def test_9_unknown_payment_event_fails_cleanly(client: TestClient, db_session: Session) -> None:
    """Test 9 (Scenario H): Event for unknown payment returns 404 and creates 0 RecoveryCases."""
    payload = {
        "event_type": "payment.failed",
        "payment_id": 999999,
        "event_id": "evt_unknown",
    }
    response = client.post("/api/events/payment-failed", json=payload)
    assert response.status_code == 404

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == 999999).first()
    assert case is None


def test_10_recovery_actions_and_audit_logs_are_persisted(db_session: Session, monkeypatch) -> None:
    """Test 10 (Scenario I): Verify table separation across recovery_cases, recovery_actions, and audit_logs."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )

    simulate_payment_failure(payment_id=easy_payment.id, db=db_session, event_id="evt_pers_01")

    # 1. RecoveryCase
    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    assert case is not None
    assert case.status == "RECOVERED"

    # 2. RecoveryAction
    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    assert len(actions) == 1
    assert actions[0].action_type == "retry_payment"
    assert actions[0].approved is True
    assert actions[0].amount_recovered_paise == easy_payment.amount_paise

    # 3. AuditLog
    audit_logs = db_session.query(AuditLog).filter(AuditLog.recovery_case_id == case.id).all()
    assert len(audit_logs) >= 3
    event_types = [log.event_type for log in audit_logs]
    assert "agent_started" in event_types
    assert "policy_allowed" in event_types
