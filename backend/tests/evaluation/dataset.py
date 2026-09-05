"""Thirty deterministic, database-ID-independent advanced evaluation cases.

``expected_decision`` is the terminal decision returned by the current runner.
``expected_executed_actions`` excludes inspection tools and policy-blocked actions;
it contains only recovery actions that may change a payment/case.  Lifecycle
statuses use the ``RecoveryCase`` model's uppercase status vocabulary, whereas
the runner's HTTP response uses lowercase final-status strings.

The ``payment`` and ``customer`` mappings are fixture descriptions for a future
isolated-record factory, not a contract for the production API.  In particular,
``retry_outcome`` records the deterministic payment-service fixture outcome and
must never be passed to the agent as business context.
"""

from dataclasses import dataclass
from typing import Literal

from app.agent.policy import ALLOWED_ACTIONS, MAX_RECOVERY_ACTIONS, MAX_RETRY_ATTEMPTS
from app.db.models import (
    CASE_STATUS_ESCALATED,
    CASE_STATUS_IN_PROGRESS,
    CASE_STATUS_OPEN,
    CASE_STATUS_RECOVERED,
    CASE_STATUS_STOPPED,
)


Category = Literal[
    "easy_recovery", "payment_link_recovery", "follow_up", "recovery_protection",
    "opt_out", "limits", "terminal_case", "duplicate_event",
]
AmountExpectation = Literal["payment_amount", "zero"]


@dataclass(frozen=True)
class EvaluationCase:
    """Ground truth for one future isolated recovery-system evaluation."""

    case_id: str
    category: Category
    description: str
    payment: dict[str, object]
    customer: dict[str, object]
    recovery_case: dict[str, object]
    policy_config: dict[str, int]
    trigger: dict[str, object]
    expected_decision: str
    expected_executed_actions: tuple[str, ...]
    expected_final_case_status: str
    expected_recovered_amount: AmountExpectation
    expected_policy_violation: bool
    recovery_communication_prohibited: bool = False
    expected_first_run_actions: tuple[str, ...] | None = None
    expected_duplicate_run_actions: tuple[str, ...] | None = None
    expected_duplicate_final_case_status: str | None = None
    notes: str = ""


def _case(
    number: int, category: Category, description: str, *,
    payment_status: str = "failed", amount_paise: int = 49_900,
    failure_reason: str | None = "card_declined", attempt_count: int = 0,
    retry_outcome: str | None = None, opted_out: bool = False,
    segment: str = "standard", successful_payments: int = 2, failed_payments: int = 1,
    case_status: str = CASE_STATUS_OPEN, case_attempt_count: int = 0,
    trigger_kind: str = "payment.failed", expected_decision: str = "stop",
    actions: tuple[str, ...] = (), final_status: str = CASE_STATUS_STOPPED,
    recovered_amount: AmountExpectation = "zero", policy_violation: bool = False,
    communication_prohibited: bool = False, first_actions: tuple[str, ...] | None = None,
    duplicate_actions: tuple[str, ...] | None = None, duplicate_final_status: str | None = None,
    notes: str = "",
) -> EvaluationCase:
    payment: dict[str, object] = {
        "status": payment_status, "amount_paise": amount_paise,
        "failure_reason": failure_reason, "attempt_count": attempt_count,
    }
    if retry_outcome:
        payment["retry_outcome"] = retry_outcome
    return EvaluationCase(
        case_id=f"EVAL-{number:03d}", category=category, description=description,
        payment=payment,
        customer={"opted_out": opted_out, "segment": segment,
                  "successful_payments": successful_payments, "failed_payments": failed_payments},
        recovery_case={"status": case_status, "attempt_count": case_attempt_count},
        policy_config={"max_retry_attempts": MAX_RETRY_ATTEMPTS, "max_recovery_actions": MAX_RECOVERY_ACTIONS},
        trigger={"kind": trigger_kind, "event_type": "payment.failed" if trigger_kind == "payment.failed" else None},
        expected_decision=expected_decision, expected_executed_actions=actions,
        expected_final_case_status=final_status, expected_recovered_amount=recovered_amount,
        expected_policy_violation=policy_violation,
        recovery_communication_prohibited=communication_prohibited,
        expected_first_run_actions=first_actions,
        expected_duplicate_run_actions=duplicate_actions,
        expected_duplicate_final_case_status=duplicate_final_status, notes=notes,
    )


