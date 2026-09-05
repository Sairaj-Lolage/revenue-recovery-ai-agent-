from dataclasses import replace

from app.evaluation.advanced import aggregate_results, run_advanced_evaluation, score_case
from tests.evaluation.dataset import EVALUATION_CASES


def _actual(case, **overrides):
    value = {
        "decision": case.expected_decision,
        "actions": list(case.expected_executed_actions),
        "state": case.expected_final_case_status,
        "amount": case.payment["amount_paise"] if case.expected_recovered_amount == "payment_amount" else 0,
    }
    value.update(overrides)
    return value


def test_perfect_behavior_receives_full_component_scores():
    case = EVALUATION_CASES[0]
    result = score_case(case, _actual(case))
    assert result.case_passed
    assert all((result.decision_correct, result.actions_correct, result.final_state_correct, result.safety_correct, result.amount_correct))


def test_scoring_detects_decision_actions_state_and_amount_errors():
    case = EVALUATION_CASES[0]
    result = score_case(case, _actual(case, decision="stop", actions=[], state="STOPPED", amount=0))
    assert not result.decision_correct and not result.actions_correct and not result.final_state_correct and not result.amount_correct
    assert not result.case_passed


def test_safety_violation_is_visible_for_opt_out_communication():
    case = EVALUATION_CASES[18]
    result = score_case(case, _actual(case, actions=["send_recovery_message"]))
    assert "OPT_OUT_COMMUNICATION" in result.safety_violations
    assert not result.safety_correct


def test_duplicate_behavior_is_scored_against_ground_truth_including_eval_030():
    case = EVALUATION_CASES[29]
    result = score_case(case, _actual(case, first_actions=list(case.expected_first_run_actions or ()), duplicate_actions=[], duplicate_state="ESCALATED"))
    assert result.idempotency_correct is True


def test_aggregate_metrics_and_confusion_matrix_are_deterministic():
    case = EVALUATION_CASES[0]
    good = score_case(case, _actual(case))
    bad = score_case(case, _actual(case, state="STOPPED"))
    summary = aggregate_results([good, bad])
    assert summary.decision_accuracy == 1.0
    assert summary.final_state_accuracy == 0.5
    assert summary.confusion_matrix == {"RECOVERED->RECOVERED": 1, "RECOVERED->STOPPED": 1}


def test_blocked_execution_is_not_scored_as_agent_failure():
    case = EVALUATION_CASES[0]
    result = score_case(case, {"blocked_reason": "fixture unavailable"})
    summary = aggregate_results([result])
    assert result.execution_status == "blocked"
    assert summary.blocked_cases == 1 and summary.decision_accuracy is None


def test_runner_executes_all_30_cases_and_preserves_eval_030_follow_up_ground_truth(tmp_path):
    output = tmp_path / "results.json"
    summary = run_advanced_evaluation(output)
    eval_030 = next(result for result in summary.case_results if result.case_id == "EVAL-030")
    assert summary.executed_cases == 30 and summary.blocked_cases == 0
    assert eval_030.idempotency_correct is True and eval_030.actual_final_state == "ESCALATED"
    assert output.exists()
