"""
backend/app/tools/__init__.py
=============================
Agent tool layer and registry.

Architecture:
  Future Agent -> Agent Tools -> PaymentService -> SQLite (SQLAlchemy)
"""

from typing import Any, Callable, Dict, List, Optional

from app.services.payment_service import PaymentService
from app.tools.customer_tools import get_customer_history
from app.tools.messaging_tools import send_recovery_message
from app.tools.payment_tools import (
    create_payment_link,
    get_payment,
    retry_payment,
)


def get_agent_tools(service: PaymentService) -> List[Callable[..., Dict[str, Any]]]:
    """
    Return the five agent-facing tool functions bound to the provided PaymentService.

    Returns:
        [
            get_payment,
            get_customer_history,
            retry_payment,
            create_payment_link,
            send_recovery_message
        ]
    """
    def tool_get_payment(payment_id: int) -> Dict[str, Any]:
        """Fetch agent-safe details for a payment."""
        return get_payment(service, payment_id)

    def tool_get_customer_history(customer_id: int) -> Dict[str, Any]:
        """Fetch agent-safe customer history and metrics."""
        return get_customer_history(service, customer_id)

    def tool_retry_payment(payment_id: int) -> Dict[str, Any]:
        """Attempt to retry a failed payment."""
        return retry_payment(service, payment_id)

    def tool_create_payment_link(payment_id: int) -> Dict[str, Any]:
        """Create a recovery payment link for a failed payment."""
        return create_payment_link(service, payment_id)

    def tool_send_recovery_message(
        customer_id: int,
        message: str,
        payment_link: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a recovery message to a customer."""
        return send_recovery_message(service, customer_id, message, payment_link)

    tool_get_payment.__name__ = "get_payment"
    tool_get_customer_history.__name__ = "get_customer_history"
    tool_retry_payment.__name__ = "retry_payment"
    tool_create_payment_link.__name__ = "create_payment_link"
    tool_send_recovery_message.__name__ = "send_recovery_message"

    tool_get_payment.__doc__ = get_payment.__doc__
    tool_get_customer_history.__doc__ = get_customer_history.__doc__
    tool_retry_payment.__doc__ = retry_payment.__doc__
    tool_create_payment_link.__doc__ = create_payment_link.__doc__
    tool_send_recovery_message.__doc__ = send_recovery_message.__doc__

    return [
        tool_get_payment,
        tool_get_customer_history,
        tool_retry_payment,
        tool_create_payment_link,
        tool_send_recovery_message,
    ]


__all__ = [
    "get_agent_tools",
    "get_payment",
    "get_customer_history",
    "retry_payment",
    "create_payment_link",
    "send_recovery_message",
]
