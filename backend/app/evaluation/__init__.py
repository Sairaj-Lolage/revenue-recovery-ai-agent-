"""
backend/app/evaluation/__init__.py
==================================
AI Revenue Recovery Evaluation Framework.
"""

from app.evaluation.cases import EvaluationCase, get_evaluation_cases
from app.evaluation.evaluator import CaseResult, EvaluationSummary, run_evaluation_suite
from app.evaluation.report import generate_evaluation_report

__all__ = [
    "EvaluationCase",
    "get_evaluation_cases",
    "CaseResult",
    "EvaluationSummary",
    "run_evaluation_suite",
    "generate_evaluation_report",
]
