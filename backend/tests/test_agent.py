"""
backend/tests/test_agent.py
===========================
Comprehensive unit tests for the Multi-Step AI Revenue Recovery Agent and Policy Guardrails.

Tests run deterministically using an in-memory SQLite database and mocked LLM reasoner.
No external Gemini API key is required.
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.agent import (
    ALLOWED_ACTIONS,
    MAX_RECOVERY_ACTIONS,
    MAX_RETRY_ATTEMPTS,
    create_recovery_graph,
    evaluate_policy_guardrails,
    run_recovery_agent,
)
from app.db.database import Base, get_db
from app.db.models import AuditLog, Customer, Payment, RecoveryAction, RecoveryCase
from app.db.seed import seed
from app.main import app
from app.services.payment_service import PaymentService
from app.tools import get_agent_tools


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Return a fresh seeded in-memory DB session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    seed(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(db_session: Session):
    """FastAPI TestClient with DB dependency overridden."""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def mock_retry_reasoner(payment_data: dict, customer_data: dict, **kwargs) -> dict:
    """Deterministic mock LLM reasoner that chooses retry_payment."""
    return {
        "decision": "retry_payment",
        "reason": "Customer has good payment history; automatic retry recommended.",
    }


def mock_stop_reasoner(payment_data: dict, customer_data: dict, **kwargs) -> dict:
    """Deterministic mock LLM reasoner that chooses stop."""
    return {
        "decision": "stop",
        "reason": "Recovery deemed inappropriate or unsafe.",
    }


# ── Core Unit Tests ───────────────────────────────────────────────────────────

def test_1_agent_can_be_created(db_session: Session) -> None:
    """Agent graph can be instantiated and compiled."""
    service = PaymentService(db_session)
    tools = get_agent_tools(service)
    tools_by_name = {fn.__name__: fn for fn in tools}
    graph = create_recovery_graph(tools_by_name=tools_by_name, llm_reasoner=mock_retry_reasoner)
    assert graph is not None


def test_2_agent_can_receive_payment_id(db_session: Session) -> None:
    """Agent runner accepts payment_id and returns result for that ID."""
    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert res["payment_id"] == 4


def test_3_payment_tool_is_available_to_agent(db_session: Session) -> None:
    """get_payment tool is invoked and recorded in agent actions."""
    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=mock_retry_reasoner)
    tools_called = [a["tool"] for a in res["actions"]]
    assert "get_payment" in tools_called
    get_payment_action = next(a for a in res["actions"] if a["tool"] == "get_payment")
    assert get_payment_action["status"] == "success"


def test_4_customer_history_tool_is_available(db_session: Session) -> None:
    """get_customer_history tool is invoked and recorded in agent actions."""
    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=mock_retry_reasoner)
    tools_called = [a["tool"] for a in res["actions"]]
    assert "get_customer_history" in tools_called
    get_cust_action = next(a for a in res["actions"] if a["tool"] == "get_customer_history")
    assert get_cust_action["status"] == "success"


def test_5_agent_can_produce_valid_structured_decision(db_session: Session) -> None:
    """Agent produces a structured result with required keys and valid decision."""
    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert "payment_id" in res
    assert "decision" in res
    assert "reason" in res
    assert "actions" in res
    assert "final_status" in res
    assert "amount_recovered_paise" in res
    assert res["decision"] in ALLOWED_ACTIONS


def test_6_agent_can_execute_retry_payment_through_tool_layer(db_session: Session) -> None:
    """Agent executes retry_payment tool when decision is retry_payment."""
    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert res["decision"] == "retry_payment"
    tools_called = [a["tool"] for a in res["actions"]]
    assert "retry_payment" in tools_called


def test_7_successful_retry_produces_recovered_amount(db_session: Session) -> None:
    """Successful retry on EASY_RECOVERY payment produces positive recovered amount."""
    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    assert easy_payment is not None

    res = run_recovery_agent(payment_id=easy_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert res["final_status"] == "success"
    assert res["amount_recovered_paise"] == easy_payment.amount_paise
    assert res["amount_recovered_paise"] > 0


def test_8_failed_retry_does_not_falsely_report_recovery(db_session: Session) -> None:
    """Failed retry does not falsely report recovery."""
    repeated_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "REPEATED_FAILURE")
        .first()
    )
    assert repeated_payment is not None

    res = run_recovery_agent(payment_id=repeated_payment.id, db=db_session, llm_reasoner=mock_stop_reasoner)
    assert res["final_status"] == "stopped"
    assert res["amount_recovered_paise"] == 0


def test_9_recovery_scenario_never_reaches_agent_context(db_session: Session) -> None:
    """Agent context (payment_data and customer_data) NEVER contains recovery_scenario."""
    received_contexts = []

    def spy_reasoner(payment_data: dict, customer_data: dict, **kwargs) -> dict:
        received_contexts.append((payment_data, customer_data))
        return {"decision": "stop", "reason": "Spy check completed."}

    run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=spy_reasoner)

    assert len(received_contexts) >= 1
    for p_data, c_data in received_contexts:
        assert "recovery_scenario" not in p_data
        assert "recovery_scenario" not in c_data

        hidden_scenarios = [
            "EASY_RECOVERY", "PAYMENT_LINK_RECOVERY", "REPEATED_FAILURE",
            "HIGH_VALUE", "OPTED_OUT", "UNRECOVERABLE",
        ]
        for val in p_data.values():
            assert val not in hidden_scenarios
        for val in c_data.values():
            assert val not in hidden_scenarios


def test_10_api_endpoint_handles_valid_payment(client: TestClient, monkeypatch) -> None:
    """POST /api/agent/recover/4 returns HTTP 200 with structured decision."""
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    response = client.post("/api/agent/recover/4")
    assert response.status_code == 200
    data = response.json()
    assert data["payment_id"] == 4
    assert "decision" in data
    assert "reason" in data
    assert "actions" in data
    assert "final_status" in data
    assert "amount_recovered_paise" in data


def test_11_api_endpoint_handles_missing_payment(client: TestClient) -> None:
    """POST /api/agent/recover/99999 returns HTTP 404 Not Found."""
    response = client.post("/api/agent/recover/99999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_12_agent_output_is_json_serializable(db_session: Session) -> None:
    """Agent response dictionary is fully JSON serializable."""
    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=mock_retry_reasoner)
    dumped = json.dumps(res)
    assert isinstance(dumped, str)


def test_13_api_key_is_never_returned_in_responses(client: TestClient, monkeypatch) -> None:
    """API key set in environment is never included in endpoint response payload."""
    secret_key = "MY_SECRET_GEMINI_KEY_99999"
    monkeypatch.setenv("GEMINI_API_KEY", secret_key)
    monkeypatch.setattr("app.agent.graph.default_gemini_reasoner", mock_retry_reasoner)

    response = client.post("/api/agent/recover/4")
    raw_response_text = response.text
    assert secret_key not in raw_response_text


def test_14_agent_does_not_directly_access_orm_database(db_session: Session) -> None:
    """Agent nodes operate strictly on tool dictionary outputs, not SQLAlchemy ORM instances."""
    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=mock_retry_reasoner)
    for act in res["actions"]:
        assert isinstance(act, dict)


# ── Multi-Step & Policy Guardrail Tests ─────────────────────────────────────────

def test_15_multistep_retry_failure_to_payment_link(db_session: Session) -> None:
    """When retry_payment fails, multi-step agent continues to create_payment_link."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    assert link_payment is not None

    def adaptive_reasoner(payment_data, customer_data, actions_history, **kwargs):
        history_tools = [a["tool"] for a in actions_history]
        if "retry_payment" not in history_tools:
            return {"decision": "retry_payment", "reason": "First attempt retry"}
        elif "create_payment_link" not in history_tools:
            return {"decision": "create_payment_link", "reason": "Retry failed; creating payment link."}
        else:
            return {"decision": "stop", "reason": "Link created, waiting for customer."}

    res = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=adaptive_reasoner)
    tools_called = [a["tool"] for a in res["actions"]]

    assert "retry_payment" in tools_called
    assert "create_payment_link" in tools_called
    assert res["final_status"] in {"in_progress", "stopped"}
    assert res["amount_recovered_paise"] == 0


