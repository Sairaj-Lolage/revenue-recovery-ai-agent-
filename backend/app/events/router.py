"""
backend/app/events/router.py
=============================
FastAPI router for local payment event ingestion.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.runner import PaymentNotFoundError, run_recovery_agent
from app.db.database import get_db
from app.events.schemas import PaymentFailedEvent, PaymentFailedEventResponse

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.post(
    "/payment-failed",
    response_model=PaymentFailedEventResponse,
    status_code=status.HTTP_200_OK,
)
def handle_payment_failed_event(
    event: PaymentFailedEvent,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Ingest a local payment.failed event and trigger the recovery workflow.

    Validation:
    - Event payload structure validated via Pydantic model.
    - event_type must be 'payment.failed' (returns 400 for unsupported types).
    - payment_id must exist in the database (returns 404 for missing payments).

    Idempotency & Lifecycle:
    - Delegates directly to existing run_recovery_agent().
    - RecoveryCase state machine handles deduplication and lifecycle rules.
    """
    if event.event_type != "payment.failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported event_type '{event.event_type}'. Expected 'payment.failed'.",
        )

    try:
        recovery_result = run_recovery_agent(payment_id=event.payment_id, db=db)
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "payment_id": event.payment_id,
            "status": "processed",
            "recovery_result": recovery_result,
        }
    except PaymentNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing payment failure event: {str(err)}",
        )
