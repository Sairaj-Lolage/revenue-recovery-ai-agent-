"""
backend/tests/test_agent_tools.py
==================================
Comprehensive tests for the Agent Tool Layer (Step 2.5).

Verifies:
1. get_payment returns correct safe data.
2. get_payment does not expose recovery_scenario.
3. get_customer_history returns correct data.
4. customer history does not expose evaluation metadata.
5. retry_payment returns successful result for EASY_RECOVERY.
6. retry_payment returns failed result for PAYMENT_LINK_RECOVERY.
7. create_payment_link works.
8. create_payment_link does not recover payment.
9. send_recovery_message works for normal customer.
10. send_recovery_message blocks opted-out customer.
11. missing payment returns predictable error.
12. missing customer returns predictable error.
13. all tool outputs are JSON serializable.
14. no tool output contains recovery_scenario.
15. tools do not directly manipulate ORM objects.
16. tool registry (get_agent_tools) returns all five tools.
"""

import json
from typing import Any, Callable, Dict, List

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.db.models import Customer, Payment, PAYMENT_STATUS_FAILED
from app.db.seed import seed
from app.services.payment_service import PaymentService
from app.tools import (
    create_payment_link,
    get_agent_tools,
    get_customer_history,
    get_payment,
    retry_payment,
    send_recovery_message,
)


@pytest.fixture(scope="module")
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    seed(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="module")
def service(db_session: Session) -> PaymentService:
    return PaymentService(db_session)


@pytest.fixture(scope="module")
def tools(service: PaymentService) -> List[Callable[..., Dict[str, Any]]]:
    return get_agent_tools(service)


def _get_payment_with_scenario(db: Session, scenario: str) -> Payment:
    p = db.query(Payment).filter(Payment.recovery_scenario == scenario).first()
    assert p is not None, f"No payment with scenario={scenario!r} found"
    return p


# 1. get_payment returns correct safe data.
def test_1_get_payment_returns_correct_safe_data(service: PaymentService, db_session: Session):
    p = _get_payment_with_scenario(db_session, "EASY_RECOVERY")
    res = get_payment(service, p.id)
    assert res["success"] is True
    assert res["payment_id"] == p.id
    assert res["customer_id"] == p.customer_id
    assert res["amount_paise"] == p.amount_paise
    assert res["currency"] == "INR"
    assert res["status"] == PAYMENT_STATUS_FAILED
    assert res["attempt_count"] == p.attempt_count


# 2. get_payment does not expose recovery_scenario.
def test_2_get_payment_does_not_expose_recovery_scenario(service: PaymentService, db_session: Session):
    p = _get_payment_with_scenario(db_session, "HIGH_VALUE")
    res = get_payment(service, p.id)
    assert "recovery_scenario" not in res
    assert "HIGH_VALUE" not in json.dumps(res)


# 3. get_customer_history returns correct data.
def test_3_get_customer_history_returns_correct_data(service: PaymentService, db_session: Session):
    c = db_session.query(Customer).first()
    res = get_customer_history(service, c.id)
    assert res["success"] is True
    assert res["customer_id"] == c.id
    assert res["name"] == c.name
    assert res["segment"] == c.segment
    assert res["total_paid_paise"] == c.total_paid_paise
    assert res["successful_payments"] == c.successful_payments
    assert res["failed_payments"] == c.failed_payments
    assert res["opted_out"] == c.opted_out


# 4. customer history does not expose evaluation metadata.
def test_4_customer_history_does_not_expose_evaluation_metadata(service: PaymentService, db_session: Session):
    c = db_session.query(Customer).first()
    res = get_customer_history(service, c.id)
    assert "recovery_scenario" not in res
    json_str = json.dumps(res)
    for scenario in ["EASY_RECOVERY", "PAYMENT_LINK_RECOVERY", "REPEATED_FAILURE", "HIGH_VALUE", "OPTED_OUT", "UNRECOVERABLE"]:
        assert scenario not in json_str


# 5. retry_payment returns successful result for EASY_RECOVERY.
def test_5_retry_payment_returns_successful_result_for_easy_recovery():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    seed(session)
    svc = PaymentService(session)

    p = _get_payment_with_scenario(session, "EASY_RECOVERY")
    res = retry_payment(svc, p.id)
    assert res["success"] is True
    assert res["status"] == "success"
    assert res["amount_recovered_paise"] == p.amount_paise

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# 6. retry_payment returns failed result for PAYMENT_LINK_RECOVERY.
def test_6_retry_payment_returns_failed_result_for_payment_link_recovery():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    seed(session)
    svc = PaymentService(session)

    p = _get_payment_with_scenario(session, "PAYMENT_LINK_RECOVERY")
    res = retry_payment(svc, p.id)
    assert res["success"] is False
    assert res["status"] == "failed"
    assert res["amount_recovered_paise"] == 0

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# 7. create_payment_link works.
def test_7_create_payment_link_works(service: PaymentService, db_session: Session):
    p = _get_payment_with_scenario(db_session, "PAYMENT_LINK_RECOVERY")
    res = create_payment_link(service, p.id)
    assert res["success"] is True
    assert res["payment_link"] is not None
    assert f"pay_{p.id}" in res["payment_link"]
    assert res["payment_link"].startswith("https://")


