"""
backend/app/tools/payment_tools.py
==================================
Agent tools for payment operations (get_payment, retry_payment, create_payment_link).
"""

from typing import Any, Dict
from pydantic import ValidationError

from app.services.payment_service import PaymentService
from app.tools.schemas import (
    CreatePaymentLinkInput,
    CreatePaymentLinkResponse,
    GetPaymentInput,
    GetPaymentResponse,
    RetryPaymentInput,
    RetryPaymentResponse,
)


def get_payment(service: PaymentService, payment_id: int) -> Dict[str, Any]:
    """
    Retrieve agent-safe information for a payment.
    Excludes internal evaluation metadata like recovery_scenario.
    """
    try:
        validated_input = GetPaymentInput(payment_id=payment_id)
    except (ValidationError, ValueError, TypeError):
        return GetPaymentResponse(
            success=False,
            error="invalid_input",
            message=f"Invalid payment_id: {payment_id}",
        ).model_dump()

    info = service.get_payment(validated_input.payment_id)
    if info is None:
        return GetPaymentResponse(
            success=False,
            error="payment_not_found",
            message=f"Payment {payment_id} was not found",
        ).model_dump()

    return GetPaymentResponse(
        success=True,
        payment_id=info.payment_id,
        customer_id=info.customer_id,
        amount_paise=info.amount_paise,
        currency=info.currency,
        status=info.status,
        failure_reason=info.failure_reason,
        attempt_count=info.attempt_count,
    ).model_dump()


def retry_payment(service: PaymentService, payment_id: int) -> Dict[str, Any]:
    """
    Attempt an automatic retry for a failed payment.
    Delegates to PaymentService. Does NOT implement recovery logic inside tool.
    """
    try:
        validated_input = RetryPaymentInput(payment_id=payment_id)
    except (ValidationError, ValueError, TypeError):
        return RetryPaymentResponse(
            success=False,
            payment_id=payment_id if isinstance(payment_id, int) else 0,
            amount_recovered_paise=0,
            status="failed",
            error="invalid_input",
            message=f"Invalid payment_id: {payment_id}",
        ).model_dump()

    res = service.retry_payment(validated_input.payment_id)
    error_code = "payment_not_found" if ("not found" in res.message.lower()) else None

    return RetryPaymentResponse(
        success=res.success,
        payment_id=res.payment_id,
        amount_recovered_paise=res.amount_recovered_paise,
        status=res.status,
        message=res.message,
        error=error_code,
    ).model_dump()


def create_payment_link(service: PaymentService, payment_id: int) -> Dict[str, Any]:
    """
    Create a payment link for a failed payment.
    Delegates to PaymentService. Does NOT recover the payment.
    """
    try:
        validated_input = CreatePaymentLinkInput(payment_id=payment_id)
    except (ValidationError, ValueError, TypeError):
        return CreatePaymentLinkResponse(
            success=False,
            payment_id=payment_id if isinstance(payment_id, int) else 0,
            payment_link=None,
            error="invalid_input",
            message=f"Invalid payment_id: {payment_id}",
        ).model_dump()

    res = service.create_payment_link(validated_input.payment_id)
    error_code = "payment_not_found" if ("not found" in res.message.lower()) else None

    return CreatePaymentLinkResponse(
        success=res.success,
        payment_id=res.payment_id,
        payment_link=res.payment_link,
        message=res.message,
        error=error_code,
    ).model_dump()
