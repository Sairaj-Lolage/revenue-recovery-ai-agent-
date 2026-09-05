"""
backend/app/agent/state.py
==========================
LangGraph state definition for the AI Revenue Recovery Agent.
"""

from typing import Any, Dict, List, Optional, TypedDict


class RecoveryAgentState(TypedDict, total=False):
    payment_id: int
    customer_id: Optional[int]
    payment_data: Optional[Dict[str, Any]]
    customer_data: Optional[Dict[str, Any]]
    proposed_decision: Optional[str]
    decision: Optional[str]
    reason: Optional[str]
    actions: List[Dict[str, Any]]
    audit_events: List[Dict[str, Any]]
    final_status: str
    amount_recovered_paise: int
    execution_result: Optional[Dict[str, Any]]
    error: Optional[str]
    action_count: int
    retry_count: int
    created_payment_link: Optional[str]
    max_retry_attempts: int
    high_value_threshold_paise: int
    should_continue: bool
