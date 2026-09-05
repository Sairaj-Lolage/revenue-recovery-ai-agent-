"""
backend/app/agent/runner.py
==========================
Orchestrator runner for the Multi-Step AI Revenue Recovery Agent.

Entry point:
    run_recovery_agent(payment_id, db, llm_reasoner=None)
"""

from typing import Any, Callable, Dict, Optional
from sqlalchemy.orm import Session

from app.agent.graph import create_recovery_graph
from app.agent.risk import calculate_risk_score
from app.db.models import (
    ACTOR_AGENT,
    AuditLog,
    CASE_STATUS_ESCALATED,
    CASE_STATUS_IN_PROGRESS,
    CASE_STATUS_RECOVERED,
    CASE_STATUS_STOPPED,
    RecoveryAction,
    RecoveryCase,
    RecoveryPolicyConfig,
)
from app.services.payment_service import PaymentService
from app.tools import get_agent_tools


class PaymentNotFoundError(Exception):
    """Raised when a requested payment ID does not exist."""
    pass


def run_recovery_agent(
    payment_id: int,
    db: Session,
    llm_reasoner: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Execute the multi-step recovery agent workflow for a single payment.
    Enforces lifecycle rules, idempotency, and one-time follow-up checks.

    Args:
        payment_id: Database ID of the failed payment.
        db: Active SQLAlchemy database session.
        llm_reasoner: Optional custom reasoning function (used for testing).

    Returns:
        Structured recovery decision dictionary.

    Raises:
        PaymentNotFoundError: If payment_id does not exist in the database.
    """
    service = PaymentService(db)

    # Verify payment exists
    payment_info = service.get_payment(payment_id)
    if not payment_info:
        raise PaymentNotFoundError(f"Payment with ID {payment_id} not found.")

    # Fetch customer info for safety check
    customer_info = service.get_customer_history(payment_info.customer_id)
    is_customer_opted_out = bool(customer_info and getattr(customer_info, "opted_out", False))

    # Get existing RecoveryCase for audit trail tracking
    case = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.payment_id == payment_id)
        .first()
    )

    # -----------------------------------------------------------------------
    # LIFECYCLE RULE C: Opted-Out Customer or Stopped Case Protection
    # -----------------------------------------------------------------------
    if is_customer_opted_out or (case and case.status == CASE_STATUS_STOPPED):
        if not case:
            case = RecoveryCase(
                payment_id=payment_id,
                customer_id=payment_info.customer_id,
                amount_at_risk_paise=payment_info.amount_paise,
                risk_score=calculate_risk_score(payment_info, customer_info),
                status=CASE_STATUS_STOPPED,
                attempt_count=0,
            )
            db.add(case)
            db.commit()
            db.refresh(case)
        else:
            case.status = CASE_STATUS_STOPPED

        db.add(
            AuditLog(
                recovery_case_id=case.id,
                actor="guardrail",
                event_type="policy_blocked",
                details=f"Recovery workflow skipped for payment {payment_id}: Customer opted out or case stopped.",
            )
        )
        db.add(
            AuditLog(
                recovery_case_id=case.id,
                actor=ACTOR_AGENT,
                event_type="agent_stopped",
                details="Agent workflow stopped due to policy block or stopped case.",
            )
        )
        db.commit()

        return {
            "payment_id": payment_id,
            "decision": "stop",
            "reason": "Customer opted out of automated recovery; processing skipped.",
            "actions": [],
            "final_status": "stopped",
            "amount_recovered_paise": 0,
            "recovered_amount_paise": 0,
            "execution_result": {"action": "stop", "reason": "Customer opted out or case stopped"},
        }

    # -----------------------------------------------------------------------
    # LIFECYCLE RULE A: Already Recovered or Payment Already Successful
    # -----------------------------------------------------------------------
    if (case and case.status == CASE_STATUS_RECOVERED) or payment_info.status == "success":
        recovered_amount = payment_info.amount_paise if payment_info.status == "success" else (case.amount_recovered_paise or payment_info.amount_paise)
        if not case:
            case = RecoveryCase(
                payment_id=payment_id,
                customer_id=payment_info.customer_id,
                amount_at_risk_paise=payment_info.amount_paise,
                risk_score=calculate_risk_score(payment_info, customer_info),
                status=CASE_STATUS_RECOVERED,
                amount_recovered_paise=recovered_amount,
                attempt_count=0,
            )
            db.add(case)
            db.commit()
            db.refresh(case)
        else:
            case.status = CASE_STATUS_RECOVERED
            case.amount_recovered_paise = recovered_amount

        db.add(
            AuditLog(
                recovery_case_id=case.id,
                actor="system",
                event_type="recovery_already_complete",
                details=f"Recovery processing skipped: Payment {payment_id} is already successfully recovered.",
            )
        )
        db.commit()

        return {
            "payment_id": payment_id,
            "decision": "stop",
            "reason": "Payment is already successfully recovered.",
            "actions": [],
            "final_status": "success",
            "amount_recovered_paise": case.amount_recovered_paise,
            "recovered_amount_paise": case.amount_recovered_paise,
            "execution_result": {"action": "stop", "reason": "Already recovered"},
        }

    # -----------------------------------------------------------------------
    # LIFECYCLE RULE B: Already Escalated
    # -----------------------------------------------------------------------
    if case and case.status == CASE_STATUS_ESCALATED:
        db.add(
            AuditLog(
                recovery_case_id=case.id,
                actor="system",
                event_type="recovery_already_escalated",
                details=f"Recovery processing skipped: Case for payment {payment_id} has already been escalated.",
            )
        )
        db.commit()

        return {
            "payment_id": payment_id,
            "decision": "stop",
            "reason": "Case has already been escalated for manual intervention.",
            "actions": [],
            "final_status": "escalated",
            "amount_recovered_paise": case.amount_recovered_paise or 0,
            "recovered_amount_paise": case.amount_recovered_paise or 0,
            "execution_result": {"action": "stop", "reason": "Already escalated"},
        }

    # Create RecoveryCase if not exists for new recovery attempt
    if not case:
        case = RecoveryCase(
            payment_id=payment_id,
            customer_id=payment_info.customer_id,
            amount_at_risk_paise=payment_info.amount_paise,
            risk_score=calculate_risk_score(payment_info, customer_info),
            status=CASE_STATUS_IN_PROGRESS,
            attempt_count=0,
        )
        db.add(case)
        db.commit()
        db.refresh(case)

    # -----------------------------------------------------------------------
    # LIFECYCLE RULE D: One-Time Follow-Up Check (case.attempt_count >= 1 & IN_PROGRESS)
    # -----------------------------------------------------------------------
    if case.status == CASE_STATUS_IN_PROGRESS and case.attempt_count >= 1:
        case.attempt_count += 1
        
        db.add(
            AuditLog(
                recovery_case_id=case.id,
                actor="system",
                event_type="follow_up_started",
                details=f"Started one-time follow-up check for payment_id={payment_id} (recovery attempt #{case.attempt_count}).",
            )
        )

        # Refresh payment status to verify if payment link was completed
        payment_info = service.get_payment(payment_id)

        if payment_info and payment_info.status == "success":
            case.status = CASE_STATUS_RECOVERED
            case.amount_recovered_paise = payment_info.amount_paise
            db.add(
                AuditLog(
                    recovery_case_id=case.id,
                    actor="system",
                    event_type="follow_up_completed",
                    details=f"Follow-up check confirmed payment {payment_id} recovered INR {payment_info.amount_paise / 100:.2f}.",
                )
            )
            db.add(
                AuditLog(
                    recovery_case_id=case.id,
                    actor=ACTOR_AGENT,
                    event_type="recovery_succeeded",
                    details=f"Payment {payment_id} successfully recovered via follow-up.",
                )
            )
            db.commit()

            return {
                "payment_id": payment_id,
                "decision": "stop",
                "reason": "Follow-up check confirmed payment was successfully recovered.",
                "actions": [],
                "final_status": "success",
                "amount_recovered_paise": payment_info.amount_paise,
                "recovered_amount_paise": payment_info.amount_paise,
                "execution_result": {"action": "follow_up", "status": "success"},
            }
        else:
            case.status = CASE_STATUS_ESCALATED
            db.add(
                AuditLog(
                    recovery_case_id=case.id,
                    actor="system",
                    event_type="follow_up_completed",
                    details=f"Follow-up check for payment {payment_id} showed payment still unrecovered. Escalating case.",
                )
            )
            db.add(
                AuditLog(
                    recovery_case_id=case.id,
                    actor=ACTOR_AGENT,
                    event_type="agent_escalated",
                    details=f"Case escalated following unrecovered follow-up check for payment {payment_id}.",
                )
            )
            db.commit()

            return {
                "payment_id": payment_id,
                "decision": "escalate",
                "reason": "Follow-up completed: payment remains unrecovered after recovery link/message. Escalating case.",
                "actions": [],
                "final_status": "escalated",
                "amount_recovered_paise": 0,
                "recovered_amount_paise": 0,
                "execution_result": {"action": "follow_up", "status": "escalated"},
            }

    # -----------------------------------------------------------------------
    # INITIAL RECOVERY RUN (attempt_count == 0)
    # -----------------------------------------------------------------------
    case.attempt_count += 1
    db.commit()

    # Retrieve registered agent tools & map by tool function name
    tools_list = get_agent_tools(service)
    tools_by_name = {fn.__name__: fn for fn in tools_list}

    # Initial state
    config = db.get(RecoveryPolicyConfig, 1)
    if not config:
        config = RecoveryPolicyConfig(id=1)
        db.add(config)
        db.commit()

    initial_state = {
        "payment_id": payment_id,
        "actions": [],
        "audit_events": [
            {
                "event_type": "AGENT_STARTED",
                "actor": ACTOR_AGENT,
                "details": f"Started AI recovery workflow for payment_id={payment_id}",
            }
        ],
        "action_count": 0,
        "retry_count": 0,
        "amount_recovered_paise": 0,
        "final_status": "in_progress",
        "max_retry_attempts": config.max_retry_attempts,
        "high_value_threshold_paise": config.high_value_threshold_paise,
    }

    # Compile & execute LangGraph recovery graph
    graph = create_recovery_graph(tools_by_name=tools_by_name, llm_reasoner=llm_reasoner)
    final_state = graph.invoke(initial_state)

    # Persist all audit log events to database
    audit_events = final_state.get("audit_events", [])
    for event in audit_events:
        db.add(
            AuditLog(
                recovery_case_id=case.id,
                actor=event.get("actor", ACTOR_AGENT),
                event_type=event.get("event_type", "agent_event").lower(),
                details=event.get("details", ""),
            )
        )

    # Persist executed recovery actions to database
    actions_executed = final_state.get("actions", [])
    valid_action_types = {
        "retry_payment",
        "create_payment_link",
        "send_recovery_message",
        "escalate",
        "stop",
    }
    decision_reason = final_state.get("reason", "No reason provided.")

    for action in actions_executed:
        action_type = action.get("action_type") or action.get("tool")
        if action_type in valid_action_types:
            db.add(
                RecoveryAction(
                    recovery_case_id=case.id,
                    action_type=action_type,
                    reason=action.get("reason") or decision_reason,
                    approved=action.get("approved", True),
                    result=action.get("result") or action.get("status"),
                    amount_recovered_paise=action.get("amount_recovered_paise", 0),
                )
            )

    # Update RecoveryCase record status and recovered amount
    amount_recovered = final_state.get("amount_recovered_paise", 0)
    final_status = final_state.get("final_status", "in_progress")
    decision = final_state.get("decision", "stop")
    reason = final_state.get("reason", "No reason provided.")

    if amount_recovered > 0:
        case.status = CASE_STATUS_RECOVERED
        case.amount_recovered_paise = amount_recovered
    elif decision == "escalate" or final_status == "escalated":
        case.status = CASE_STATUS_ESCALATED
    elif decision == "stop" or final_status == "stopped":
        case.status = CASE_STATUS_STOPPED
    else:
        case.status = CASE_STATUS_IN_PROGRESS

    db.commit()

    return {
        "payment_id": payment_id,
        "decision": decision,
        "reason": reason,
        "actions": final_state.get("actions", []),
        "final_status": final_status,
        "amount_recovered_paise": amount_recovered,
        "recovered_amount_paise": amount_recovered,
        "execution_result": final_state.get("execution_result"),
    }