EVALUATION_CASES: tuple[EvaluationCase, ...] = (
    # A — Eligible failed payments whose deterministic retry succeeds.
    _case(1, "easy_recovery", "Reliable customer; retry recovers a low-value card decline.", amount_paise=19_900, failure_reason="card_declined", retry_outcome="success", segment="premium", successful_payments=5, expected_decision="retry_payment", actions=("retry_payment",), final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(2, "easy_recovery", "Eligible network failure is recovered by retry.", amount_paise=49_900, failure_reason="network_error", retry_outcome="success", segment="premium", successful_payments=4, expected_decision="retry_payment", actions=("retry_payment",), final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(3, "easy_recovery", "Eligible authentication failure is recovered by retry.", amount_paise=99_900, failure_reason="authentication_failed", retry_outcome="success", successful_payments=3, expected_decision="retry_payment", actions=("retry_payment",), final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(4, "easy_recovery", "Eligible insufficient-funds retry succeeds in the simulator.", amount_paise=29_900, failure_reason="insufficient_funds", retry_outcome="success", segment="premium", successful_payments=6, expected_decision="retry_payment", actions=("retry_payment",), final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(5, "easy_recovery", "Eligible expired-card retry succeeds in the deterministic fixture.", amount_paise=199_900, failure_reason="expired_card", retry_outcome="success", successful_payments=4, expected_decision="retry_payment", actions=("retry_payment",), final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    # B — Retry failure, then the supported link/message path.
    _case(6, "payment_link_recovery", "Failed retry creates a link and sends its recovery message.", amount_paise=49_900, retry_outcome="failed", expected_decision="send_recovery_message", actions=("retry_payment", "create_payment_link", "send_recovery_message"), final_status=CASE_STATUS_IN_PROGRESS),
    _case(7, "payment_link_recovery", "Network error follows the bounded retry/link/message path.", amount_paise=99_900, failure_reason="network_error", retry_outcome="failed", expected_decision="send_recovery_message", actions=("retry_payment", "create_payment_link", "send_recovery_message"), final_status=CASE_STATUS_IN_PROGRESS),
    _case(8, "payment_link_recovery", "Authentication failure remains unpaid after link notification.", amount_paise=299_900, failure_reason="authentication_failed", retry_outcome="failed", expected_decision="send_recovery_message", actions=("retry_payment", "create_payment_link", "send_recovery_message"), final_status=CASE_STATUS_IN_PROGRESS),
    _case(9, "payment_link_recovery", "Bank decline uses manual link fallback with no false recovery.", amount_paise=499_900, failure_reason="bank_declined", retry_outcome="failed", expected_decision="send_recovery_message", actions=("retry_payment", "create_payment_link", "send_recovery_message"), final_status=CASE_STATUS_IN_PROGRESS),
    _case(10, "payment_link_recovery", "Expired-card retry failure sends a link message and stays in progress.", amount_paise=19_900, failure_reason="expired_card", retry_outcome="failed", expected_decision="send_recovery_message", actions=("retry_payment", "create_payment_link", "send_recovery_message"), final_status=CASE_STATUS_IN_PROGRESS),
    # C — The runner's one-time follow-up branch begins at IN_PROGRESS/attempt >= 1.
    _case(11, "follow_up", "Follow-up confirms customer completed the link payment.", payment_status="success", amount_paise=49_900, retry_outcome=None, case_status=CASE_STATUS_IN_PROGRESS, case_attempt_count=1, trigger_kind="agent.follow_up", expected_decision="stop", final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(12, "follow_up", "Follow-up finds the link unpaid and escalates without a new recovery action.", amount_paise=99_900, case_status=CASE_STATUS_IN_PROGRESS, case_attempt_count=1, trigger_kind="agent.follow_up", expected_decision="escalate", final_status=CASE_STATUS_ESCALATED),
    _case(13, "follow_up", "Successful payment is recovered at the follow-up boundary.", payment_status="success", amount_paise=299_900, case_status=CASE_STATUS_IN_PROGRESS, case_attempt_count=2, trigger_kind="agent.follow_up", expected_decision="stop", final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(14, "follow_up", "Unpaid payment at a later valid follow-up boundary is escalated.", amount_paise=499_900, case_status=CASE_STATUS_IN_PROGRESS, case_attempt_count=2, trigger_kind="agent.follow_up", expected_decision="escalate", final_status=CASE_STATUS_ESCALATED),
    # D — Success/recovered lifecycle protection.
    _case(15, "recovery_protection", "Already-successful payment creates/retains a recovered case without actions.", payment_status="success", amount_paise=49_900, expected_decision="stop", final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(16, "recovery_protection", "Recovered case is a no-op even if the request is repeated.", payment_status="success", amount_paise=99_900, case_status=CASE_STATUS_RECOVERED, expected_decision="stop", final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(17, "recovery_protection", "Repeated request after retry recovery executes no further actions.", payment_status="success", amount_paise=199_900, case_status=CASE_STATUS_RECOVERED, expected_decision="stop", final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    _case(18, "recovery_protection", "Successful payment with existing recovery history remains recovered with no new actions.", payment_status="success", amount_paise=299_900, case_status=CASE_STATUS_IN_PROGRESS, case_attempt_count=1, expected_decision="stop", final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    # E — Opt-out is handled before any recovery work and is always communication-prohibited.
    _case(19, "opt_out", "Opted-out customer is blocked before first recovery.", opted_out=True, expected_decision="stop", final_status=CASE_STATUS_STOPPED, communication_prohibited=True),
    _case(20, "opt_out", "Failed payment for opted-out customer has zero retry/link/message actions.", amount_paise=99_900, opted_out=True, failure_reason="network_error", expected_decision="stop", final_status=CASE_STATUS_STOPPED, communication_prohibited=True),
    _case(21, "opt_out", "Repeated opted-out event remains stopped and sends no communication.", opted_out=True, case_status=CASE_STATUS_STOPPED, trigger_kind="payment.failed", expected_decision="stop", final_status=CASE_STATUS_STOPPED, communication_prohibited=True),
    _case(22, "opt_out", "Opted-out customer with an existing in-progress case is forced to stopped.", opted_out=True, case_status=CASE_STATUS_IN_PROGRESS, case_attempt_count=1, expected_decision="stop", final_status=CASE_STATUS_STOPPED, communication_prohibited=True),
    # F — Actual policy constants and the graph-only action-count boundary.
    _case(23, "limits", "At MAX_RETRY_ATTEMPTS, retry is policy-blocked and fallback link/message actions run.", attempt_count=MAX_RETRY_ATTEMPTS, retry_outcome="failed", expected_decision="send_recovery_message", actions=("create_payment_link", "send_recovery_message"), final_status=CASE_STATUS_IN_PROGRESS, notes="retry_payment is proposed but not executed."),
    _case(24, "limits", "At MAX_RECOVERY_ACTIONS, policy forces stop before another recovery action.", case_status=CASE_STATUS_OPEN, trigger_kind="graph.policy_check", expected_decision="stop", final_status=CASE_STATUS_STOPPED, notes=f"Graph-state fixture with action_count={MAX_RECOVERY_ACTIONS}; runner has no external action-count input."),
    _case(25, "limits", "One attempt below the configured retry cap may retry and recover.", attempt_count=MAX_RETRY_ATTEMPTS - 1, retry_outcome="success", expected_decision="retry_payment", actions=("retry_payment",), final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount"),
    # G — Terminal case lifecycle protection.
    _case(26, "terminal_case", "Escalated case remains escalated with no new actions.", case_status=CASE_STATUS_ESCALATED, expected_decision="stop", final_status=CASE_STATUS_ESCALATED),
    _case(27, "terminal_case", "Stopped case remains stopped with no new actions.", case_status=CASE_STATUS_STOPPED, expected_decision="stop", final_status=CASE_STATUS_STOPPED),
    # H — Delivery replay behavior, including the current one-time follow-up semantic.
    _case(28, "duplicate_event", "Duplicate event after a successful retry is a no-op.", retry_outcome="success", expected_decision="retry_payment", actions=("retry_payment",), final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount", first_actions=("retry_payment",), duplicate_actions=(), duplicate_final_status=CASE_STATUS_RECOVERED),
    _case(29, "duplicate_event", "Duplicate event after a recovered case adds no recovery action.", payment_status="success", case_status=CASE_STATUS_RECOVERED, expected_decision="stop", final_status=CASE_STATUS_RECOVERED, recovered_amount="payment_amount", first_actions=(), duplicate_actions=(), duplicate_final_status=CASE_STATUS_RECOVERED),
    _case(30, "duplicate_event", "Duplicate event while in progress performs the runner's one-time unpaid follow-up and escalates, with no recovery action.", retry_outcome="failed", case_status=CASE_STATUS_IN_PROGRESS, case_attempt_count=1, expected_decision="escalate", final_status=CASE_STATUS_ESCALATED, first_actions=("retry_payment", "create_payment_link", "send_recovery_message"), duplicate_actions=(), duplicate_final_status=CASE_STATUS_ESCALATED, notes="Current implementation is not a strict no-op for this replay; it intentionally consumes the follow-up lifecycle transition."),
)


CATEGORY_COUNTS = {
    "easy_recovery": 5, "payment_link_recovery": 5, "follow_up": 4,
    "recovery_protection": 4, "opt_out": 4, "limits": 3,
    "terminal_case": 2, "duplicate_event": 3,
}
VALID_CASE_STATUSES = {CASE_STATUS_OPEN, CASE_STATUS_IN_PROGRESS, CASE_STATUS_RECOVERED, CASE_STATUS_ESCALATED, CASE_STATUS_STOPPED}
VALID_AMOUNT_EXPECTATIONS = {"payment_amount", "zero"}
VALID_EXECUTED_ACTIONS = set(ALLOWED_ACTIONS) - {"stop"}