def test_16_multistep_link_to_recovery_message(db_session: Session) -> None:
    """Multi-step agent can create payment link then send recovery message."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    assert link_payment is not None

    def link_and_message_reasoner(payment_data, customer_data, actions_history, **kwargs):
        history_tools = [a["tool"] for a in actions_history]
        if "create_payment_link" not in history_tools:
            return {"decision": "create_payment_link", "reason": "Generate payment link"}
        elif "send_recovery_message" not in history_tools:
            return {"decision": "send_recovery_message", "reason": "Send payment link to customer"}
        else:
            return {"decision": "stop", "reason": "Message sent"}

    res = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=link_and_message_reasoner)
    tools_called = [a["tool"] for a in res["actions"]]

    assert "create_payment_link" in tools_called
    assert "send_recovery_message" in tools_called


def test_17_policy_blocks_opted_out_customer(db_session: Session) -> None:
    """Policy guardrail stops workflow and blocks retries/messages for opted-out customer."""
    opted_out_payment = (
        db_session.query(Payment)
        .join(Customer)
        .filter(Customer.opted_out == True)
        .first()
    )
    assert opted_out_payment is not None

    res = run_recovery_agent(payment_id=opted_out_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)

    assert res["decision"] == "stop"
    assert res["final_status"] == "stopped"
    tools_called = [a["tool"] for a in res["actions"]]
    assert "retry_payment" not in tools_called
    assert "send_recovery_message" not in tools_called


def test_18_policy_blocks_already_successful_payment(db_session: Session) -> None:
    """Policy guardrail stops workflow if payment status is already 'success'."""
    success_payment = (
        db_session.query(Payment)
        .filter(Payment.status == "success")
        .first()
    )
    assert success_payment is not None

    res = run_recovery_agent(payment_id=success_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)

    assert res["decision"] == "stop"
    tools_called = [a["tool"] for a in res["actions"]]
    assert "retry_payment" not in tools_called


def test_19_policy_enforces_retry_limit(db_session: Session) -> None:
    """Policy guardrail blocks retry_payment when payment attempt_count >= MAX_RETRY_ATTEMPTS."""
    payment = (
        db_session.query(Payment)
        .filter(Payment.status == "failed")
        .first()
    )
    payment.attempt_count = MAX_RETRY_ATTEMPTS
    db_session.commit()

    res = run_recovery_agent(payment_id=payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)
    tools_called = [a["tool"] for a in res["actions"]]
    assert "retry_payment" not in tools_called


def test_19a_retry_limit_completes_link_recovery_once(db_session: Session) -> None:
    """A retry-cap fallback creates one link, sends one message, and is repeat-safe."""
    payment = (
        db_session.query(Payment)
        .filter(Payment.status == "failed")
        .first()
    )
    assert payment is not None
    payment.attempt_count = MAX_RETRY_ATTEMPTS
    db_session.commit()

    first = run_recovery_agent(payment_id=payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert [a["tool"] for a in first["actions"] if a["tool"] not in {"get_payment", "get_customer_history"}] == [
        "create_payment_link", "send_recovery_message"
    ]
    assert first["final_status"] == "in_progress"

    case = db_session.query(RecoveryCase).filter_by(payment_id=payment.id).one()
    actions = db_session.query(RecoveryAction).filter_by(recovery_case_id=case.id).all()
    assert [(a.action_type, a.amount_recovered_paise) for a in actions] == [
        ("create_payment_link", 0), ("send_recovery_message", 0)
    ]
    events = {log.event_type for log in db_session.query(AuditLog).filter_by(recovery_case_id=case.id)}
    assert {"agent_decision", "policy_blocked", "payment_link_created", "recovery_message_sent"} <= events

    second = run_recovery_agent(payment_id=payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert second["final_status"] == "escalated"
    assert db_session.query(RecoveryAction).filter_by(recovery_case_id=case.id).count() == 2


def test_20_policy_enforces_max_action_limit(db_session: Session) -> None:
    """Policy guardrail stops workflow after MAX_RECOVERY_ACTIONS (3 actions)."""
    payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "REPEATED_FAILURE")
        .first()
    )
    assert payment is not None

    def infinite_loop_reasoner(payment_data, customer_data, actions_history, **kwargs):
        # Keep proposing retry_payment endlessly
        return {"decision": "retry_payment", "reason": "Persistent retry"}

    res = run_recovery_agent(payment_id=payment.id, db=db_session, llm_reasoner=infinite_loop_reasoner)

    # Count recovery actions executed (excluding get_payment and get_customer_history)
    recovery_actions = [a for a in res["actions"] if a["tool"] not in {"get_payment", "get_customer_history"}]
    assert len(recovery_actions) <= MAX_RECOVERY_ACTIONS


def test_21_policy_rejects_invalid_llm_action(db_session: Session) -> None:
    """Policy guardrail overrides unapproved action (e.g. 'delete_payment') to 'stop'."""
    def invalid_action_reasoner(payment_data, customer_data, **kwargs):
        return {"decision": "delete_payment", "reason": "Destructive test action"}

    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=invalid_action_reasoner)
    assert res["decision"] == "stop"
    assert res["final_status"] == "stopped"


def test_22_payment_link_does_not_falsely_report_recovery(db_session: Session) -> None:
    """Creating a payment link or sending a message reports amount_recovered_paise == 0."""
    def link_reasoner(payment_data, customer_data, **kwargs):
        return {"decision": "create_payment_link", "reason": "Send payment link"}

    res = run_recovery_agent(payment_id=4, db=db_session, llm_reasoner=link_reasoner)
    assert res["amount_recovered_paise"] == 0
    assert res["final_status"] in {"in_progress", "stopped"}


# ── RecoveryAction Database Persistence Tests ───────────────────────────────────

def test_23_successful_retry_is_persisted(db_session: Session) -> None:
    """Successful retry creates RecoveryAction row with approved=True, action_type=retry_payment, amount>0."""
    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    res = run_recovery_agent(payment_id=easy_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)
    
    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    assert case is not None

    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    assert len(actions) == 1
    action = actions[0]
    assert action.action_type == "retry_payment"
    assert action.approved is True
    assert action.amount_recovered_paise == easy_payment.amount_paise
    assert action.amount_recovered_paise > 0


def test_24_failed_retry_is_persisted(db_session: Session) -> None:
    """Failed retry creates RecoveryAction row with result indicating failure and amount_recovered_paise=0."""
    failed_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    res = run_recovery_agent(payment_id=failed_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == failed_payment.id).first()
    assert case is not None

    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    assert len(actions) >= 1
    retry_action = next((a for a in actions if a.action_type == "retry_payment"), None)
    assert retry_action is not None
    assert retry_action.approved is True
    assert retry_action.amount_recovered_paise == 0
    assert "fail" in retry_action.result.lower()


def test_25_payment_link_is_persisted(db_session: Session) -> None:
    """Creating a payment link creates RecoveryAction with action_type=create_payment_link and amount=0."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )

    def link_reasoner(payment_data, customer_data, **kwargs):
        return {"decision": "create_payment_link", "reason": "Create recovery link"}

    run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=link_reasoner)

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    assert case is not None

    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    link_action = next((a for a in actions if a.action_type == "create_payment_link"), None)
    assert link_action is not None
    assert link_action.approved is True
    assert link_action.amount_recovered_paise == 0


