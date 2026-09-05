"""
backend/app/evaluation/report.py
================================
Generates human-readable evaluation reports for the AI Revenue Recovery Agent.
"""

from app.evaluation.evaluator import EvaluationSummary
from app.evaluation.advanced import AdvancedEvaluationSummary


def generate_evaluation_report(summary: EvaluationSummary, live: bool = False) -> str:
    """Format EvaluationSummary into terminal report string."""
    mode_str = "LIVE GEMINI EVALUATION" if live else "DETERMINISTIC MOCK EVALUATION"

    lines = [
        "══════════════════════════════════════════",
        "       AI REVENUE RECOVERY EVALUATION     ",
        "══════════════════════════════════════════",
        f"Mode                   : {mode_str}",
        f"Cases evaluated        : {summary.total_cases}",
        f"Decision accuracy      : {summary.decision_accuracy * 100:.1f}%",
        f"Safety compliance      : {summary.safety_compliance * 100:.1f}%",
        "",
        f"Safety violations      : {summary.false_recoveries + summary.opt_out_violations + summary.retry_limit_violations + summary.action_limit_violations}",
        f"False recoveries       : {summary.false_recoveries}",
        f"Opt-out violations     : {summary.opt_out_violations}",
        f"Retry limit violations : {summary.retry_limit_violations}",
        f"Action limit violations: {summary.action_limit_violations}",
        "",
        f"Recovered cases        : {summary.recovered_cases}",
        f"Recoverable cases      : {summary.recoverable_cases}",
        f"Recovery rate          : {summary.recovery_rate * 100:.1f}%",
        "",
        "──────────────────────────────────────────",
        "CASE RESULTS",
        "──────────────────────────────────────────",
    ]

    for res in summary.case_results:
        status_str = "PASS" if res.passed else "FAIL"
        lines.append(f"\nPayment {res.payment_id} ({res.scenario_tag})")
        lines.append(f"  Expected : {res.expected_decision} -> {res.expected_status}")
        lines.append(f"  Actual   : {res.actual_decision} -> {res.actual_status}")
        lines.append(f"  Actions  : {', '.join(res.actions_taken)}")
        lines.append(f"  Result   : {status_str}")
        if res.safety_violations:
            for v in res.safety_violations:
                lines.append(f"  ⚠️  Violation: {v}")

    lines.append("\n══════════════════════════════════════════\n")

    return "\n".join(lines)


def generate_advanced_evaluation_report(summary: AdvancedEvaluationSummary) -> str:
    """Format the 30-case advanced benchmark without concealing safety failures."""
    pct = lambda value: "N/A" if value is None else f"{value * 100:.1f}%"
    lines = [
        "Revenue Recovery Agent — Advanced Evaluation", "",
        f"Cases: {summary.total_cases}", f"Executed: {summary.executed_cases}", f"Blocked: {summary.blocked_cases}",
        f"Decision Accuracy:       {pct(summary.decision_accuracy)}",
        f"Action Accuracy:         {pct(summary.action_accuracy)}",
        f"Final-State Accuracy:    {pct(summary.final_state_accuracy)}",
        f"Safety Accuracy:         {pct(summary.safety_accuracy)}",
        f"Idempotency Accuracy:    {pct(summary.idempotency_accuracy)}",
        f"Overall Score:           {pct(summary.overall_score)}",
        f"Safety Violations:       {summary.safety_violations_total}",
        f"Recovery Amount Match:   {summary.recovery_amount_matches}/{summary.recovery_amount_cases} cases", "",
        "Case Results", "-" * 60,
    ]
    for result in summary.case_results:
        status = "BLOCKED" if result.execution_status == "blocked" else ("PASS" if result.case_passed else "FAIL")
        lines.append(f"{result.case_id}  {status}")
        if status == "FAIL":
            lines.extend([f"  Expected: {result.expected_decision}; {result.expected_actions}; {result.expected_final_state}",
                          f"  Actual:   {result.actual_decision}; {result.actual_actions}; {result.actual_final_state}"])
        if result.safety_violations:
            lines.append(f"  Safety:   {', '.join(result.safety_violations)}")
        if result.blocked_reason:
            lines.append(f"  Blocked:  {result.blocked_reason}")
    return "\n".join(lines)
