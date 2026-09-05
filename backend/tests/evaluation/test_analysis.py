from app.evaluation.analysis import analyze_advanced_evaluation, diagnose_failure
from app.evaluation.advanced import run_advanced_evaluation


def _analysis():
    return analyze_advanced_evaluation(run_advanced_evaluation())


def test_category_safety_financial_and_idempotency_analysis():
    analysis = _analysis()
    assert analysis["category_analysis"]["easy_recovery"]["passed"] == 5
    assert analysis["safety_analysis"]["total_violations"] == 0
    assert analysis["financial_analysis"]["difference_paise"] == 0
    assert analysis["idempotency_analysis"]["accuracy"] == 1.0


def test_lifecycle_action_decision_and_confusion_analysis():
    analysis = _analysis()
    assert analysis["lifecycle_analysis"]["illegal_transitions"] == []
    assert analysis["action_analysis"]["missing_by_action"] == {}
    assert analysis["decision_analysis"]["incorrect_case_ids"] == ["EVAL-024"]
    assert analysis["confusion_matrix"]["RECOVERED->RECOVERED"] == 14


def test_eval_023_and_024_have_evidence_based_distinct_diagnoses():
    assert diagnose_failure("EVAL-023").classification == "PRODUCTION_DEFECT"
    assert diagnose_failure("EVAL-024").classification == "EVALUATION_HARNESS_LIMITATION"


def test_risk_assessment_is_mvp_acceptable_but_not_production_ready():
    assessment = _analysis()["mvp_readiness"]
    assert assessment["overall_mvp_risk"] == "MVP_ACCEPTABLE"
    assert assessment["mvp_ready"] and not assessment["production_ready"]