def test_26_recovery_message_is_persisted(db_session: Session) -> None:
    """Sending a recovery message creates RecoveryAction with action_type=send_recovery_message and amount=0."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )

    def message_reasoner(payment_data, customer_data, **kwargs):
        return {"decision": "send_recovery_message", "reason": "Send notification message"}

    run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=message_reasoner)

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    assert case is not None

    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    msg_action = next((a for a in actions if a.action_type == "send_recovery_message"), None)
    assert msg_action is not None
    assert msg_action.approved is True
    assert msg_action.amount_recovered_paise == 0


def test_27_opt_out_protection_no_prohibited_action(db_session: Session) -> None:
    """Opted-out customer never has an executed prohibited recovery action in recovery_actions table."""
    opted_out_payment = (
        db_session.query(Payment)
        .join(Customer)
        .filter(Customer.opted_out == True)
        .first()
    )
    run_recovery_agent(payment_id=opted_out_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == opted_out_payment.id).first()
    assert case is not None

    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    prohibited = {"retry_payment", "create_payment_link", "send_recovery_message"}
    for a in actions:
        assert a.action_type not in prohibited or a.approved is False


def test_28_no_false_recovery_on_link_or_message(db_session: Session) -> None:
    """Creating a payment link or sending a message never produces RecoveryAction with amount_recovered_paise > 0."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )

    def multi_reasoner(payment_data, customer_data, actions_history, **kwargs):
        history_tools = [a["tool"] for a in actions_history]
        if "create_payment_link" not in history_tools:
            return {"decision": "create_payment_link", "reason": "Link"}
        elif "send_recovery_message" not in history_tools:
            return {"decision": "send_recovery_message", "reason": "Message"}
        return {"decision": "stop", "reason": "Stop"}

    run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=multi_reasoner)

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    for a in actions:
        if a.action_type in {"create_payment_link", "send_recovery_message"}:
            assert a.amount_recovered_paise == 0


