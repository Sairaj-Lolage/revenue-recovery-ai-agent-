"""
backend/app/services/payment_service.py
========================================
Mock payment and recovery simulation service.

Architecture:
    API Route / Agent Tool
        ↓
    PaymentService   ← you are here
        ↓
    Database (SQLAlchemy)

IMPORTANT:
- The agent NEVER touches models/DB directly.
- ``recovery_scenario`` is NEVER returned in any public result object.
- All mock behaviour is deterministic so tests are predictable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import (
    Customer,
    Payment,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_SUCCESS,
)

# ---------------------------------------------------------------------------
# Scenario constants (internal only — never surfaced to callers)
# ---------------------------------------------------------------------------

_SCENARIO_EASY_RECOVERY         = "EASY_RECOVERY"
_SCENARIO_PAYMENT_LINK_RECOVERY = "PAYMENT_LINK_RECOVERY"
_SCENARIO_REPEATED_FAILURE      = "REPEATED_FAILURE"
_SCENARIO_HIGH_VALUE            = "HIGH_VALUE"
_SCENARIO_OPTED_OUT             = "OPTED_OUT"
_SCENARIO_UNRECOVERABLE         = "UNRECOVERABLE"


# ---------------------------------------------------------------------------
# Result dataclasses (agent-safe — no recovery_scenario)
# ---------------------------------------------------------------------------

@dataclass
class PaymentInfo:
    """Agent-safe view of a payment record."""
    payment_id:    int
    customer_id:   int
    amount_paise:  int
    currency:      str
    status:        str
    failure_reason: Optional[str]
    attempt_count: int
    created_at:    datetime


@dataclass
class CustomerHistory:
    """Agent-safe view of a customer record."""
    customer_id:         int
    name:                str
    segment:             Optional[str]
    total_paid_paise:    int
    successful_payments: int
    failed_payments:     int
    opted_out:           bool


@dataclass
class RetryResult:
    success:               bool
    payment_id:            int
    amount_recovered_paise: int
    status:                str          # "success" | "failed" | "blocked"
    message:               str


@dataclass
class PaymentLinkResult:
    success:      bool
    payment_id:   int
    payment_link: Optional[str]
    message:      str


@dataclass
class MessageResult:
    success:     bool
    customer_id: int
    channel:     str
    message_id:  Optional[str]
    message:     str


# ---------------------------------------------------------------------------
# PaymentService
# ---------------------------------------------------------------------------

class PaymentService:
    """
    Provides all payment-related operations for the recovery agent.

    Receives a SQLAlchemy ``Session`` so it can be used inside
    FastAPI dependency injection or in standalone scripts/tests.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Lookups ──────────────────────────────────────────────────────────────

    def get_payment(self, payment_id: int) -> Optional[PaymentInfo]:
        """
        Return agent-safe payment information.
        ``recovery_scenario`` is deliberately excluded.
        """
        p: Optional[Payment] = self._db.get(Payment, payment_id)
        if p is None:
            return None
        return PaymentInfo(
            payment_id=p.id,
            customer_id=p.customer_id,
            amount_paise=p.amount_paise,
            currency=p.currency,
            status=p.status,
            failure_reason=p.failure_reason,
            attempt_count=p.attempt_count,
            created_at=p.created_at,
        )

    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """Return the raw ORM Customer object (internal use)."""
        return self._db.get(Customer, customer_id)

    def get_customer_history(self, customer_id: int) -> Optional[CustomerHistory]:
        """Return agent-safe customer history."""
        c: Optional[Customer] = self._db.get(Customer, customer_id)
        if c is None:
            return None
        return CustomerHistory(
            customer_id=c.id,
            name=c.name,
            segment=c.segment,
            total_paid_paise=c.total_paid_paise,
            successful_payments=c.successful_payments,
            failed_payments=c.failed_payments,
            opted_out=c.opted_out,
        )

    # ── Retry ────────────────────────────────────────────────────────────────

    def retry_payment(self, payment_id: int) -> RetryResult:
        """
        Simulate a payment retry.

        Behaviour is driven by the hidden ``recovery_scenario`` field —
        the agent never sees this field; it only receives the RetryResult.
        """
        p: Optional[Payment] = self._db.get(Payment, payment_id)

        if p is None:
            return RetryResult(
                success=False,
                payment_id=payment_id,
                amount_recovered_paise=0,
                status="failed",
                message=f"Payment {payment_id} not found",
            )

        if p.status == PAYMENT_STATUS_SUCCESS:
            return RetryResult(
                success=False,
                payment_id=payment_id,
                amount_recovered_paise=0,
                status="already_successful",
                message="Payment is already successful; no retry needed",
            )

        # Opted-out customers are never retried automatically
        customer: Optional[Customer] = self._db.get(Customer, p.customer_id)
        if customer and customer.opted_out:
            return RetryResult(
                success=False,
                payment_id=payment_id,
                amount_recovered_paise=0,
                status="blocked",
                message="Customer opted out of automated recovery",
            )

        # Increment attempt count regardless of outcome
        p.attempt_count += 1
        p.updated_at = datetime.now(timezone.utc)

        # --- Scenario-driven simulation (internal; never surfaced) -----------
        scenario = p.recovery_scenario  # hidden field

        if scenario == _SCENARIO_EASY_RECOVERY:
            # First retry succeeds
            p.status = PAYMENT_STATUS_SUCCESS
            self._db.commit()
            return RetryResult(
                success=True,
                payment_id=payment_id,
                amount_recovered_paise=p.amount_paise,
                status="success",
                message="Payment recovered via automatic retry",
            )

        # All other scenarios: retry fails
        self._db.commit()
        return RetryResult(
            success=False,
            payment_id=payment_id,
            amount_recovered_paise=0,
            status="failed",
            message="Retry failed; payment remains unrecovered",
        )

    # ── Payment link ─────────────────────────────────────────────────────────

    def create_payment_link(self, payment_id: int) -> PaymentLinkResult:
        """
        Generate a deterministic mock payment link.
        Does NOT mark the payment as recovered.
        """
        p: Optional[Payment] = self._db.get(Payment, payment_id)
        if p is None:
            return PaymentLinkResult(
                success=False,
                payment_id=payment_id,
                payment_link=None,
                message=f"Payment {payment_id} not found",
            )

        if p.status == PAYMENT_STATUS_SUCCESS:
            return PaymentLinkResult(
                success=False,
                payment_id=payment_id,
                payment_link=None,
                message="Payment is already successful; no link needed",
            )

        customer = self._db.get(Customer, p.customer_id)
        if customer and customer.opted_out:
            return PaymentLinkResult(
                success=False,
                payment_id=payment_id,
                payment_link=None,
                message="Customer opted out of automated recovery",
            )

        link = f"https://pay.example.com/recover/pay_{payment_id}"
        return PaymentLinkResult(
            success=True,
            payment_id=payment_id,
            payment_link=link,
            message="Payment link created successfully",
        )

    def complete_payment_via_link(self, payment_id: int) -> RetryResult:
        """
        Simulate a customer clicking the payment link and completing payment.

        Behaviour is also driven by the hidden ``recovery_scenario``; the
        caller receives only a RetryResult.
        """
        p: Optional[Payment] = self._db.get(Payment, payment_id)

        if p is None:
            return RetryResult(
                success=False,
                payment_id=payment_id,
                amount_recovered_paise=0,
                status="failed",
                message=f"Payment {payment_id} not found",
            )

        if p.status == PAYMENT_STATUS_SUCCESS:
            return RetryResult(
                success=False,
                payment_id=payment_id,
                amount_recovered_paise=0,
                status="already_successful",
                message="Payment is already successful",
            )

        customer = self._db.get(Customer, p.customer_id)
        if customer and customer.opted_out:
            return RetryResult(
                success=False,
                payment_id=payment_id,
                amount_recovered_paise=0,
                status="blocked",
                message="Customer opted out of automated recovery",
            )

        scenario = p.recovery_scenario  # internal only

        # Scenarios that succeed via payment link
        if scenario in (
            _SCENARIO_PAYMENT_LINK_RECOVERY,
            _SCENARIO_HIGH_VALUE,
            _SCENARIO_EASY_RECOVERY,
        ):
            p.status = PAYMENT_STATUS_SUCCESS
            p.updated_at = datetime.now(timezone.utc)
            self._db.commit()
            return RetryResult(
                success=True,
                payment_id=payment_id,
                amount_recovered_paise=p.amount_paise,
                status="success",
                message="Payment recovered via payment link",
            )

        # Scenarios that fail via payment link
        return RetryResult(
            success=False,
            payment_id=payment_id,
            amount_recovered_paise=0,
            status="failed",
            message="Payment link completion failed; payment unrecoverable",
        )

    # ── Messaging ─────────────────────────────────────────────────────────────

    def send_recovery_message(
        self,
        customer_id: int,
        message: str,
        payment_link: Optional[str] = None,
    ) -> MessageResult:
        """
        Simulate sending a recovery message (email/SMS/WhatsApp mock).
        No real messages are sent.
        """
        customer: Optional[Customer] = self._db.get(Customer, customer_id)

        if customer is None:
            return MessageResult(
                success=False,
                customer_id=customer_id,
                channel="mock",
                message_id=None,
                message="Customer not found",
            )

        if customer.opted_out:
            return MessageResult(
                success=False,
                customer_id=customer_id,
                channel="mock",
                message_id=None,
                message="Customer opted out; message not sent",
            )

        # Deterministic mock message ID based on customer + content hash
        message_id = f"msg_{customer_id}_{abs(hash(message)) % 100_000:05d}"

        full_message = message
        if payment_link:
            full_message = f"{message}\nPayment link: {payment_link}"

        return MessageResult(
            success=True,
            customer_id=customer_id,
            channel="mock",
            message_id=message_id,
            message=full_message,
        )
