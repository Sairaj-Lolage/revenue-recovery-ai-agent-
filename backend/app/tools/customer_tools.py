"""
backend/app/tools/customer_tools.py
===================================
Agent tools for customer operations (get_customer_history).
"""

from typing import Any, Dict
from pydantic import ValidationError

from app.services.payment_service import PaymentService
from app.tools.schemas import (
    GetCustomerHistoryInput,
    GetCustomerHistoryResponse,
)


def get_customer_history(service: PaymentService, customer_id: int) -> Dict[str, Any]:
    """
    Retrieve agent-safe customer history and profile metrics.
    Excludes hidden evaluation metadata.
    """
    try:
        validated_input = GetCustomerHistoryInput(customer_id=customer_id)
    except (ValidationError, ValueError, TypeError):
        return GetCustomerHistoryResponse(
            success=False,
            error="invalid_input",
            message=f"Invalid customer_id: {customer_id}",
        ).model_dump()

    history = service.get_customer_history(validated_input.customer_id)
    if history is None:
        return GetCustomerHistoryResponse(
            success=False,
            error="customer_not_found",
            message=f"Customer {customer_id} was not found",
        ).model_dump()

    return GetCustomerHistoryResponse(
        success=True,
        customer_id=history.customer_id,
        name=history.name,
        segment=history.segment,
        total_paid_paise=history.total_paid_paise,
        successful_payments=history.successful_payments,
        failed_payments=history.failed_payments,
        opted_out=history.opted_out,
    ).model_dump()
