"""
backend/app/api/router.py
=========================
FastAPI read endpoints & event simulation helper routes for the Revenue Recovery Frontend.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import (
    Customer,
    Payment,
    RecoveryCase,
    RecoveryAction,
    AuditLog,
    RecoveryPolicyConfig,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_SUCCESS,
    CASE_STATUS_OPEN,
    CASE_STATUS_IN_PROGRESS,
    CASE_STATUS_RECOVERED,
    CASE_STATUS_ESCALATED,
    CASE_STATUS_STOPPED,
)
from app.events.simulator import simulate_payment_completion
from app.agent.risk import calculate_risk_score

router = APIRouter(prefix="/api", tags=["Dashboard & Read APIs"])


class PolicyConfigUpdate(BaseModel):
    max_retry_attempts: int = Field(ge=1, le=3)
    high_value_threshold_paise: int = Field(ge=1)


def _policy_config_response(config: RecoveryPolicyConfig) -> Dict[str, Any]:
    return {
        "max_retry_attempts": config.max_retry_attempts,
        "high_value_threshold_paise": config.high_value_threshold_paise,
        "strict_opt_out": True,
        "auto_escalate_delay_hours": None,
    }


def _get_or_create_policy_config(db: Session) -> RecoveryPolicyConfig:
    config = db.get(RecoveryPolicyConfig, 1)
    if not config:
        config = RecoveryPolicyConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.get("/settings/policy")
def get_policy_config(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return the persisted policy limits used by future recovery runs."""
    return _policy_config_response(_get_or_create_policy_config(db))


@router.put("/settings/policy")
def update_policy_config(
    update: PolicyConfigUpdate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update operator-configurable recovery limits for future agent runs."""
    config = _get_or_create_policy_config(db)
    config.max_retry_attempts = update.max_retry_attempts
    config.high_value_threshold_paise = update.high_value_threshold_paise
    db.commit()
    db.refresh(config)
    return _policy_config_response(config)


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------

@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Calculate aggregate financial and operational KPI metrics."""
    failed_payments = db.query(Payment).filter(Payment.status == PAYMENT_STATUS_FAILED).all()
    failed_count = len(failed_payments)
    amount_at_risk_paise = sum(p.amount_paise for p in failed_payments)

    cases = db.query(RecoveryCase).all()
    recovered_amount_paise = sum(c.amount_recovered_paise or 0 for c in cases)
    in_progress_count = sum(1 for c in cases if c.status == CASE_STATUS_IN_PROGRESS)
    escalated_count = sum(1 for c in cases if c.status == CASE_STATUS_ESCALATED)
    stopped_count = sum(1 for c in cases if c.status == CASE_STATUS_STOPPED)
    recovered_count = sum(1 for c in cases if c.status == CASE_STATUS_RECOVERED)

    total_evaluated = len(cases)
    recovery_rate_percent = (
        round((recovered_count / total_evaluated) * 100, 1) if total_evaluated > 0 else 0.0
    )

    # Calculate recoveries today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_recoveries_today = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.status == CASE_STATUS_RECOVERED)
        .filter(RecoveryCase.updated_at >= today_start)
        .count()
    )

    return {
        "amountAtRiskPaise": amount_at_risk_paise,
        "recoveredAmountPaise": recovered_amount_paise,
        "failedCount": failed_count,
        "recoveryRatePercent": recovery_rate_percent,
        "inProgressCount": in_progress_count,
        "escalatedCount": escalated_count,
        "stoppedCount": stopped_count,
        "totalRecoveriesToday": total_recoveries_today,
    }


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

