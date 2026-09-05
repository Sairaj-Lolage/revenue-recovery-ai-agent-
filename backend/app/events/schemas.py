"""
backend/app/events/schemas.py
==============================
Pydantic schemas for payment failure event ingestion.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class PaymentFailedEvent(BaseModel):
    """Event payload for incoming payment failure notifications."""

    event_type: str = Field(
        ...,
        description="Type of the event. Must be 'payment.failed'.",
    )
    payment_id: int = Field(
        ...,
        gt=0,
        description="ID of the payment that failed (must be a positive integer).",
    )
    event_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the event (e.g. 'evt_001').",
    )


class PaymentFailedEventResponse(BaseModel):
    """Response payload returned after processing a payment failure event."""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type")
    payment_id: int = Field(..., description="Payment ID")
    status: str = Field(default="processed", description="Event ingestion status")
    recovery_result: Dict[str, Any] = Field(..., description="Result of the recovery agent execution")
