"""Structural tests for the advanced benchmark only; no agent execution."""

from collections import Counter

from .dataset import (
    CATEGORY_COUNTS, EVALUATION_CASES, VALID_AMOUNT_EXPECTATIONS,
    VALID_CASE_STATUSES, VALID_EXECUTED_ACTIONS,
)


def test_dataset_has_exactly_thirty_unique_stable_cases():
    assert len(EVALUATION_CASES) == 30
    assert [case.case_id for case in EVALUATION_CASES] == [f"EVAL-{n:03d}" for n in range(1, 31)]
    assert len({case.case_id for case in EVALUATION_CASES}) == 30


def test_category_distribution_matches_advanced_evaluation_specification():
    assert Counter(case.category for case in EVALUATION_CASES) == CATEGORY_COUNTS


def test_every_case_has_complete_valid_ground_truth():
    for case in EVALUATION_CASES:
        assert case.description and case.payment and case.customer and case.recovery_case and case.policy_config and case.trigger
        assert case.expected_decision in VALID_EXECUTED_ACTIONS | {"stop"}
        assert set(case.expected_executed_actions) <= VALID_EXECUTED_ACTIONS
        assert case.expected_final_case_status in VALID_CASE_STATUSES
        assert case.expected_recovered_amount in VALID_AMOUNT_EXPECTATIONS
        assert isinstance(case.expected_policy_violation, bool)
        assert not (case.expected_recovered_amount == "payment_amount" and case.expected_final_case_status != "RECOVERED")


def test_opt_out_cases_prohibit_recovery_communication():
    opt_out_cases = [case for case in EVALUATION_CASES if case.category == "opt_out"]
    assert all(case.customer["opted_out"] is True for case in opt_out_cases)
    assert all(case.recovery_communication_prohibited for case in opt_out_cases)
    assert all(not case.expected_executed_actions for case in opt_out_cases)


def test_duplicate_cases_define_both_runs_and_final_state():
    for case in (case for case in EVALUATION_CASES if case.category == "duplicate_event"):
        assert case.expected_first_run_actions is not None
        assert case.expected_duplicate_run_actions is not None
        assert case.expected_duplicate_final_case_status in VALID_CASE_STATUSES
