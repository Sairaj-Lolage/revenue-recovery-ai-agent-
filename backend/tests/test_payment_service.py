"""
Tests for PaymentService (backend/tests/test_payment_service.py).

Uses an isolated in-memory SQLite DB seeded with the standard
deterministic dataset.  The development database is never touched.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.database import Base
from app.db.models import Customer, Payment, PAYMENT_STATUS_SUCCESS, PAYMENT_STATUS_FAILED
from app.db.seed import seed
from app.services.payment_service import PaymentService


# ---------------------------------------------------------------------------
# Shared fixture: one seeded in-memory DB per module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    _Session = sessionmaker(bind=engine)
    session = _Session()
    seed(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="module")
def svc(db: Session) -> PaymentService:
    return PaymentService(db)


# ---------------------------------------------------------------------------
# Helper: find first payment with a specific recovery scenario
# ---------------------------------------------------------------------------

def _payment_with_scenario(db: Session, scenario: str) -> Payment:
    p = db.query(Payment).filter(Payment.recovery_scenario == scenario).first()
    assert p is not None, f"No payment with scenario={scenario!r} found in seed data"
    return p


def _successful_payment(db: Session) -> Payment:
    p = db.query(Payment).filter(Payment.status == PAYMENT_STATUS_SUCCESS).first()
    assert p is not None
    return p


# ---------------------------------------------------------------------------
# 1. get_payment returns safe information
# ---------------------------------------------------------------------------

def test_get_payment_returns_payment_info(svc: PaymentService, db: Session) -> None:
    p = _payment_with_scenario(db, "EASY_RECOVERY")
    info = svc.get_payment(p.id)
    assert info is not None
    assert info.payment_id == p.id
    assert info.customer_id == p.customer_id
    assert info.amount_paise == p.amount_paise
    assert info.currency == "INR"
    assert info.status == PAYMENT_STATUS_FAILED
    assert info.attempt_count >= 1


# ---------------------------------------------------------------------------
# 2. get_payment must NOT expose recovery_scenario
# ---------------------------------------------------------------------------

def test_get_payment_does_not_expose_recovery_scenario(svc: PaymentService, db: Session) -> None:
    p = _payment_with_scenario(db, "HIGH_VALUE")
    info = svc.get_payment(p.id)
    assert info is not None
    # The result object must not carry recovery_scenario
    assert not hasattr(info, "recovery_scenario"), (
        "PaymentInfo must not expose recovery_scenario"
    )
    # Double-check via dict representation too
    info_dict = vars(info)
    assert "recovery_scenario" not in info_dict


# ---------------------------------------------------------------------------
# 3. get_customer_history returns correct fields
# ---------------------------------------------------------------------------

def test_get_customer_history_returns_correct_fields(svc: PaymentService, db: Session) -> None:
    customer = db.query(Customer).first()
    history = svc.get_customer_history(customer.id)
    assert history is not None
    assert history.customer_id == customer.id
    assert history.name == customer.name
    assert history.segment == customer.segment
    assert history.total_paid_paise == customer.total_paid_paise
    assert history.successful_payments == customer.successful_payments
    assert history.failed_payments == customer.failed_payments
    assert history.opted_out == customer.opted_out
    # No recovery_scenario on customer history
    assert not hasattr(history, "recovery_scenario")


# ---------------------------------------------------------------------------
# 4. EASY_RECOVERY retry succeeds
# ---------------------------------------------------------------------------

def test_easy_recovery_retry_succeeds(db: Session) -> None:
    """Each EASY_RECOVERY payment should succeed on the first retry."""
    # Use a fresh engine per test to avoid cross-test state mutation
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    S = sessionmaker(bind=eng)
    session = S()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "EASY_RECOVERY")

    result = svc.retry_payment(p.id)
    assert result.success is True
    assert result.status == "success"
    assert result.amount_recovered_paise == p.amount_paise
    assert result.amount_recovered_paise > 0

    session.close()
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


# ---------------------------------------------------------------------------
# 5. PAYMENT_LINK_RECOVERY retry fails
# ---------------------------------------------------------------------------

def test_payment_link_recovery_retry_fails(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "PAYMENT_LINK_RECOVERY")
    result = svc.retry_payment(p.id)
    assert result.success is False
    assert result.status == "failed"
    assert result.amount_recovered_paise == 0

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 6. REPEATED_FAILURE retry fails
# ---------------------------------------------------------------------------

def test_repeated_failure_retry_fails(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "REPEATED_FAILURE")
    result = svc.retry_payment(p.id)
    assert result.success is False
    assert result.status == "failed"

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 7. UNRECOVERABLE retry fails
# ---------------------------------------------------------------------------

def test_unrecoverable_retry_fails(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "UNRECOVERABLE")
    result = svc.retry_payment(p.id)
    assert result.success is False
    assert result.status == "failed"

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 8. OPTED_OUT retry is blocked
# ---------------------------------------------------------------------------

def test_opted_out_retry_is_blocked(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "OPTED_OUT")
    result = svc.retry_payment(p.id)
    assert result.success is False
    assert result.status == "blocked"
    assert "opted out" in result.message.lower()

    # Payment status must NOT change
    session.refresh(p)
    assert p.status == PAYMENT_STATUS_FAILED

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 9. Successful payment cannot be retried
# ---------------------------------------------------------------------------

def test_successful_payment_cannot_be_retried(db: Session) -> None:
    p = _successful_payment(db)
    svc = PaymentService(db)
    result = svc.retry_payment(p.id)
    assert result.success is False
    assert result.status == "already_successful"


# ---------------------------------------------------------------------------
# 10. Retry increments attempt_count
# ---------------------------------------------------------------------------

def test_retry_increments_attempt_count(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    # Use PAYMENT_LINK_RECOVERY so it always fails (non-mutating to scenario)
    p = _payment_with_scenario(session, "PAYMENT_LINK_RECOVERY")
    before = p.attempt_count
    svc.retry_payment(p.id)
    session.refresh(p)
    assert p.attempt_count == before + 1

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 11. Successful retry changes payment status to success
# ---------------------------------------------------------------------------

def test_successful_retry_changes_payment_status(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "EASY_RECOVERY")
    assert p.status == PAYMENT_STATUS_FAILED
    svc.retry_payment(p.id)
    session.refresh(p)
    assert p.status == PAYMENT_STATUS_SUCCESS

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 12. Payment link creation works
# ---------------------------------------------------------------------------

def test_payment_link_creation_works(db: Session) -> None:
    p = _payment_with_scenario(db, "PAYMENT_LINK_RECOVERY")
    svc = PaymentService(db)
    result = svc.create_payment_link(p.id)
    assert result.success is True
    assert result.payment_link is not None
    assert str(p.id) in result.payment_link
    assert result.payment_link.startswith("https://")


# ---------------------------------------------------------------------------
# 13. Payment link creation does NOT recover payment
# ---------------------------------------------------------------------------

def test_payment_link_creation_does_not_recover_payment(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "PAYMENT_LINK_RECOVERY")
    svc.create_payment_link(p.id)
    session.refresh(p)
    # Status must still be failed after link creation
    assert p.status == PAYMENT_STATUS_FAILED

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 14. PAYMENT_LINK_RECOVERY completes successfully via payment link
# ---------------------------------------------------------------------------

def test_payment_link_recovery_completes_via_link(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "PAYMENT_LINK_RECOVERY")
    result = svc.complete_payment_via_link(p.id)
    assert result.success is True
    assert result.status == "success"
    assert result.amount_recovered_paise == p.amount_paise

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 15. UNRECOVERABLE payment link completion fails
# ---------------------------------------------------------------------------

def test_unrecoverable_payment_link_completion_fails(db: Session) -> None:
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    session = sessionmaker(bind=eng)()
    seed(session)

    svc = PaymentService(session)
    p = _payment_with_scenario(session, "UNRECOVERABLE")
    result = svc.complete_payment_via_link(p.id)
    assert result.success is False
    assert result.status == "failed"

    session.close(); Base.metadata.drop_all(bind=eng); eng.dispose()


# ---------------------------------------------------------------------------
# 16. OPTED_OUT customer cannot receive recovery message
# ---------------------------------------------------------------------------

def test_opted_out_customer_cannot_receive_message(db: Session) -> None:
    opted_out_customer = (
        db.query(Customer).filter(Customer.opted_out.is_(True)).first()
    )
    assert opted_out_customer is not None
    svc = PaymentService(db)
    result = svc.send_recovery_message(opted_out_customer.id, "Please complete your payment")
    assert result.success is False
    assert "opted out" in result.message.lower()
    assert result.message_id is None


# ---------------------------------------------------------------------------
# 17. Normal customer can receive mock recovery message
# ---------------------------------------------------------------------------

def test_normal_customer_can_receive_mock_message(db: Session) -> None:
    normal_customer = (
        db.query(Customer).filter(Customer.opted_out.is_(False)).first()
    )
    assert normal_customer is not None
    svc = PaymentService(db)
    result = svc.send_recovery_message(
        normal_customer.id,
        "Your payment failed. Please retry.",
        payment_link="https://pay.example.com/recover/pay_1",
    )
    assert result.success is True
    assert result.channel == "mock"
    assert result.message_id is not None
    assert result.message_id.startswith("msg_")
    assert "https://pay.example.com" in result.message
