"""Deterministic, explainable recovery-risk scoring."""

from typing import Any


def calculate_risk_score(payment: Any, customer: Any) -> int:
    """Return a 0–100 recovery risk score using agent-safe business signals."""
    score = 15
    score += min(getattr(payment, "attempt_count", 0) * 12, 30)

    amount_paise = getattr(payment, "amount_paise", 0)
    if amount_paise >= 1_000_000:
        score += 25
    elif amount_paise >= 500_000:
        score += 10

    failure_reason = getattr(payment, "failure_reason", "") or ""
    if failure_reason in {"card_declined", "bank_declined", "expired_card"}:
        score += 10
    elif failure_reason in {"insufficient_funds", "authentication_failed"}:
        score += 5

    successful = getattr(customer, "successful_payments", 0)
    failed = getattr(customer, "failed_payments", 0)
    if failed > successful:
        score += 20
    elif successful >= 3:
        score -= 10

    segment = getattr(customer, "segment", "") or ""
    if segment == "at_risk":
        score += 15
    elif segment == "new":
        score += 8
    if getattr(customer, "opted_out", False):
        score += 20

    return max(0, min(score, 100))
