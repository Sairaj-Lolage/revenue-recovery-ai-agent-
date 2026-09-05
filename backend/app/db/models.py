"""
SQLAlchemy 2.x ORM models for the Revenue Recovery Agent.

Money is stored as integer paise (1 INR = 100 paise) to avoid
floating-point rounding errors on currency arithmetic.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Money stored as integer paise (INR)
    total_paid_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    successful_payments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_payments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="customer")
    recovery_cases: Mapped[list["RecoveryCase"]] = relationship(
        "RecoveryCase", back_populates="customer"
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email={self.email!r}>"


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

# Simple string constants — no enum overhead for an MVP.
PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_SUCCESS = "success"
PAYMENT_STATUS_FAILED = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # "pending" | "success" | "failed"
    status: Mapped[str] = mapped_column(
        String(20), default=PAYMENT_STATUS_PENDING, nullable=False, index=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Synthetic evaluation metadata — NOT exposed to the agent.
    # Possible values: EASY_RECOVERY | PAYMENT_LINK_RECOVERY | REPEATED_FAILURE
    #                  HIGH_VALUE | OPTED_OUT | UNRECOVERABLE | None (successful payments)
    recovery_scenario: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="payments")
    recovery_cases: Mapped[list["RecoveryCase"]] = relationship(
        "RecoveryCase", back_populates="payment"
    )

    def __repr__(self) -> str:
        return f"<Payment id={self.id} status={self.status!r} amount_paise={self.amount_paise}>"


# ---------------------------------------------------------------------------
# RecoveryCase
# ---------------------------------------------------------------------------

CASE_STATUS_OPEN = "OPEN"
CASE_STATUS_IN_PROGRESS = "IN_PROGRESS"
CASE_STATUS_RECOVERED = "RECOVERED"
CASE_STATUS_ESCALATED = "ESCALATED"
CASE_STATUS_STOPPED = "STOPPED"


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("payments.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )

    amount_at_risk_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0–100

    # "OPEN" | "IN_PROGRESS" | "RECOVERED" | "ESCALATED" | "STOPPED"
    status: Mapped[str] = mapped_column(
        String(20), default=CASE_STATUS_OPEN, nullable=False, index=True
    )
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_recovered_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="recovery_cases")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="recovery_cases")
    actions: Mapped[list["RecoveryAction"]] = relationship(
        "RecoveryAction", back_populates="recovery_case"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="recovery_case"
    )

    def __repr__(self) -> str:
        return f"<RecoveryCase id={self.id} status={self.status!r}>"


# ---------------------------------------------------------------------------
# RecoveryAction
# ---------------------------------------------------------------------------

ACTION_TYPE_RETRY_PAYMENT = "retry_payment"
ACTION_TYPE_CREATE_PAYMENT_LINK = "create_payment_link"
ACTION_TYPE_SEND_RECOVERY_MESSAGE = "send_recovery_message"
ACTION_TYPE_ESCALATE = "escalate"
ACTION_TYPE_STOP = "stop"


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recovery_case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recovery_cases.id"), nullable=False, index=True
    )

    # See ACTION_TYPE_* constants above
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_recovered_paise: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    recovery_case: Mapped["RecoveryCase"] = relationship(
        "RecoveryCase", back_populates="actions"
    )

    def __repr__(self) -> str:
        return f"<RecoveryAction id={self.id} type={self.action_type!r}>"


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

# event_type constants (non-exhaustive — agent can emit custom events)
EVENT_CASE_CREATED = "CASE_CREATED"
EVENT_RISK_DETECTED = "RISK_DETECTED"
EVENT_DIAGNOSIS_COMPLETED = "DIAGNOSIS_COMPLETED"
EVENT_ACTION_PROPOSED = "ACTION_PROPOSED"
EVENT_GUARDRAIL_CHECKED = "GUARDRAIL_CHECKED"
EVENT_ACTION_EXECUTED = "ACTION_EXECUTED"
EVENT_PAYMENT_RECOVERED = "PAYMENT_RECOVERED"
EVENT_ESCALATED = "ESCALATED"
EVENT_WORKFLOW_STOPPED = "WORKFLOW_STOPPED"

# actor constants
ACTOR_AGENT = "agent"
ACTOR_SYSTEM = "system"
ACTOR_GUARDRAIL = "guardrail"
ACTOR_TOOL = "tool"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recovery_case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recovery_cases.id"), nullable=False, index=True
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    recovery_case: Mapped["RecoveryCase"] = relationship(
        "RecoveryCase", back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} event={self.event_type!r} actor={self.actor!r}>"


# ---------------------------------------------------------------------------
# Runtime policy configuration (single local deployment record)
# ---------------------------------------------------------------------------


class RecoveryPolicyConfig(Base):
    """Persisted, operator-configurable limits for the local recovery agent."""

    __tablename__ = "recovery_policy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    max_retry_attempts: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    high_value_threshold_paise: Mapped[int] = mapped_column(BigInteger, default=1_000_000, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
