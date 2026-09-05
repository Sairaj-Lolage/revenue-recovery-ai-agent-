"""
Tests for database initialisation, models, and relationships.

Uses a temporary in-memory SQLite database so the development DB is
never touched during test runs.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.database import Base
from app.db.models import (
    AuditLog,
    Customer,
    Payment,
    RecoveryAction,
    RecoveryCase,
    # Status / type constants
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_SUCCESS,
    CASE_STATUS_OPEN,
    CASE_STATUS_RECOVERED,
    ACTION_TYPE_RETRY_PAYMENT,
    ACTION_TYPE_CREATE_PAYMENT_LINK,
    EVENT_CASE_CREATED,
    EVENT_PAYMENT_RECOVERED,
    ACTOR_AGENT,
    ACTOR_SYSTEM,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite engine and all tables once per module."""
    _engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


@pytest.fixture
def db(engine) -> Session:
    """Provide a fresh, rolled-back session for every test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_customer(db: Session, *, email: str = "alice@example.com") -> Customer:
    customer = Customer(
        name="Alice Kumar",
        email=email,
        phone="+919999999999",
        segment="premium",
        total_paid_paise=500_000,  # ₹5,000 in paise
        successful_payments=10,
        failed_payments=1,
        opted_out=False,
    )
    db.add(customer)
    db.flush()
    return customer


def _make_payment(db: Session, customer: Customer) -> Payment:
    payment = Payment(
        customer_id=customer.id,
        amount_paise=99_900,  # ₹999
        currency="INR",
        status=PAYMENT_STATUS_FAILED,
        failure_reason="insufficient_funds",
        attempt_count=1,
    )
    db.add(payment)
    db.flush()
    return payment


def _make_case(db: Session, payment: Payment, customer: Customer) -> RecoveryCase:
    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        amount_at_risk_paise=payment.amount_paise,
        risk_score=75,
        status=CASE_STATUS_OPEN,
        current_step="diagnosis",
        attempt_count=0,
        amount_recovered_paise=0,
    )
    db.add(case)
    db.flush()
    return case


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_database_initialises(engine) -> None:
    """All expected tables exist after init."""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "customers" in tables
    assert "payments" in tables
    assert "recovery_cases" in tables
    assert "recovery_actions" in tables
    assert "audit_logs" in tables


def test_customer_insert(db: Session) -> None:
    """A Customer row can be inserted and retrieved."""
    customer = _make_customer(db)
    assert customer.id is not None
    fetched = db.get(Customer, customer.id)
    assert fetched is not None
    assert fetched.email == "alice@example.com"
    assert fetched.opted_out is False


def test_payment_references_customer(db: Session) -> None:
    """A Payment can reference a Customer via FK and relationship."""
    customer = _make_customer(db)
    payment = _make_payment(db, customer)

    assert payment.id is not None
    assert payment.customer_id == customer.id
    assert payment.customer.email == customer.email


def test_recovery_case_references_payment_and_customer(db: Session) -> None:
    """A RecoveryCase links both Payment and Customer."""
    customer = _make_customer(db)
    payment = _make_payment(db, customer)
    case = _make_case(db, payment, customer)

    assert case.id is not None
    assert case.payment_id == payment.id
    assert case.customer_id == customer.id
    assert case.payment.amount_paise == 99_900
    assert case.customer.name == "Alice Kumar"


def test_recovery_action_references_case(db: Session) -> None:
    """A RecoveryAction references its RecoveryCase."""
    customer = _make_customer(db)
    payment = _make_payment(db, customer)
    case = _make_case(db, payment, customer)

    action = RecoveryAction(
        recovery_case_id=case.id,
        action_type=ACTION_TYPE_RETRY_PAYMENT,
        reason="First automated retry",
        approved=True,
        result="payment_initiated",
        amount_recovered_paise=0,
    )
    db.add(action)
    db.flush()

    assert action.id is not None
    assert action.recovery_case_id == case.id
    assert action.recovery_case.status == CASE_STATUS_OPEN


def test_audit_log_references_case(db: Session) -> None:
    """An AuditLog row references its RecoveryCase."""
    customer = _make_customer(db)
    payment = _make_payment(db, customer)
    case = _make_case(db, payment, customer)

    log = AuditLog(
        recovery_case_id=case.id,
        event_type=EVENT_CASE_CREATED,
        actor=ACTOR_SYSTEM,
        details='{"triggered_by": "payment_webhook"}',
    )
    db.add(log)
    db.flush()

    assert log.id is not None
    assert log.recovery_case.id == case.id


def test_relationships_via_back_population(db: Session) -> None:
    """Verify back-populated collections work in both directions."""
    customer = _make_customer(db)
    payment = _make_payment(db, customer)
    case = _make_case(db, payment, customer)

    action1 = RecoveryAction(
        recovery_case_id=case.id,
        action_type=ACTION_TYPE_RETRY_PAYMENT,
        approved=True,
    )
    action2 = RecoveryAction(
        recovery_case_id=case.id,
        action_type=ACTION_TYPE_CREATE_PAYMENT_LINK,
        approved=False,
    )
    db.add_all([action1, action2])

    log = AuditLog(
        recovery_case_id=case.id,
        event_type=EVENT_PAYMENT_RECOVERED,
        actor=ACTOR_AGENT,
    )
    db.add(log)
    db.flush()

    db.refresh(case)
    assert len(case.actions) == 2
    assert len(case.audit_logs) == 1
    assert len(customer.payments) == 1
    assert len(customer.recovery_cases) == 1


def test_money_stored_as_integer_paise(db: Session) -> None:
    """Money fields persist as integers; no floating-point coercion."""
    customer = _make_customer(db)
    customer.total_paid_paise = 1_234_567  # ₹12,345.67

    payment = Payment(
        customer_id=customer.id,
        amount_paise=49_900,  # ₹499
        currency="INR",
        status=PAYMENT_STATUS_FAILED,
        attempt_count=0,
    )
    db.add(payment)
    db.flush()

    fetched = db.get(Payment, payment.id)
    assert isinstance(fetched.amount_paise, int)
    assert fetched.amount_paise == 49_900

    fetched_customer = db.get(Customer, customer.id)
    assert isinstance(fetched_customer.total_paid_paise, int)
    assert fetched_customer.total_paid_paise == 1_234_567


def test_recovery_case_status_transition(db: Session) -> None:
    """Status field can be updated to any valid constant."""
    customer = _make_customer(db)
    payment = _make_payment(db, customer)
    case = _make_case(db, payment, customer)

    assert case.status == CASE_STATUS_OPEN

    case.status = CASE_STATUS_RECOVERED
    case.amount_recovered_paise = payment.amount_paise
    db.flush()

    fetched = db.get(RecoveryCase, case.id)
    assert fetched.status == CASE_STATUS_RECOVERED
    assert fetched.amount_recovered_paise == 99_900
