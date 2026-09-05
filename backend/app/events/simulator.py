"""
backend/app/events/simulator.py
================================
Local Payment Failure Event Simulator.

Simulates payment failure events from external payment infrastructure and
dispatches them to the local event ingestion endpoint (/api/events/payment-failed).

Usage via CLI:
    python -m app.events.simulator 67
    python -m app.events.simulator 4 --reset
    python -m app.events.simulator 67 --base-url http://127.0.0.1:8000
"""

import argparse
import sys
import uuid
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, init_db
from app.db.seed import seed
from app.events.router import handle_payment_failed_event
from app.events.schemas import PaymentFailedEvent
from app.services.payment_service import PaymentService


def simulate_payment_failure(
    payment_id: int,
    db: Optional[Session] = None,
    event_id: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simulate a payment failure operation and dispatch a payment.failed event.

    Args:
        payment_id: ID of the failed payment.
        db: Optional SQLAlchemy session. If None and no base_url, a session is managed automatically.
        event_id: Optional unique event ID. If None, a random ID is generated.
        base_url: Optional base HTTP URL (e.g., 'http://127.0.0.1:8000'). If provided, dispatches via HTTP POST.

    Returns:
        Structured result containing event details and recovery outcome.
    """
    generated_event_id = event_id or f"evt_sim_{uuid.uuid4().hex[:8]}"
    payload = {
        "event_type": "payment.failed",
        "payment_id": payment_id,
        "event_id": generated_event_id,
    }

    # Dispatch mode 1: HTTP API endpoint
    if base_url:
        target_url = f"{base_url.rstrip('/')}/api/events/payment-failed"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(target_url, json=payload)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "event_id": generated_event_id,
                        "event_type": "payment.failed",
                        "payment_id": payment_id,
                        "status": "error",
                        "error_code": response.status_code,
                        "detail": response.json().get("detail", response.text),
                    }
        except Exception as err:
            return {
                "event_id": generated_event_id,
                "event_type": "payment.failed",
                "payment_id": payment_id,
                "status": "dispatch_failed",
                "detail": str(err),
            }

    # Dispatch mode 2: Direct call to event ingestion handler with active DB session
    close_db_on_exit = False
    if db is None:
        init_db()
        db = SessionLocal()
        close_db_on_exit = True

    try:
        event_schema = PaymentFailedEvent(**payload)
        res = handle_payment_failed_event(event=event_schema, db=db)
        return res
    finally:
        if close_db_on_exit and db:
            db.close()


def simulate_payment_completion(
    payment_id: int,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Simulate a customer completing payment via payment link.

    Args:
        payment_id: ID of the payment completed.
        db: Optional SQLAlchemy session.

    Returns:
        Result dictionary indicating success/failure of the payment completion.
    """
    close_db_on_exit = False
    if db is None:
        init_db()
        db = SessionLocal()
        close_db_on_exit = True

    try:
        service = PaymentService(db)
        result = service.complete_payment_via_link(payment_id)
        return {
            "payment_id": result.payment_id,
            "success": result.success,
            "amount_recovered_paise": result.amount_recovered_paise,
            "status": result.status,
            "message": result.message,
        }
    finally:
        if close_db_on_exit and db:
            db.close()


def main() -> None:
    """CLI entry point for simulating payment events."""
    parser = argparse.ArgumentParser(
        description="Local Payment Failure Event Simulator for Revenue Recovery Agent."
    )
    parser.add_argument(
        "payment_id",
        type=int,
        help="ID of the failed payment to simulate.",
    )
    parser.add_argument(
        "--event-id",
        type=str,
        default=None,
        help="Optional custom event ID (e.g., evt_001).",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Target base HTTP URL for running FastAPI server (e.g., http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset and re-seed the local SQLite database before simulation.",
    )

    args = parser.parse_args()

    if args.reset:
        print("[INIT] Resetting database and seeding synthetic data...")
        init_db()
        db_seed = SessionLocal()
        seed(db_seed)
        db_seed.close()
        print("[INIT] Database reset complete.\n")

    print("=" * 60)
    print("REVENUE RECOVERY AGENT — LOCAL EVENT SIMULATOR")
    print("=" * 60)
    print(f"Simulating payment failure...")
    print(f"Payment ID:  {args.payment_id}")
    print(f"Event ID:    {args.event_id or 'Auto-generated'}")
    print(f"Event Type:  payment.failed")
    if args.base_url:
        print(f"Dispatch:    HTTP POST -> {args.base_url}/api/events/payment-failed")
    else:
        print(f"Dispatch:    Direct event ingestion router call")
    print("-" * 60)
    print("Dispatching event...\n")

    result = simulate_payment_failure(
        payment_id=args.payment_id,
        event_id=args.event_id,
        base_url=args.base_url,
    )

    print("Result Summary:")
    status_code = result.get("status", "processed")
    print(f"Event Status:    {status_code}")

    if status_code in {"error", "dispatch_failed"}:
        print(f"Error Detail:    {result.get('detail')}")
        sys.exit(1)

    rec_res = result.get("recovery_result", {})
    decision = rec_res.get("decision", "N/A")
    reason = rec_res.get("reason", "N/A")
    final_status = rec_res.get("final_status", "N/A")
    amount_rec = rec_res.get("amount_recovered_paise", 0) / 100.0
    actions = rec_res.get("actions", [])

    print(f"Decision:        {decision}")
    print(f"Reason:          {reason}")
    print(f"Final Status:    {final_status}")
    print(f"Amount Recovered: INR {amount_rec:.2f}")
    print(f"Actions Executed ({len(actions)}):")
    for act in actions:
        tool_name = act.get("tool") or act.get("action_type", "unknown")
        act_status = act.get("status") or act.get("result", "done")
        print(f"  - {tool_name}: {act_status}")

    print("=" * 60)


if __name__ == "__main__":
    main()
