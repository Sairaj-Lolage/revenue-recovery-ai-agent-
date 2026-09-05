"""
backend/app/db/seed.py
======================
Deterministic synthetic data generator for the Revenue Recovery Agent.

Produces:
  - 50 customers  (4 behaviour profiles)
  - 150 payments  (90 successful + 60 failed with explicit recovery scenarios)

The ``recovery_scenario`` field on failed payments is *evaluation metadata only*
and must NEVER be supplied to the agent when it makes recovery decisions.

Usage::

    python -m app.db.seed          # from backend/
    python backend/app/db/seed.py  # from project root
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.database import SessionLocal, engine, init_db
from app.db.models import (
    Customer,
    Payment,
    PAYMENT_STATUS_SUCCESS,
    PAYMENT_STATUS_FAILED,
)

# ── Reproducibility ──────────────────────────────────────────────────────────

SEED = 42
TARGET_CUSTOMERS = 50
TARGET_PAYMENTS = 150

# Payments with amount_paise >= this threshold require human escalation.
AUTO_RECOVERY_THRESHOLD_PAISE = 1_000_000  # ₹10,000

# ── Synthetic data pools ─────────────────────────────────────────────────────

FIRST_NAMES = [
    "Aarav", "Aditi", "Arjun", "Anjali", "Bhavna", "Dev", "Divya", "Gaurav",
    "Isha", "Karan", "Kavya", "Manish", "Meera", "Nikhil", "Priya", "Rahul",
    "Riya", "Rohan", "Sanya", "Suresh", "Tanvi", "Uday", "Vikram", "Vishal",
    "Yamini", "Zara", "Amit", "Ananya", "Deepak", "Harsh", "Ishaan", "Jaya",
    "Krish", "Lakshmi", "Maya", "Neeraj", "Pooja", "Rajesh", "Sakshi", "Tarun",
    "Uma", "Varun", "Sneha", "Ritesh", "Pallavi", "Mohit", "Leela", "Kiran",
    "Juhi", "Hemant",
]

LAST_NAMES = [
    "Sharma", "Patel", "Gupta", "Singh", "Kumar", "Verma", "Joshi", "Shah",
    "Mehta", "Nair", "Iyer", "Reddy", "Rao", "Pillai", "Desai", "Malhotra",
    "Agarwal", "Kapoor", "Bose", "Das",
]

# Realistic INR SaaS/e-commerce amounts (paise)
COMMON_AMOUNTS = [19900, 29900, 49900, 99900, 199900, 299900, 499900, 999900]
HIGH_VALUE_AMOUNTS = [1049900, 1499900, 1999900, 2499900, 4999900]

FAILURE_REASONS = [
    "insufficient_funds",
    "card_declined",
    "network_error",
    "authentication_failed",
    "expired_card",
    "bank_declined",
]

# ── Profile definitions ──────────────────────────────────────────────────────
# (profile_name, segment, base_successful_payments, opted_out)
_PROFILE_SEQUENCE: list[tuple[str, str, int, bool]] = (
    [("RELIABLE",            "premium",  3, False)] * 15 +
    [("OCCASIONAL_FAILURE",  "standard", 2, False)] * 13 +
    [("HIGH_RISK",           "at_risk",  1, False)] * 10 +
    [("NEW_CUSTOMER",        "new",      1, False)] * 3  +   # 3 new customers with 1 prior payment
    [("NEW_CUSTOMER",        "new",      0, False)] * 6  +   # 6 brand-new customers with no history
    [("OPTED_OUT",           "standard", 2, True)]  * 3
)
assert len(_PROFILE_SEQUENCE) == TARGET_CUSTOMERS


# ── Builder helpers ───────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(rng: random.Random, lo: int, hi: int) -> datetime:
    return _utcnow() - timedelta(days=rng.randint(lo, hi), hours=rng.randint(0, 23))


def _build_customers(rng: random.Random) -> list[dict]:
    """Return a list of 50 customer attribute dicts."""
    last_pool = LAST_NAMES[:]
    records = []
    for i, (profile, segment, base_ok, opted_out) in enumerate(_PROFILE_SEQUENCE):
        first = FIRST_NAMES[i]
        last  = rng.choice(last_pool)
        slug  = f"{first.lower()}.{last.lower()}{i:02d}"
        records.append({
            "name":                 f"{first} {last}",
            "email":                f"{slug}@synth-merchant.example",
            "phone":                f"+91{9000000000 + i * 7 + rng.randint(1, 6):010d}",
            "segment":              segment,
            "opted_out":            opted_out,
            # history counters will be set after payments are generated
            "_profile":             profile,
            "_base_successful":     base_ok,
        })
    return records


def _assign_scenarios(rng: random.Random) -> list[tuple[int, str, int]]:
    """
    Return a list of (customer_index, scenario, attempt_count) for the
    60 failed payments.

    Customer index bands:
      0-14   RELIABLE
      15-27  OCCASIONAL_FAILURE
      28-37  HIGH_RISK
      38-46  NEW_CUSTOMER
      47-49  OPTED_OUT
    """
    assignments: list[tuple[int, str, int]] = []

    # EASY_RECOVERY — 15: one per RELIABLE customer
    for idx in range(15):
        assignments.append((idx, "EASY_RECOVERY", 1))

    # PAYMENT_LINK_RECOVERY — 10: from first 10 OCCASIONAL_FAILURE
    for idx in range(15, 25):
        assignments.append((idx, "PAYMENT_LINK_RECOVERY", 1))

    # REPEATED_FAILURE — 9: spread across HIGH_RISK customers
    hr_indices = list(range(28, 37))
    rng.shuffle(hr_indices)
    for idx in hr_indices:
        attempts = rng.randint(2, 3)
        assignments.append((idx, "REPEATED_FAILURE", attempts))

    # HIGH_VALUE — 8: mix of RELIABLE (4) + OCCASIONAL_FAILURE (4)
    hv_cust = list(range(0, 4)) + list(range(15, 19))
    for idx in hv_cust:
        assignments.append((idx, "HIGH_VALUE", 1))

    # OPTED_OUT — 5: from the 3 opted-out customers (some get 2)
    opted_indices = [47, 47, 48, 49, 49]
    for idx in opted_indices:
        assignments.append((idx, "OPTED_OUT", 1))

    # UNRECOVERABLE — 13: HIGH_RISK customer 37 + repeat from HIGH_RISK pool
    unr_pool = [37] + list(range(28, 37)) + [25, 26, 27]
    for idx in unr_pool[:13]:
        assignments.append((idx, "UNRECOVERABLE", rng.randint(1, 3)))

    assert len(assignments) == 60, f"Expected 60 failed scenarios, got {len(assignments)}"
    return assignments


# ── Main seed function ────────────────────────────────────────────────────────

def seed(db: Session) -> dict:
    """
    Clear existing synthetic data and insert fresh deterministic dataset.
    Returns a summary dict.
    """
    rng = random.Random(SEED)

    # ── Wipe existing data (FK order) ────────────────────────────────────────
    from app.db.models import AuditLog, RecoveryAction, RecoveryCase
    db.query(AuditLog).delete()
    db.query(RecoveryAction).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.query(Customer).delete()
    db.commit()

    # ── Build customer specs ─────────────────────────────────────────────────
    cust_specs = _build_customers(rng)
    scenario_assignments = _assign_scenarios(rng)

    # Index: customer_index → list of scenario tuples that land on it
    from collections import defaultdict
    scenario_map: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for cust_idx, scenario, attempts in scenario_assignments:
        scenario_map[cust_idx].append((scenario, attempts))

    # ── Insert customers ─────────────────────────────────────────────────────
    customers: list[Customer] = []
    for spec in cust_specs:
        c = Customer(
            name=spec["name"],
            email=spec["email"],
            phone=spec["phone"],
            segment=spec["segment"],
            opted_out=spec["opted_out"],
            total_paid_paise=0,
            successful_payments=0,
            failed_payments=0,
            created_at=_days_ago(rng, 60, 180),
        )
        db.add(c)
        customers.append(c)
    db.flush()

    # ── Insert payments ───────────────────────────────────────────────────────
    payments: list[Payment] = []

    for i, (spec, customer) in enumerate(zip(cust_specs, customers)):
        # Background successful payments
        for _ in range(spec["_base_successful"]):
            amount = rng.choice(COMMON_AMOUNTS)
            p = Payment(
                customer_id=customer.id,
                amount_paise=amount,
                currency="INR",
                status=PAYMENT_STATUS_SUCCESS,
                attempt_count=1,
                recovery_scenario=None,
                created_at=_days_ago(rng, 5, 45),
                updated_at=_days_ago(rng, 1, 5),
            )
            db.add(p)
            payments.append(p)
            customer.successful_payments += 1
            customer.total_paid_paise += amount

        # Scenario-specific failed payments
        for scenario, attempt_count in scenario_map.get(i, []):
            if scenario == "HIGH_VALUE":
                amount = rng.choice(HIGH_VALUE_AMOUNTS)
            else:
                amount = rng.choice(COMMON_AMOUNTS)

            # Guarantee all failure reasons appear by cycling them
            reason_idx = len([p for p in payments if p.status == PAYMENT_STATUS_FAILED]) % len(FAILURE_REASONS)
            reason = FAILURE_REASONS[reason_idx]

            p = Payment(
                customer_id=customer.id,
                amount_paise=amount,
                currency="INR",
                status=PAYMENT_STATUS_FAILED,
                failure_reason=reason,
                attempt_count=attempt_count,
                recovery_scenario=scenario,
                created_at=_days_ago(rng, 1, 7),
                updated_at=_days_ago(rng, 0, 1),
            )
            db.add(p)
            payments.append(p)
            customer.failed_payments += 1

    db.commit()

    # ── Verify counts ─────────────────────────────────────────────────────────
    assert len(customers) == TARGET_CUSTOMERS, f"Expected {TARGET_CUSTOMERS} customers"
    assert len(payments) == TARGET_PAYMENTS,   f"Expected {TARGET_PAYMENTS} payments"

    # ── Build summary ─────────────────────────────────────────────────────────
    successful   = [p for p in payments if p.status == PAYMENT_STATUS_SUCCESS]
    failed       = [p for p in payments if p.status == PAYMENT_STATUS_FAILED]
    at_risk_paise = sum(p.amount_paise for p in failed)

    scenario_counts: dict[str, int] = {}
    for scenario in ["EASY_RECOVERY", "PAYMENT_LINK_RECOVERY", "REPEATED_FAILURE",
                     "HIGH_VALUE", "OPTED_OUT", "UNRECOVERABLE"]:
        scenario_counts[scenario] = sum(1 for p in failed if p.recovery_scenario == scenario)

    return {
        "customers":         len(customers),
        "payments":          len(payments),
        "successful":        len(successful),
        "failed":            len(failed),
        "at_risk_paise":     at_risk_paise,
        "scenario_counts":   scenario_counts,
    }


def print_summary(summary: dict) -> None:
    at_risk_rupees = summary["at_risk_paise"] / 100
    print()
    print("══════════════════════════════════════════")
    print("   AI Revenue Recovery — Seed Complete")
    print("══════════════════════════════════════════")
    print(f"Customers created   : {summary['customers']}")
    print(f"Payments created    : {summary['payments']}")
    print(f"  Successful        : {summary['successful']}")
    print(f"  Failed            : {summary['failed']}")
    print(f"Revenue at risk     : ₹{at_risk_rupees:,.2f}")
    print()
    print("Scenario distribution:")
    for scenario, count in summary["scenario_counts"].items():
        print(f"  {scenario:<26}: {count}")
    print("══════════════════════════════════════════")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    with SessionLocal() as db:
        summary = seed(db)
    print_summary(summary)
    sys.exit(0)
