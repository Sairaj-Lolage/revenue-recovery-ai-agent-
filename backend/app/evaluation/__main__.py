"""
backend/app/evaluation/__main__.py
==================================
CLI entry point for running the AI Revenue Recovery Agent Evaluation Framework.

Usage:
    python -m app.evaluation
    python -m app.evaluation --live
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.seed import seed
from app.evaluation.evaluator import run_evaluation_suite
from app.evaluation.report import generate_evaluation_report
from app.evaluation.advanced import run_advanced_evaluation
from app.evaluation.report import generate_advanced_evaluation_report
from app.evaluation.analysis import generate_advanced_analysis_report, generate_advanced_quality_report, run_advanced_analysis, run_advanced_quality_analysis


def main():
    if "--advanced-quality" in sys.argv:
        json_path = None
        if "--json" in sys.argv:
            json_index = sys.argv.index("--json")
            if json_index + 1 >= len(sys.argv):
                raise SystemExit("--json requires an output path")
            json_path = sys.argv[json_index + 1]
        print(generate_advanced_quality_report(run_advanced_quality_analysis(output_path=json_path)))
        return

    if "--advanced-analysis" in sys.argv:
        json_path = None
        if "--json" in sys.argv:
            json_index = sys.argv.index("--json")
            if json_index + 1 >= len(sys.argv):
                raise SystemExit("--json requires an output path")
            json_path = sys.argv[json_index + 1]
        print(generate_advanced_analysis_report(run_advanced_analysis(output_path=json_path)))
        return

    if "--advanced" in sys.argv:
        json_path = None
        if "--json" in sys.argv:
            json_index = sys.argv.index("--json")
            if json_index + 1 >= len(sys.argv):
                raise SystemExit("--json requires an output path")
            json_path = sys.argv[json_index + 1]
        summary = run_advanced_evaluation(output_path=json_path)
        print(generate_advanced_evaluation_report(summary))
        return

    """CLI runner for evaluation framework."""
    live_requested = "--live" in sys.argv
    live_mode = False

    if live_requested:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key:
            live_mode = True
            print("🚀 Running LIVE evaluation with Gemini API...")
        else:
            print("⚠️  GEMINI_API_KEY not found in environment. Falling back to deterministic mock evaluation.")
            live_mode = False
    else:
        print("⚡ Running DETERMINISTIC mock evaluation...")

    # Set up in-memory DB and seed
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    seed(db)

    try:
        summary = run_evaluation_suite(db=db, live=live_mode)
        report = generate_evaluation_report(summary=summary, live=live_mode)
        print(report)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


if __name__ == "__main__":
    main()
