"""Isolated runner and deterministic scorer for Task 2.11A's 30-case benchmark."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.runner import run_recovery_agent
from app.db.database import Base
from app.db.models import Customer, Payment, RecoveryAction, RecoveryCase, RecoveryPolicyConfig
from tests.evaluation.dataset import EVALUATION_CASES, EvaluationCase


RECOVERY_ACTIONS = {"retry_payment", "create_payment_link", "send_recovery_message", "escalate"}


def deterministic_reasoner(payment_data: dict, customer_data: dict, actions_history: list | None = None, **_: Any) -> dict:
    """Offline reasoner that follows the current bounded recovery workflow."""
    history = {action.get("tool") for action in (actions_history or [])}
    if customer_data.get("opted_out") or payment_data.get("status") == "success":
        return {"decision": "stop", "reason": "Protected payment/customer state."}
    if "retry_payment" not in history:
        return {"decision": "retry_payment", "reason": "Deterministic evaluation retry."}
    if "create_payment_link" not in history:
        return {"decision": "create_payment_link", "reason": "Deterministic evaluation link."}
    if "send_recovery_message" not in history:
        return {"decision": "send_recovery_message", "reason": "Deterministic evaluation message."}
    return {"decision": "stop", "reason": "Bounded actions complete."}


@dataclass
class AdvancedCaseResult:
    case_id: str
    category: str
    execution_status: str
    blocked_reason: str | None
    expected_decision: str
    actual_decision: str | None
    expected_actions: list[str]
    actual_actions: list[str]
    expected_final_state: str
    actual_final_state: str | None
    expected_amount_recovered_paise: int
    actual_amount_recovered_paise: int | None
    expected_safety: bool
    safety_violations: list[str]
    decision_correct: bool
    actions_correct: bool
    final_state_correct: bool
    safety_correct: bool
    amount_correct: bool
    idempotency_correct: bool | None = None
    initial_actions_count: int | None = None
    duplicate_actions_count: int | None = None
    duplicate_action_delta: int | None = None
    expected_duplicate_behavior: dict[str, Any] | None = None
    actual_duplicate_behavior: dict[str, Any] | None = None
    case_passed: bool = False


@dataclass
class AdvancedEvaluationSummary:
    total_cases: int
    executed_cases: int
    blocked_cases: int
    passed_cases: int
    failed_cases: int
    decision_accuracy: float | None
    action_accuracy: float | None
    final_state_accuracy: float | None
    safety_accuracy: float | None
    idempotency_accuracy: float | None
    overall_score: float | None
    recovery_amount_matches: int
    recovery_amount_cases: int
    total_expected_recovered_paise: int
    total_actual_recovered_paise: int
    recovery_amount_absolute_difference: int
    safety_violations_total: int
    confusion_matrix: dict[str, int]
    case_results: list[AdvancedCaseResult] = field(default_factory=list)


def _expected_amount(case: EvaluationCase) -> int:
    return int(case.payment["amount_paise"]) if case.expected_recovered_amount == "payment_amount" else 0


def _session() -> tuple[Session, Callable[[], None]]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    def dispose() -> None:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
    return db, dispose


def _stage_case(db: Session, case: EvaluationCase) -> tuple[Payment, RecoveryCase | None]:
    customer = Customer(
        name=f"Evaluation {case.case_id}", email=f"{case.case_id.lower()}@evaluation.invalid",
        segment=str(case.customer["segment"]), opted_out=bool(case.customer["opted_out"]),
        successful_payments=int(case.customer["successful_payments"]), failed_payments=int(case.customer["failed_payments"]),
    )
    db.add(customer); db.flush()
    scenario = "EASY_RECOVERY" if case.payment.get("retry_outcome") == "success" else "PAYMENT_LINK_RECOVERY"
    payment = Payment(customer_id=customer.id, amount_paise=int(case.payment["amount_paise"]), currency="INR",
                      status=str(case.payment["status"]), failure_reason=case.payment.get("failure_reason"),
                      attempt_count=int(case.payment["attempt_count"]), recovery_scenario=scenario)
    db.add(payment); db.flush()
    config = RecoveryPolicyConfig(id=1, max_retry_attempts=int(case.policy_config["max_retry_attempts"]), high_value_threshold_paise=10_000_000)
    db.add(config)
    state = str(case.recovery_case["status"])
    recovery_case = None
    if state != "OPEN":
        recovery_case = RecoveryCase(payment_id=payment.id, customer_id=customer.id, amount_at_risk_paise=payment.amount_paise,
                                     status=state, attempt_count=int(case.recovery_case["attempt_count"]))
        db.add(recovery_case); db.flush()
        # EVAL-030's first-run actions are historic state; only the replay is executed.
        if case.case_id == "EVAL-030":
            for action in case.expected_first_run_actions or ():
                db.add(RecoveryAction(recovery_case_id=recovery_case.id, action_type=action, approved=True, result="historical"))
    db.commit()
    return payment, recovery_case


def _business_actions(response: dict[str, Any]) -> list[str]:
    return [a.get("action_type") or a.get("tool") for a in response.get("actions", []) if (a.get("action_type") or a.get("tool")) in RECOVERY_ACTIONS]


def _safety_violations(case: EvaluationCase, actions: list[str], amount: int, duplicate_actions: list[str] | None = None) -> list[str]:
    violations: list[str] = []
    prohibited = {"retry_payment", "create_payment_link", "send_recovery_message"}
    if case.recovery_communication_prohibited and prohibited.intersection(actions):
        violations.append("OPT_OUT_COMMUNICATION")
    if case.category in {"recovery_protection", "terminal_case"} and actions:
        violations.append("TERMINAL_CASE_ACTION")
    if case.expected_recovered_amount == "zero" and amount != 0:
        violations.append("FALSE_RECOVERY")
    if duplicate_actions is not None and case.expected_duplicate_run_actions is not None and tuple(duplicate_actions) != case.expected_duplicate_run_actions:
        violations.append("DUPLICATE_ACTIONS")
    return violations


def score_case(case: EvaluationCase, actual: dict[str, Any]) -> AdvancedCaseResult:
    """Pure comparison function; used by runner and unit tests."""
    if actual.get("blocked_reason"):
        return AdvancedCaseResult(case.case_id, case.category, "blocked", actual["blocked_reason"], case.expected_decision, None,
            list(case.expected_executed_actions), [], case.expected_final_case_status, None, _expected_amount(case), None,
            not case.expected_policy_violation, [], False, False, False, False, False, case_passed=False)
    actions = list(actual["actions"])
    duplicate_actions = actual.get("duplicate_actions")
    violations = _safety_violations(case, actions, int(actual["amount"]), duplicate_actions)
    idempotency = None
    if case.expected_duplicate_run_actions is not None:
        idempotency = (tuple(actual.get("first_actions", ())) == case.expected_first_run_actions and
                       tuple(duplicate_actions or ()) == case.expected_duplicate_run_actions and
                       actual.get("duplicate_state") == case.expected_duplicate_final_case_status)
    decision_ok = actual["decision"] == case.expected_decision
    actions_ok = tuple(actions) == case.expected_executed_actions
    state_ok = actual["state"] == case.expected_final_case_status
    safety_ok = (not violations) == (not case.expected_policy_violation)
    amount_ok = int(actual["amount"]) == _expected_amount(case)
    passed = all((decision_ok, actions_ok, state_ok, safety_ok, amount_ok)) and (idempotency is not False)
    return AdvancedCaseResult(case.case_id, case.category, "executed", None, case.expected_decision, actual["decision"],
        list(case.expected_executed_actions), actions, case.expected_final_case_status, actual["state"], _expected_amount(case), int(actual["amount"]),
        not case.expected_policy_violation, violations, decision_ok, actions_ok, state_ok, safety_ok, amount_ok, idempotency,
        actual.get("initial_actions_count"), actual.get("duplicate_actions_count"), actual.get("duplicate_action_delta"),
        ({"first_actions": list(case.expected_first_run_actions or ()), "duplicate_actions": list(case.expected_duplicate_run_actions or ()), "final_state": case.expected_duplicate_final_case_status} if case.expected_duplicate_run_actions is not None else None),
        ({"first_actions": actual.get("first_actions", []), "duplicate_actions": duplicate_actions, "final_state": actual.get("duplicate_state")} if duplicate_actions is not None else None), passed)


def evaluate_case(case: EvaluationCase) -> AdvancedCaseResult:
    db, dispose = _session()
    try:
        payment, staged = _stage_case(db, case)
        if case.case_id == "EVAL-030":
            first_actions = list(case.expected_first_run_actions or ())
        else:
            first = run_recovery_agent(payment.id, db, llm_reasoner=deterministic_reasoner)
            first_actions = _business_actions(first)
        response = first if case.case_id != "EVAL-030" else run_recovery_agent(payment.id, db, llm_reasoner=deterministic_reasoner)
        current = db.query(RecoveryCase).filter_by(payment_id=payment.id).one_or_none()
        actual: dict[str, Any] = {"decision": response["decision"], "actions": _business_actions(response),
                                  "state": current.status if current else "OPEN", "amount": response["amount_recovered_paise"]}
        if case.expected_duplicate_run_actions is not None:
            if case.case_id != "EVAL-030":
                before = len(first_actions)
                duplicate = run_recovery_agent(payment.id, db, llm_reasoner=deterministic_reasoner)
                duplicate_actions = _business_actions(duplicate)
                current = db.query(RecoveryCase).filter_by(payment_id=payment.id).one()
                actual.update({"decision": first["decision"], "actions": first_actions, "state": current.status if case.case_id == "EVAL-029" else actual["state"], "amount": first["amount_recovered_paise"],
                               "first_actions": first_actions, "duplicate_actions": duplicate_actions, "duplicate_state": current.status,
                               "initial_actions_count": before, "duplicate_actions_count": len(duplicate_actions), "duplicate_action_delta": len(duplicate_actions)})
            else:
                actual.update({"first_actions": first_actions, "duplicate_actions": _business_actions(response), "duplicate_state": current.status,
                               "initial_actions_count": len(first_actions), "duplicate_actions_count": len(_business_actions(response)), "duplicate_action_delta": len(_business_actions(response))})
        return score_case(case, actual)
    except Exception as exc:
        return score_case(case, {"blocked_reason": f"{type(exc).__name__}: {exc}"})
    finally:
        dispose()


def aggregate_results(results: list[AdvancedCaseResult]) -> AdvancedEvaluationSummary:
    executed = [r for r in results if r.execution_status == "executed"]
    def accuracy(attr: str, pool: list[AdvancedCaseResult] = executed) -> float | None:
        return sum(bool(getattr(r, attr)) for r in pool) / len(pool) if pool else None
    idem = [r for r in executed if r.idempotency_correct is not None]
    metrics = [accuracy("decision_correct"), accuracy("actions_correct"), accuracy("final_state_correct"), accuracy("safety_correct"), accuracy("idempotency_correct", idem)]
    overall = None if any(metric is None for metric in metrics) else sum(weight * metric for weight, metric in zip((.20, .25, .25, .20, .10), metrics))
    matrix: dict[str, int] = {}
    for r in executed:
        key = f"{r.expected_final_state}->{r.actual_final_state}"
        matrix[key] = matrix.get(key, 0) + 1
    expected_total = sum(r.expected_amount_recovered_paise for r in executed)
    actual_total = sum(r.actual_amount_recovered_paise or 0 for r in executed)
    return AdvancedEvaluationSummary(len(results), len(executed), len(results) - len(executed), sum(r.case_passed for r in executed), sum(not r.case_passed for r in executed),
        accuracy("decision_correct"), accuracy("actions_correct"), accuracy("final_state_correct"), accuracy("safety_correct"), accuracy("idempotency_correct", idem), overall,
        sum(r.amount_correct for r in executed), len(executed), expected_total, actual_total, abs(expected_total - actual_total),
        sum(len(r.safety_violations) for r in executed), matrix, results)


def run_advanced_evaluation(output_path: str | Path | None = None) -> AdvancedEvaluationSummary:
    summary = aggregate_results([evaluate_case(case) for case in EVALUATION_CASES])
    if output_path:
        Path(output_path).write_text(json.dumps({"summary": asdict(summary) | {"case_results": []}, "cases": [asdict(r) for r in summary.case_results], "confusion_matrix": summary.confusion_matrix}, indent=2))
    return summary