def test_29_audit_log_remains_intact_alongside_recovery_actions(db_session: Session) -> None:
    """Both AuditLog entries and RecoveryAction entries are persisted simultaneously for a workflow."""
    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    run_recovery_agent(payment_id=easy_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    audit_logs = db_session.query(AuditLog).filter(AuditLog.recovery_case_id == case.id).all()

    assert len(actions) >= 1
    assert len(audit_logs) >= 4
    audit_events = [log.event_type for log in audit_logs]
    assert "agent_started" in audit_events
    assert "payment_inspected" in audit_events
    assert "policy_allowed" in audit_events


# ── Task 2.8C Lifecycle, Idempotency & Follow-Up Regression Tests ───────────────

def test_30_recovered_case_is_idempotent(db_session: Session) -> None:
    """Calling recovery twice on a recovered case does not re-execute recovery actions."""
    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    res1 = run_recovery_agent(payment_id=easy_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert res1["final_status"] == "success"

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    actions_count_after_first = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()

    res2 = run_recovery_agent(payment_id=easy_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert res2["final_status"] == "success"
    assert res2["actions"] == []

    actions_count_after_second = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()
    assert actions_count_after_second == actions_count_after_first


def test_31_successful_payment_is_protected(db_session: Session) -> None:
    """Already successful payment cannot be retried or recovered."""
    succ_payment = (
        db_session.query(Payment)
        .filter(Payment.status == "success")
        .first()
    )
    res = run_recovery_agent(payment_id=succ_payment.id, db=db_session, llm_reasoner=mock_retry_reasoner)
    assert res["final_status"] == "success"
    assert res["actions"] == []
    tools_called = [a.get("tool") for a in res["actions"]]
    assert "retry_payment" not in tools_called


from app.evaluation.evaluator import mock_evaluation_reasoner


def test_32_escalated_case_is_idempotent(db_session: Session) -> None:
    """Escalated case remains escalated and does not execute actions on subsequent calls."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    res2 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res2["final_status"] == "escalated"

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    actions_before = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()

    res3 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res3["final_status"] == "escalated"
    assert res3["actions"] == []

    actions_after = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()
    assert actions_after == actions_before


def test_33_payment_link_case_does_not_repeat_message(db_session: Session) -> None:
    """Subsequent API call after link creation triggers follow-up rather than duplicating links/messages."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    res1 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res1["final_status"] == "in_progress"

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    links_count = db_session.query(RecoveryAction).filter(
        RecoveryAction.recovery_case_id == case.id,
        RecoveryAction.action_type == "create_payment_link"
    ).count()
    assert links_count == 1

    res2 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    links_count_after = db_session.query(RecoveryAction).filter(
        RecoveryAction.recovery_case_id == case.id,
        RecoveryAction.action_type == "create_payment_link"
    ).count()
    assert links_count_after == 1


def test_34_one_time_follow_up(db_session: Session) -> None:
    """Follow-up transitions IN_PROGRESS case to ESCALATED when payment remains unpaid."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    res1 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res1["final_status"] == "in_progress"

    res2 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res2["final_status"] == "escalated"
    assert res2["execution_result"]["action"] == "follow_up"


def test_35_follow_up_succeeds(db_session: Session) -> None:
    """Follow-up transitions IN_PROGRESS case to RECOVERED when payment link is paid between runs."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    res1 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res1["final_status"] == "in_progress"

    service = PaymentService(db_session)
    service.complete_payment_via_link(payment_id=link_payment.id)

    res2 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res2["final_status"] == "success"
    assert res2["amount_recovered_paise"] == link_payment.amount_paise

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    assert case.status == "RECOVERED"
    assert case.amount_recovered_paise == link_payment.amount_paise


def test_36_opt_out_remains_protected(db_session: Session) -> None:
    """No recovery actions are executed for opted-out customer across multiple calls."""
    opted_out_payment = (
        db_session.query(Payment)
        .join(Customer)
        .filter(Customer.opted_out == True)
        .first()
    )
    res1 = run_recovery_agent(payment_id=opted_out_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res1["final_status"] == "stopped"

    res2 = run_recovery_agent(payment_id=opted_out_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res2["final_status"] == "stopped"

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == opted_out_payment.id).first()
    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    assert len(actions) == 0


def test_37_retry_limit_remains_protected(db_session: Session) -> None:
    """Existing retry limit guardrail continues to block excessive payment retries."""
    payment = (
        db_session.query(Payment)
        .filter(Payment.status == "failed")
        .first()
    )
    payment.attempt_count = MAX_RETRY_ATTEMPTS
    db_session.commit()

    res = run_recovery_agent(payment_id=payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    tools = [a.get("tool") for a in res["actions"]]
    assert "retry_payment" not in tools


def test_38_action_limit_remains_protected(db_session: Session) -> None:
    """Existing action limit guardrail continues to cap actions at MAX_RECOVERY_ACTIONS."""
    payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "REPEATED_FAILURE")
        .first()
    )
    def loop_reasoner(payment_data, customer_data, **kwargs):
        return {"decision": "retry_payment", "reason": "Loop"}

    res = run_recovery_agent(payment_id=payment.id, db=db_session, llm_reasoner=loop_reasoner)
    rec_actions = [a for a in res["actions"] if a["tool"] not in {"get_payment", "get_customer_history"}]
    assert len(rec_actions) <= MAX_RECOVERY_ACTIONS


def test_39_recovery_action_persistence(db_session: Session) -> None:
    """Structured RecoveryAction records are persisted with accurate status and amounts."""
    easy_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "EASY_RECOVERY")
        .first()
    )
    run_recovery_agent(payment_id=easy_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == easy_payment.id).first()
    actions = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).all()
    assert len(actions) == 1
    assert actions[0].action_type == "retry_payment"
    assert actions[0].approved is True
    assert actions[0].amount_recovered_paise == easy_payment.amount_paise


