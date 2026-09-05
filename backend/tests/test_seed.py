"""
Tests for the synthetic data seed (backend/tests/test_seed.py).

Uses an in-memory SQLite DB; never touches the development database.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.database import Base
from app.db.models import Customer, Payment, PAYMENT_STATUS_SUCCESS, PAYMENT_STATUS_FAILED
from app.db.seed import (
    FAILURE_REASONS,
    TARGET_CUSTOMERS,
    TARGET_PAYMENTS,
    seed,
)

# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def seeded_db():
    """Return a seeded in-memory DB session (created once for the module)."""
    _engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=_engine)
    _Session = sessionmaker(bind=_engine)
    db = _Session()
    seed(db)
    yield db
    db.close()
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_seed_creates_50_customers(seeded_db: Session) -> None:
    """Seed must produce exactly 50 customers."""
    count = seeded_db.query(Customer).count()
    assert count == TARGET_CUSTOMERS == 50


def test_seed_creates_150_payments(seeded_db: Session) -> None:
    """Seed must produce exactly 150 payments."""
    count = seeded_db.query(Payment).count()
    assert count == TARGET_PAYMENTS == 150


def test_seed_is_deterministic(seeded_db: Session) -> None:
    """Running seed twice produces the same dataset."""
    engine2 = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine2)
    Session2 = sessionmaker(bind=engine2)
    db2 = Session2()
    seed(db2)

    emails_1 = sorted(r.email for r in seeded_db.query(Customer).all())
    emails_2 = sorted(r.email for r in db2.query(Customer).all())
    assert emails_1 == emails_2

    amounts_1 = sorted(p.amount_paise for p in seeded_db.query(Payment).all())
    amounts_2 = sorted(p.amount_paise for p in db2.query(Payment).all())
    assert amounts_1 == amounts_2

    db2.close()
    Base.metadata.drop_all(bind=engine2)
    engine2.dispose()


def test_both_payment_statuses_exist(seeded_db: Session) -> None:
    """Dataset must contain both successful and failed payments."""
    statuses = {r.status for r in seeded_db.query(Payment).all()}
    assert PAYMENT_STATUS_SUCCESS in statuses
    assert PAYMENT_STATUS_FAILED in statuses


def test_all_failure_reasons_present(seeded_db: Session) -> None:
    """Every defined failure reason must appear at least once."""
    reasons = {
        p.failure_reason
        for p in seeded_db.query(Payment).filter(Payment.status == PAYMENT_STATUS_FAILED).all()
        if p.failure_reason is not None
    }
    for required in FAILURE_REASONS:
        assert required in reasons, f"Missing failure reason: {required}"


def test_all_recovery_scenarios_present(seeded_db: Session) -> None:
    """All six recovery scenarios must be represented in the failed payments."""
    required = {
        "EASY_RECOVERY",
        "PAYMENT_LINK_RECOVERY",
        "REPEATED_FAILURE",
        "HIGH_VALUE",
        "OPTED_OUT",
        "UNRECOVERABLE",
    }
    found = {
        p.recovery_scenario
        for p in seeded_db.query(Payment).filter(Payment.status == PAYMENT_STATUS_FAILED).all()
        if p.recovery_scenario is not None
    }
    assert required == found, f"Missing scenarios: {required - found}"


def test_failed_payments_have_positive_amount(seeded_db: Session) -> None:
    """Every failed payment must have a positive paise amount."""
    failed = seeded_db.query(Payment).filter(Payment.status == PAYMENT_STATUS_FAILED).all()
    assert len(failed) > 0
    for p in failed:
        assert p.amount_paise > 0, f"Payment {p.id} has non-positive amount"


def test_payment_customer_relationships_valid(seeded_db: Session) -> None:
    """Every payment must reference an existing customer."""
    customer_ids = {c.id for c in seeded_db.query(Customer).all()}
    for p in seeded_db.query(Payment).all():
        assert p.customer_id in customer_ids, f"Payment {p.id} has orphan customer_id"
        assert p.customer is not None


def test_revenue_at_risk_is_calculable(seeded_db: Session) -> None:
    """Sum of failed payment amounts must be a positive integer."""
    failed = seeded_db.query(Payment).filter(Payment.status == PAYMENT_STATUS_FAILED).all()
    at_risk = sum(p.amount_paise for p in failed)
    assert isinstance(at_risk, int)
    assert at_risk > 0


def test_opted_out_customers_have_opted_out_scenario(seeded_db: Session) -> None:
    """Payments tagged OPTED_OUT must belong to customers with opted_out=True."""
    opted_payments = (
        seeded_db.query(Payment)
        .filter(Payment.recovery_scenario == "OPTED_OUT")
        .all()
    )
    assert len(opted_payments) > 0
    for p in opted_payments:
        assert p.customer.opted_out is True, (
            f"Payment {p.id} is OPTED_OUT scenario but customer.opted_out is False"
        )


def test_high_value_payments_exceed_threshold(seeded_db: Session) -> None:
    """All HIGH_VALUE scenario payments must be above the auto-recovery threshold."""
    from app.db.seed import AUTO_RECOVERY_THRESHOLD_PAISE
    hv = (
        seeded_db.query(Payment)
        .filter(Payment.recovery_scenario == "HIGH_VALUE")
        .all()
    )
    assert len(hv) > 0
    for p in hv:
        assert p.amount_paise >= AUTO_RECOVERY_THRESHOLD_PAISE, (
            f"HIGH_VALUE payment {p.id} amount {p.amount_paise} is below threshold"
        )


def test_repeated_failure_has_multiple_attempts(seeded_db: Session) -> None:
    """REPEATED_FAILURE payments must have attempt_count >= 2."""
    rf = (
        seeded_db.query(Payment)
        .filter(Payment.recovery_scenario == "REPEATED_FAILURE")
        .all()
    )
    assert len(rf) > 0
    for p in rf:
        assert p.attempt_count >= 2, (
            f"REPEATED_FAILURE payment {p.id} has attempt_count={p.attempt_count}"
        )


def test_successful_payments_have_no_scenario(seeded_db: Session) -> None:
    """Successful payments must not carry a recovery scenario tag."""
    successful = (
        seeded_db.query(Payment)
        .filter(Payment.status == PAYMENT_STATUS_SUCCESS)
        .all()
    )
    assert len(successful) > 0
    for p in successful:
        assert p.recovery_scenario is None, (
            f"Successful payment {p.id} unexpectedly has scenario {p.recovery_scenario}"
        )
