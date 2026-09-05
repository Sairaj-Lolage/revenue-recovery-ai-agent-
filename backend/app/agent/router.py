"""
backend/app/agent/router.py
===========================
FastAPI router for the AI Revenue Recovery Agent endpoints.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.runner import PaymentNotFoundError, run_recovery_agent
from app.db.database import get_db

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/recover/{payment_id}")
def recover_payment(payment_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Trigger AI revenue recovery workflow for a failed payment.

    Args:
        payment_id: ID of the payment to attempt recovery for.
        db: Database session injected via dependency.

    Returns:
        Structured recovery decision and execution result.
    """
    if payment_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment_id. Must be a positive integer.",
        )

    try:
        result = run_recovery_agent(payment_id=payment_id, db=db)
        return result
    except PaymentNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )
    except Exception as err:
        # Prevent stack trace or key leakage; return controlled error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution encountered an internal error: {str(err)}",
        )