# 8. create_payment_link does not recover payment.
def test_8_create_payment_link_does_not_recover_payment():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    seed(session)
    svc = PaymentService(session)

    p = _get_payment_with_scenario(session, "PAYMENT_LINK_RECOVERY")
    create_payment_link(svc, p.id)
    p_info = get_payment(svc, p.id)
    assert p_info["status"] == PAYMENT_STATUS_FAILED

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# 9. send_recovery_message works for normal customer.
def test_9_send_recovery_message_works_for_normal_customer(service: PaymentService, db_session: Session):
    normal_customer = db_session.query(Customer).filter(Customer.opted_out.is_(False)).first()
    res = send_recovery_message(service, normal_customer.id, "Please settle your bill", "https://pay.example.com/pay_1")
    assert res["success"] is True
    assert res["channel"] == "mock"
    assert res["message_id"].startswith("msg_")
    assert "https://pay.example.com" in res["message"]


# 10. send_recovery_message blocks opted-out customer.
def test_10_send_recovery_message_blocks_opted_out_customer(service: PaymentService, db_session: Session):
    opted_out = db_session.query(Customer).filter(Customer.opted_out.is_(True)).first()
    res = send_recovery_message(service, opted_out.id, "Reminder to pay")
    assert res["success"] is False
    assert "opted out" in res["message"].lower()
    assert res["error"] == "customer_opted_out"


# 11. missing payment returns predictable error.
def test_11_missing_payment_returns_predictable_error(service: PaymentService):
    res_get = get_payment(service, 999999)
    assert res_get["success"] is False
    assert res_get["error"] == "payment_not_found"

    res_retry = retry_payment(service, 999999)
    assert res_retry["success"] is False
    assert res_retry["error"] == "payment_not_found"

    res_link = create_payment_link(service, 999999)
    assert res_link["success"] is False
    assert res_link["error"] == "payment_not_found"


# 12. missing customer returns predictable error.
def test_12_missing_customer_returns_predictable_error(service: PaymentService):
    res_hist = get_customer_history(service, 999999)
    assert res_hist["success"] is False
    assert res_hist["error"] == "customer_not_found"

    res_msg = send_recovery_message(service, 999999, "Hello")
    assert res_msg["success"] is False
    assert res_msg["error"] == "customer_not_found"


# 13. all tool outputs are JSON serializable.
def test_13_all_tool_outputs_are_json_serializable(tools: List[Callable[..., Dict[str, Any]]]):
    tool_get_payment, tool_get_customer_history, tool_retry_payment, tool_create_payment_link, tool_send_recovery_message = tools

    outputs = [
        tool_get_payment(1),
        tool_get_customer_history(1),
        tool_retry_payment(1),
        tool_create_payment_link(1),
        tool_send_recovery_message(1, "Test message", "https://pay.example.com/1"),
        tool_get_payment(999999),
        tool_get_customer_history(999999),
    ]

    for out in outputs:
        dumped = json.dumps(out)
        assert isinstance(dumped, str)


# 14. no tool output contains recovery_scenario.
def test_14_no_tool_output_contains_recovery_scenario(service: PaymentService, db_session: Session):
    payments = db_session.query(Payment).all()
    hidden_scenarios = [
        "EASY_RECOVERY",
        "PAYMENT_LINK_RECOVERY",
        "REPEATED_FAILURE",
        "HIGH_VALUE",
        "OPTED_OUT",
        "UNRECOVERABLE",
    ]

    for p in payments:
        out = get_payment(service, p.id)
        json_str = json.dumps(out)
        assert "recovery_scenario" not in json_str
        for s in hidden_scenarios:
            assert s not in json_str, f"Found scenario {s} in get_payment output for payment {p.id}"


# 15. tools do not directly manipulate ORM objects.
def test_15_tools_do_not_directly_manipulate_orm_objects(service: PaymentService):
    res = get_payment(service, 1)
    assert not hasattr(res, "_sa_instance_state")
    assert type(res) is dict

    res_hist = get_customer_history(service, 1)
    assert not hasattr(res_hist, "_sa_instance_state")
    assert type(res_hist) is dict


# 16. registry exposes all 5 bound tools
def test_16_tool_registry(service: PaymentService):
    tools = get_agent_tools(service)
    assert len(tools) == 5
    names = [t.__name__ for t in tools]
    assert names == [
        "get_payment",
        "get_customer_history",
        "retry_payment",
        "create_payment_link",
        "send_recovery_message",
    ]

    # Verify tool execution via registry functions
    res = tools[0](payment_id=1)
    assert res["success"] is True