def test_40_audit_log_remains_intact(db_session: Session) -> None:
    """AuditLog records complete lifecycle telemetry including follow-up and completion events."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    audit_logs = db_session.query(AuditLog).filter(AuditLog.recovery_case_id == case.id).all()
    events = [log.event_type for log in audit_logs]

    assert "agent_started" in events
    assert "follow_up_started" in events
    assert "follow_up_completed" in events
    assert "agent_escalated" in events


def test_41_repeated_api_calls_do_not_accumulate_duplicate_actions(db_session: Session) -> None:
    """Repeated recovery API calls for a payment do not create invalid duplicate actions on 3rd+ runs."""
    link_payment = (
        db_session.query(Payment)
        .filter(Payment.recovery_scenario == "PAYMENT_LINK_RECOVERY")
        .first()
    )
    res1 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res1["final_status"] == "in_progress"

    case = db_session.query(RecoveryCase).filter(RecoveryCase.payment_id == link_payment.id).first()
    actions_call1 = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()

    res2 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res2["final_status"] == "escalated"

    actions_call2 = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()

    res3 = run_recovery_agent(payment_id=link_payment.id, db=db_session, llm_reasoner=mock_evaluation_reasoner)
    assert res3["final_status"] == "escalated"

    actions_call3 = db_session.query(RecoveryAction).filter(RecoveryAction.recovery_case_id == case.id).count()

    assert actions_call3 == actions_call2
