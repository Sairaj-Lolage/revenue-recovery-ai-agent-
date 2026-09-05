"""
backend/app/tools/messaging_tools.py
====================================
Agent tools for messaging operations (send_recovery_message).
"""

from typing import Any, Dict, Optional
from pydantic import ValidationError

from app.services.payment_service import PaymentService
from app.tools.schemas import (
    SendRecoveryMessageInput,
    SendRecoveryMessageResponse,
)


def send_recovery_message(
    service: PaymentService,
    customer_id: int,
    message: str,
    payment_link: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a recovery message to a customer.
    Honors customer opt-out settings via PaymentService.
    """
    try:
        validated_input = SendRecoveryMessageInput(
            customer_id=customer_id,
            message=message,
            payment_link=payment_link,
        )
    except (ValidationError, ValueError, TypeError) as err:
        return SendRecoveryMessageResponse(
            success=False,
            customer_id=customer_id if isinstance(customer_id, int) else 0,
            channel="mock",
            message_id=None,
            message=f"Invalid input: {err}",
            error="invalid_input",
        ).model_dump()

    res = service.send_recovery_message(
        customer_id=validated_input.customer_id,
        message=validated_input.message,
        payment_link=validated_input.payment_link,
    )

    error_code = None
    if not res.success:
        if "not found" in res.message.lower():
            error_code = "customer_not_found"
        elif "opted out" in res.message.lower():
            error_code = "customer_opted_out"

    return SendRecoveryMessageResponse(
        success=res.success,
        customer_id=res.customer_id,
        channel=res.channel,
        message_id=res.message_id,
        message=res.message,
        error=error_code,
    ).model_dump()
