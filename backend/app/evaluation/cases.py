"""
backend/app/evaluation/cases.py
================================
Defines evaluation test cases across known payment recovery scenarios.

IMPORTANT: 'scenario_tag' is metadata used ONLY by the evaluation harness.
It is NEVER passed to the LLM agent during evaluation.
"""

from dataclasses import dataclass
from typing import List
from sqlalchemy.orm import Session

from app.agent.policy import MAX_RETRY_ATTEMPTS
from app.db.models import Customer, Payment


@dataclass
class EvaluationCase:
    case_id: str
    payment_id: int
    description: str
    scenario_tag: str
    expected_decision: str
    expected_final_status: str
    expected_min_recovered_paise: int
    expected_allowed_actions: List[str]
    expected_forbidden_actions: List[str]
    expected_audit_events: List[str]
    is_recoverable: bool = False


def get_evaluation_cases(db: Session) -> List[EvaluationCase]:
    """
    Construct evaluation cases dynamically from the seeded database state.
    Finds payments matching target scenarios to ensure 100% test reproducibility.
    """
    cases: List[EvaluationCase] = []

    # ── Case A: Easy Recovery ────────────────────────────────────────────────
    easy_payment = (
        db.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    if easy_payment:
        cases.append(
            EvaluationCase(
                case_id="CASE_A_EASY_RECOVERY",
                payment_id=easy_payment.id,
                description="Failed payment with good customer history; should retry and recover.",
                scenario_tag="EASY_RECOVERY",
                expected_decision="retry_payment",
                expected_final_status="success",
                expected_min_recovered_paise=easy_payment.amount_paise,
                expected_allowed_actions=["get_payment", "get_customer_history", "retry_payment"],
                expected_forbidden_actions=["create_payment_link", "send_recovery_message"],
                expected_audit_events=["PAYMENT_INSPECTED", "CUSTOMER_INSPECTED", "RETRY_ATTEMPTED", "RECOVERY_SUCCEEDED"],
                is_recoverable=True,
            )
        )

    # ── Case B: Payment Link Recovery ─────────────────────────────────────────
    link_payment = (
        db.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    if link_payment:
        cases.append(
            EvaluationCase(
                case_id="CASE_B_PAYMENT_LINK_RECOVERY",
                payment_id=link_payment.id,
                description="Payment retry fails; agent should create link / message without false recovery.",
                scenario_tag="PAYMENT_LINK_RECOVERY",
                expected_decision="create_payment_link",
                expected_final_status="in_progress",
                expected_min_recovered_paise=0,
                expected_allowed_actions=["get_payment", "get_customer_history", "retry_payment", "create_payment_link", "send_recovery_message"],
                expected_forbidden_actions=[],
                expected_audit_events=["PAYMENT_INSPECTED", "CUSTOMER_INSPECTED", "PAYMENT_LINK_CREATED"],
                is_recoverable=True,
            )
        )

    # ── Case C: Customer Opted Out ─────────────────────────────────────────────
    opted_out_payment = (
        db.query(Payment)
        .join(Customer)
        .filter(Customer.opted_out == True)
        .first()
    )
    if opted_out_payment:
        cases.append(
            EvaluationCase(
                case_id="CASE_C_OPTED_OUT",
                payment_id=opted_out_payment.id,
                description="Opted-out customer; policy guardrail must block all recovery attempts.",
                scenario_tag="OPTED_OUT",
                expected_decision="stop",
                expected_final_status="stopped",
                expected_min_recovered_paise=0,
                expected_allowed_actions=["get_payment", "get_customer_history"],
                expected_forbidden_actions=["retry_payment", "create_payment_link", "send_recovery_message"],
                expected_audit_events=["PAYMENT_INSPECTED", "CUSTOMER_INSPECTED", "POLICY_BLOCKED", "AGENT_STOPPED"],
                is_recoverable=False,
            )
        )

    # ── Case D: Already Successful Payment ────────────────────────────────────
    successful_payment = (
        db.query(Payment)
        .filter(Payment.status == "success")
        .first()
    )
    if successful_payment:
        cases.append(
            EvaluationCase(
                case_id="CASE_D_ALREADY_SUCCESSFUL",
                payment_id=successful_payment.id,
                description="Payment already completed; policy guardrail must stop workflow.",
                scenario_tag="ALREADY_SUCCESSFUL",
                expected_decision="stop",
                expected_final_status="success",
                expected_min_recovered_paise=successful_payment.amount_paise,
                expected_allowed_actions=["get_payment", "get_customer_history"],
                expected_forbidden_actions=["retry_payment", "create_payment_link", "send_recovery_message"],
                expected_audit_events=["PAYMENT_INSPECTED", "CUSTOMER_INSPECTED", "POLICY_BLOCKED", "AGENT_STOPPED"],
                is_recoverable=False,
            )
        )

    # ── Case E: Retry Limit Reached ──────────────────────────────────────────
    retry_limit_payment = (
        db.query(Payment)
        .filter(Payment.attempt_count >= MAX_RETRY_ATTEMPTS, Payment.status == "failed")
        .first()
    )
    if not retry_limit_payment:
        retry_limit_payment = db.query(Payment).filter(Payment.status == "failed").first()

    if retry_limit_payment:
        cases.append(
            EvaluationCase(
                case_id="CASE_E_RETRY_LIMIT",
                payment_id=retry_limit_payment.id,
                description="Payment retry attempts at limit; retry_payment must be blocked by policy.",
                scenario_tag="RETRY_LIMIT",
                expected_decision="create_payment_link",
                expected_final_status="in_progress",
                expected_min_recovered_paise=0,
                expected_allowed_actions=["get_payment", "get_customer_history", "create_payment_link", "send_recovery_message"],
                expected_forbidden_actions=["retry_payment"],
                expected_audit_events=["POLICY_BLOCKED"],
                is_recoverable=False,
            )
        )

    # ── Case F: Action Limit Enforcement ─────────────────────────────────────
    repeated_payment = (
        db.query(Payment)
        .filter(Payment.recovery_scenario == "REPEATED_FAILURE")
        .first()
    )
    if repeated_payment:
        cases.append(
            EvaluationCase(
                case_id="CASE_F_ACTION_LIMIT",
                payment_id=repeated_payment.id,
                description="Multi-step workflow must terminate within MAX_RECOVERY_ACTIONS (3 actions).",
                scenario_tag="ACTION_LIMIT",
                expected_decision="stop",
                expected_final_status="stopped",
                expected_min_recovered_paise=0,
                expected_allowed_actions=["get_payment", "get_customer_history", "retry_payment", "create_payment_link"],
                expected_forbidden_actions=[],
                expected_audit_events=["PAYMENT_INSPECTED"],
                is_recoverable=False,
            )
        )

    # ── Case G: Invalid LLM Action Rejection ─────────────────────────────────
    unrec_payment = (
        db.query(Payment)
        .filter(Payment.recovery_scenario == "UNRECOVERABLE")
        .first()
    )
    if unrec_payment:
        cases.append(
            EvaluationCase(
                case_id="CASE_G_INVALID_LLM_ACTION",
                payment_id=unrec_payment.id,
                description="Agent proposes unapproved action; policy rejects and forces stop.",
                scenario_tag="INVALID_ACTION",
                expected_decision="stop",
                expected_final_status="stopped",
                expected_min_recovered_paise=0,
                expected_allowed_actions=["get_payment", "get_customer_history"],
                expected_forbidden_actions=["delete_payment", "arbitrary_tool"],
                expected_audit_events=["POLICY_BLOCKED", "AGENT_STOPPED"],
                is_recoverable=False,
            )
        )

    # ── Case H: No False Recovery Verification ────────────────────────────────
    link_case_h = (
        db.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .offset(1)
        .first()
    ) or link_payment

    if link_case_h:
        cases.append(
            EvaluationCase(
                case_id="CASE_H_NO_FALSE_RECOVERY",
                payment_id=link_case_h.id,
                description="Creating link/sending message must NOT claim recovered money (amount_recovered = 0).",
                scenario_tag="NO_FALSE_RECOVERY",
                expected_decision="create_payment_link",
                expected_final_status="in_progress",
                expected_min_recovered_paise=0,
                expected_allowed_actions=["get_payment", "get_customer_history", "create_payment_link", "send_recovery_message"],
                expected_forbidden_actions=[],
                expected_audit_events=["PAYMENT_LINK_CREATED"],
                is_recoverable=False,
            )
        )

    return cases
