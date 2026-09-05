from app.evaluation.analysis import analyze_recovery_quality, classify_recovery_quality, run_advanced_quality_analysis
from app.evaluation.advanced import AdvancedEvaluationSummary, run_advanced_evaluation, score_case
from tests.evaluation.dataset import EVALUATION_CASES


def _quality():
    return analyze_recovery_quality(run_advanced_evaluation())


def test_quality_metrics_preserve_safety_and_financial_correctness():
    quality = _quality()["quality_summary"]
    assert quality["safety"]["total_violations"] == 0
    assert quality["financial"]["difference_paise"] == 0
    assert quality["financial"]["incorrect_recovered_amount_cases"] == 0


def test_unsafe_actions_counts_each_prohibited_execution_not_just_one_violation():
    case = EVALUATION_CASES[18]  # opted-out customer
    result = score_case(case, {
        "decision": "send_recovery_message",
        "actions": ["retry_payment", "create_payment_link", "send_recovery_message"],
        "state": case.expected_final_case_status,
        "amount": 0,
    })
    quality = analyze_recovery_quality(AdvancedEvaluationSummary(
        total_cases=1, executed_cases=1, blocked_cases=0, passed_cases=0, failed_cases=1,
        decision_accuracy=0.0, action_accuracy=0.0, final_state_accuracy=1.0,
        safety_accuracy=0.0, idempotency_accuracy=None, overall_score=None,
        recovery_amount_matches=1, recovery_amount_cases=1,
        total_expected_recovered_paise=0, total_actual_recovered_paise=0,
        recovery_amount_absolute_difference=0, safety_violations_total=len(result.safety_violations),
        confusion_matrix={"STOPPED->STOPPED": 1}, case_results=[result],
    ))
    assert quality["quality_summary"]["safety"]["unsafe_actions"] == 3


def test_recovery_opportunity_capture_includes_the_retry_limit_message():
    opportunity = _quality()["quality_summary"]["recovery_opportunity"]
    assert opportunity == {"expected_actionable_opportunities": 24, "captured_opportunities": 24, "missed_opportunities": 0, "capture_percentage": 1.0}


def test_quality_classification_marks_eval_023_fixed_and_eval_024_as_harness_limited():
    quality = _quality()
    by_id = {item["case_id"]: item for item in quality["recovery_quality_cases"]}
    assert (by_id["EVAL-023"]["classification"], by_id["EVAL-023"]["severity"]) == ("PASS", "NONE")
    assert (by_id["EVAL-024"]["classification"], by_id["EVAL-024"]["severity"]) == ("EVALUATION_HARNESS_LIMITATION", "LOW")


def test_quality_separates_production_defect_from_harness_limitation_and_assesses_mvp():
    quality = _quality()["quality_summary"]
    assert quality["production_defects"] == 0 and quality["evaluation_harness_limitations"] == 1
    assert quality["mvp_assessment"] == "MVP_ACCEPTABLE"


def test_quality_json_runner_is_deterministic(tmp_path):
    output = tmp_path / "quality.json"
    quality = run_advanced_quality_analysis(output)
    assert output.exists()
    assert quality["quality_summary"]["failure_severity"]["MEDIUM"] == 0
