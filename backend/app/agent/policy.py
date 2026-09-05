"""
backend/app/agent/policy.py
===========================
Deterministic Recovery Policy & Guardrails for AI Revenue Recovery Agent.

Enforces business boundaries, safety rules, and limits regardless of LLM recommendations.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

# Policy Limits
MAX_RETRY_ATTEMPTS = 2
MAX_RECOVERY_ACTIONS = 3

# Controlled Allowlist of Action Types
ALLOWED_ACTIONS: Set[str] = {
    "retry_payment",
    "create_payment_link",
    "send_recovery_message",
    "stop",
    "escalate",
}


@dataclass
class PolicyDecision:
    allowed: bool
    decision: str
    reason: str
    event_type: str  # "POLICY_ALLOWED" or "POLICY_BLOCKED"
    override_reason: Optional[str] = None


def evaluate_policy_guardrails(
    proposed_decision: str,
    proposed_reason: str,
    payment_data: Optional[Dict[str, Any]],
    customer_data: Optional[Dict[str, Any]],
    action_count: int,
    retry_count: int,
    payment_link_created: bool = False,
    recovery_message_sent: bool = False,
    max_retry_attempts: int = MAX_RETRY_ATTEMPTS,
    high_value_threshold_paise: Optional[int] = None,
) -> PolicyDecision:
    """
    Evaluate deterministic policy rules against a proposed LLM decision.

    Rules enforced:
    1. Action Allowlist: Proposed decision must be in ALLOWED_ACTIONS.
    2. Successful Payment: If payment status is 'success', force STOP.
    3. Customer Opt-Out: If customer opted_out == True, force STOP.
    4. Action Limit: If action_count >= MAX_RECOVERY_ACTIONS, force STOP.
    5. Retry Limit: If proposed decision is 'retry_payment' and attempt_count >= MAX_RETRY_ATTEMPTS, block retry.
    """

    # 1. Action Allowlist check
    if proposed_decision not in ALLOWED_ACTIONS:
        return PolicyDecision(
            allowed=False,
            decision="stop",
            reason=f"Action '{proposed_decision}' rejected by policy allowlist.",
            event_type="POLICY_BLOCKED",
            override_reason=f"Invalid action '{proposed_decision}' requested.",
        )

    # 2. Already Successful check
    if payment_data and payment_data.get("status") == "success":
        return PolicyDecision(
            allowed=False,
            decision="stop",
            reason="Payment is already successful; automated recovery blocked.",
            event_type="POLICY_BLOCKED",
            override_reason="Payment status is success.",
        )

    # 3. Customer Opt-Out check
    if customer_data and customer_data.get("opted_out") is True:
        return PolicyDecision(
            allowed=False,
            decision="stop",
            reason="Customer opted out of automated recovery; all actions blocked.",
            event_type="POLICY_BLOCKED",
            override_reason="Customer opted_out is True.",
        )

    # 4. High-value payments require human review before automated action.
    if (
        high_value_threshold_paise is not None
        and payment_data
        and payment_data.get("amount_paise", 0) >= high_value_threshold_paise
    ):
        return PolicyDecision(
            allowed=False,
            decision="escalate",
            reason="Payment exceeds the configured high-value escalation threshold.",
            event_type="POLICY_BLOCKED",
            override_reason="High-value payment requires human review.",
        )

    # 5. Maximum Action Limit check
    if action_count >= MAX_RECOVERY_ACTIONS:
        return PolicyDecision(
            allowed=False,
            decision="stop",
            reason=f"Maximum recovery action limit ({MAX_RECOVERY_ACTIONS}) reached for single workflow run.",
            event_type="POLICY_BLOCKED",
            override_reason=f"action_count ({action_count}) >= MAX_RECOVERY_ACTIONS ({MAX_RECOVERY_ACTIONS}).",
        )

    # 6. Retry Limit check
    if proposed_decision == "retry_payment":
        current_attempts = payment_data.get("attempt_count", 0) if payment_data else 0
        if current_attempts >= max_retry_attempts or retry_count >= max_retry_attempts:
            # A blocked retry must advance the bounded link-recovery sequence,
            # rather than terminate it.  This also makes the guardrail safe
            # when a reasoner repeats its original retry recommendation.
            if not payment_link_created:
                fallback_decision = "create_payment_link"
            elif not recovery_message_sent:
                fallback_decision = "send_recovery_message"
            else:
                fallback_decision = "stop"
            return PolicyDecision(
                allowed=False,
                decision=fallback_decision,
                reason=f"Retry attempt limit ({max_retry_attempts}) reached. Switching recovery path.",
                event_type="POLICY_BLOCKED",
                override_reason=f"Retry limit ({max_retry_attempts}) reached.",
            )

    # Policy approves proposed action
    return PolicyDecision(
        allowed=True,
        decision=proposed_decision,
        reason=proposed_reason,
        event_type="POLICY_ALLOWED",
    )