@router.get("/payments")
def get_payments(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return all payments with customer details and recovery case status."""
    payments = db.query(Payment).order_by(Payment.id.asc()).all()

    # Pre-fetch recovery cases mapped by payment_id
    cases = db.query(RecoveryCase).all()
    case_by_payment = {c.payment_id: c for c in cases}

    results = []
    for p in payments:
        cust = p.customer
        c = case_by_payment.get(p.id)
        
        last_action = None
        if c and c.actions:
            last_action = c.actions[-1].action_type

        results.append({
            "id": p.id,
            "customer_id": p.customer_id,
            "customer_name": cust.name if cust else "Unknown",
            "customer_email": cust.email if cust else "",
            "amount_paise": p.amount_paise,
            "currency": p.currency,
            "status": p.status,
            "failure_reason": p.failure_reason,
            "attempt_count": p.attempt_count,
            "case_id": c.id if c else None,
            "case_status": c.status if c else None,
            "last_action": last_action,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })

    return results


@router.get("/payments/{payment_id}")
def get_payment_detail(payment_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return detail for a single payment."""
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    cust = p.customer
    case = db.query(RecoveryCase).filter(RecoveryCase.payment_id == payment_id).first()

    return {
        "id": p.id,
        "customer_id": p.customer_id,
        "customer_name": cust.name if cust else "Unknown",
        "customer_email": cust.email if cust else "",
        "amount_paise": p.amount_paise,
        "currency": p.currency,
        "status": p.status,
        "failure_reason": p.failure_reason,
        "attempt_count": p.attempt_count,
        "case_id": case.id if case else None,
        "case_status": case.status if case else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Recovery Cases
# ---------------------------------------------------------------------------

@router.get("/recovery-cases")
def get_recovery_cases(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return all recovery cases with associated payment and customer information."""
    cases = db.query(RecoveryCase).order_by(RecoveryCase.id.asc()).all()

    results = []
    for c in cases:
        cust = c.customer
        p = c.payment

        results.append({
            "id": c.id,
            "payment_id": c.payment_id,
            "customer_id": c.customer_id,
            "customer_name": cust.name if cust else "Unknown",
            "customer_email": cust.email if cust else "",
            "amount_at_risk_paise": c.amount_at_risk_paise,
            "amount_recovered_paise": c.amount_recovered_paise or 0,
            "risk_score": c.risk_score if c.risk_score is not None else calculate_risk_score(p, cust),
            "status": c.status,
            "current_step": c.current_step or (
                "Recovery Completed" if c.status == CASE_STATUS_RECOVERED else
                "Case Escalated" if c.status == CASE_STATUS_ESCALATED else
                "Workflow Stopped" if c.status == CASE_STATUS_STOPPED else
                "Awaiting Payment" if c.status == CASE_STATUS_IN_PROGRESS else "Open"
            ),
            "attempt_count": c.attempt_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    return results


@router.get("/recovery-cases/{case_id}")
def get_recovery_case_detail(case_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return full detail for a recovery case including actions and audit log timeline."""
    c = db.get(RecoveryCase, case_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Recovery case {case_id} not found.")

    cust = c.customer
    p = c.payment

    # Format recovery actions
    actions_data = []
    for act in c.actions:
        actions_data.append({
            "id": act.id,
            "recovery_case_id": act.recovery_case_id,
            "action_type": act.action_type,
            "reason": act.reason,
            "approved": act.approved,
            "result": act.result,
            "amount_recovered_paise": act.amount_recovered_paise or 0,
            "created_at": act.created_at.isoformat() if act.created_at else None,
        })

    # Format audit logs
    logs_data = []
    for log in c.audit_logs:
        logs_data.append({
            "id": log.id,
            "recovery_case_id": log.recovery_case_id,
            "event_type": log.event_type,
            "actor": log.actor,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        })

    # Determine proposed decision and reasoning if available
    proposed_action = "stop"
    proposed_reason = "No active actions taken."
    if c.actions:
        last = c.actions[-1]
        proposed_action = last.action_type
        proposed_reason = last.reason or "Action executed by agent policy."
    elif c.status == CASE_STATUS_STOPPED:
        proposed_action = "stop"
        proposed_reason = "Customer opted out of automated recovery workflow."

    return {
        "id": c.id,
        "payment_id": c.payment_id,
        "customer_id": c.customer_id,
        "customer_name": cust.name if cust else "Unknown",
        "customer_email": cust.email if cust else "",
        "amount_at_risk_paise": c.amount_at_risk_paise,
        "amount_recovered_paise": c.amount_recovered_paise or 0,
        "risk_score": c.risk_score if c.risk_score is not None else calculate_risk_score(p, cust),
        "status": c.status,
        "current_step": c.current_step or "Case Active",
        "attempt_count": c.attempt_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "decision_reasoning": {
            "proposed_action": proposed_action,
            "reason": proposed_reason,
            "policy_result": "Approved" if c.status != CASE_STATUS_STOPPED else "Blocked",
            "guardrail_note": "Customer opted out." if c.status == CASE_STATUS_STOPPED else "Maximum retry policy enforced.",
        },
        "actions": actions_data,
        "audit_logs": logs_data,
    }


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@router.get("/customers")
def get_customers(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return customer directory."""
    customers = db.query(Customer).order_by(Customer.id.asc()).all()

    # Pre-fetch case counts
    cases = db.query(RecoveryCase).all()
    cases_by_customer = {}
    for c in cases:
        cases_by_customer[c.customer_id] = cases_by_customer.get(c.customer_id, 0) + 1

    results = []
    for c in customers:
        results.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone or "",
            "segment": c.segment or "standard",
            "total_paid_paise": c.total_paid_paise or 0,
            "successful_payments": c.successful_payments,
            "failed_payments": c.failed_payments,
            "recovery_cases_count": cases_by_customer.get(c.id, 0),
            "opted_out": c.opted_out,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return results


@router.get("/customers/{customer_id}")
def get_customer_detail(customer_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return customer detail profile."""
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")

    cases_count = db.query(RecoveryCase).filter(RecoveryCase.customer_id == customer_id).count()

    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone or "",
        "segment": c.segment or "standard",
        "total_paid_paise": c.total_paid_paise or 0,
        "successful_payments": c.successful_payments,
        "failed_payments": c.failed_payments,
        "recovery_cases_count": cases_count,
        "opted_out": c.opted_out,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return all audit activity logs."""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()

    # Pre-fetch cases for payment_id mapping
    cases = db.query(RecoveryCase).all()
    case_map = {c.id: c.payment_id for c in cases}

    results = []
    for l in logs:
        results.append({
            "id": l.id,
            "recovery_case_id": l.recovery_case_id,
            "payment_id": case_map.get(l.recovery_case_id),
            "event_type": l.event_type,
            "actor": l.actor,
            "details": l.details,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None,
        })

    return results


# ---------------------------------------------------------------------------
# Simulation Endpoint: Payment Link Completion
# ---------------------------------------------------------------------------

@router.post("/events/complete-payment-link/{payment_id}")
def trigger_payment_link_completion(
    payment_id: int, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Simulate a customer completing payment after receiving a recovery payment link.
    """
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found.")

    res = simulate_payment_completion(payment_id=payment_id, db=db)
    return res
