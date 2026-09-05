"""
backend/app/agent/graph.py
==========================
LangGraph agent graph definition for the Multi-Step AI Revenue Recovery Agent.

Graph Architecture:
    START -> inspect_payment -> inspect_customer -> agent_reasoning ◄───────────┐
                                                         ↓                        │
                                                    policy_check                  │
                                                         ↓                        │
                                                   execute_action                 │
                                                         ↓                        │
                                                evaluate_result ─── continue ─────┘
                                                         │
                                                     (recovered / stopped / escalated)
                                                         ↓
                                                        END
"""

import json
from typing import Any, Callable, Dict, Optional
from google import genai
from google.genai import types
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agent.config import get_gemini_api_key, get_gemini_client, get_gemini_model_name
from app.agent.policy import (
    ALLOWED_ACTIONS,
    MAX_RECOVERY_ACTIONS,
    MAX_RETRY_ATTEMPTS,
    evaluate_policy_guardrails,
)
from app.agent.prompts import RECOVERY_AGENT_SYSTEM_PROMPT
from app.agent.state import RecoveryAgentState
from app.db.models import ACTOR_AGENT, ACTOR_GUARDRAIL


class DecisionOutput(BaseModel):
    decision: str = Field(description="One of: retry_payment, create_payment_link, send_recovery_message, stop, escalate")
    reason: str = Field(description="Short business explanation for the decision")


def default_gemini_reasoner(
    payment_data: Dict[str, Any],
    customer_data: Dict[str, Any],
    actions_history: list,
    created_payment_link: Optional[str] = None,
) -> Dict[str, str]:
    """Call Google Gemini API using official google-genai SDK to select recovery action."""
    safe_payment = {k: v for k, v in payment_data.items() if k != "recovery_scenario"}
    safe_customer = {k: v for k, v in customer_data.items() if k != "recovery_scenario"}

    def fallback_reasoner(reason_prefix: str) -> Dict[str, str]:
        executed_tools = {a.get("tool") for a in actions_history}
        if safe_customer.get("opted_out"):
            return {"decision": "stop", "reason": "Customer opted out of recovery."}
        if "retry_payment" not in executed_tools and safe_payment.get("attempt_count", 0) < 2:
            return {"decision": "retry_payment", "reason": f"{reason_prefix}: automatic payment retry."}
        if "create_payment_link" not in executed_tools:
            return {"decision": "create_payment_link", "reason": f"{reason_prefix}: create recovery payment link."}
        if "send_recovery_message" not in executed_tools:
            return {"decision": "send_recovery_message", "reason": f"{reason_prefix}: notify customer with recovery link."}
        return {"decision": "stop", "reason": f"{reason_prefix}: all bounded recovery actions completed."}

    # A missing key is an intentional local/demo configuration.  Do not create
    # an unauthenticated client or wait on a network request before falling back.
    if not get_gemini_api_key():
        return fallback_reasoner("Deterministic local policy")

    client = get_gemini_client()
    model_name = get_gemini_model_name()

    prompt = (
        f"Analyze the payment and customer details to choose the next recovery action:\n\n"
        f"PAYMENT:\n{json.dumps(safe_payment, indent=2, default=str)}\n\n"
        f"CUSTOMER:\n{json.dumps(safe_customer, indent=2, default=str)}\n\n"
        f"ACTIONS EXECUTED SO FAR IN THIS WORKFLOW RUN:\n{json.dumps(actions_history, indent=2)}\n"
        f"CREATED PAYMENT LINK: {created_payment_link or 'None'}\n"
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=RECOVERY_AGENT_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=DecisionOutput,
                temperature=0.0,
            ),
        )
        raw_text = response.text or ""
        parsed = json.loads(raw_text)
        decision = parsed.get("decision", "stop")
        reason = parsed.get("reason", "Gemini agent decision.")
    except Exception as e:
        # Heuristic fallback if LLM API is unavailable or encounters high demand (e.g. 503/429)
        fallback = fallback_reasoner(f"LLM unavailable ({str(e)})")
        decision = fallback["decision"]
        reason = fallback["reason"]

    if decision not in ALLOWED_ACTIONS:
        decision = "stop"

    return {"decision": decision, "reason": reason}


# ── Node Definitions ──────────────────────────────────────────────────────────

def inspect_payment_node(state: RecoveryAgentState, tools_by_name: Dict[str, Callable]) -> Dict[str, Any]:
    """Node 1: Inspect payment details via get_payment tool."""
    actions = list(state.get("actions", []))
    audit_events = list(state.get("audit_events", []))
    payment_id = state["payment_id"]

    try:
        tool_fn = tools_by_name["get_payment"]
        res = tool_fn(payment_id)
        if res.get("error") or not res.get("success", False):
            actions.append({"tool": "get_payment", "status": "failed"})
            return {
                "actions": actions,
                "audit_events": audit_events,
                "error": res.get("message") or res.get("error") or "Failed to fetch payment",
                "final_status": "error",
            }

        actions.append({"tool": "get_payment", "status": "success"})
        audit_events.append({
            "event_type": "PAYMENT_INSPECTED",
            "actor": ACTOR_AGENT,
            "details": f"Payment {payment_id} inspected (status={res.get('status')}, amount={res.get('amount_paise')} paise)",
        })

        return {
            "payment_data": res,
            "customer_id": res.get("customer_id"),
            "actions": actions,
            "audit_events": audit_events,
        }
    except Exception as exc:
        actions.append({"tool": "get_payment", "status": "failed"})
        return {
            "actions": actions,
            "audit_events": audit_events,
            "error": f"Error inspecting payment: {str(exc)}",
            "final_status": "error",
        }


def inspect_customer_node(state: RecoveryAgentState, tools_by_name: Dict[str, Callable]) -> Dict[str, Any]:
    """Node 2: Inspect customer history via get_customer_history tool."""
    if state.get("error"):
        return {}

    actions = list(state.get("actions", []))
    audit_events = list(state.get("audit_events", []))
    customer_id = state.get("customer_id")

    if customer_id is None:
        actions.append({"tool": "get_customer_history", "status": "failed"})
        return {"actions": actions, "audit_events": audit_events, "error": "Customer ID missing", "final_status": "error"}

    try:
        tool_fn = tools_by_name["get_customer_history"]
        res = tool_fn(customer_id)
        if res.get("error") or not res.get("success", False):
            actions.append({"tool": "get_customer_history", "status": "failed"})
            return {
                "actions": actions,
                "audit_events": audit_events,
                "error": res.get("message") or res.get("error") or "Failed to fetch customer history",
                "final_status": "error",
            }

        actions.append({"tool": "get_customer_history", "status": "success"})
        audit_events.append({
            "event_type": "CUSTOMER_INSPECTED",
            "actor": ACTOR_AGENT,
            "details": f"Customer {customer_id} inspected (opted_out={res.get('opted_out')})",
        })

        return {
            "customer_data": res,
            "actions": actions,
            "audit_events": audit_events,
        }
    except Exception as exc:
        actions.append({"tool": "get_customer_history", "status": "failed"})
        return {
            "actions": actions,
            "audit_events": audit_events,
            "error": f"Error inspecting customer history: {str(exc)}",
            "final_status": "error",
        }


def agent_reasoning_node(state: RecoveryAgentState, llm_reasoner: Callable) -> Dict[str, Any]:
    """Node 3: Propose next recovery decision using LLM reasoner."""
    if state.get("error"):
        return {}

    payment_data = state.get("payment_data") or {}
    customer_data = state.get("customer_data") or {}
    actions_history = state.get("actions", [])
    link = state.get("created_payment_link")
    audit_events = list(state.get("audit_events", []))

    try:
        # Call reasoner with arguments supported by default / custom reasoner
        try:
            result = llm_reasoner(
                payment_data=payment_data,
                customer_data=customer_data,
                actions_history=actions_history,
                created_payment_link=link,
            )
        except TypeError:
            # Fallback for reasoners taking 2 positional arguments
            result = llm_reasoner(payment_data, customer_data)

        proposed_decision = result.get("decision", "stop")
        reason = result.get("reason", "No reason provided.")

        audit_events.append({
            "event_type": "AGENT_DECISION",
            "actor": ACTOR_AGENT,
            "details": f"Proposed Decision: {proposed_decision} | Reason: {reason}",
        })

        return {
            "proposed_decision": proposed_decision,
            "reason": reason,
            "audit_events": audit_events,
        }
    except Exception as exc:
        audit_events.append({
            "event_type": "AGENT_DECISION",
            "actor": ACTOR_AGENT,
            "details": f"Proposed Decision: stop | Reason: Reasoning error {str(exc)}",
        })
        return {
            "proposed_decision": "stop",
            "reason": f"Agent reasoning error: {str(exc)}",
            "audit_events": audit_events,
        }


def policy_check_node(state: RecoveryAgentState) -> Dict[str, Any]:
    """Node 4: Evaluate deterministic policy rules against proposed LLM decision."""
    if state.get("error"):
        return {}

    audit_events = list(state.get("audit_events", []))
    proposed_decision = state.get("proposed_decision", "stop")
    proposed_reason = state.get("reason", "")
    payment_data = state.get("payment_data")
    customer_data = state.get("customer_data")
    action_count = state.get("action_count", 0)
    retry_count = state.get("retry_count", 0)
    payment_link_created = bool(state.get("created_payment_link"))
    recovery_message_sent = any(
        action.get("tool") == "send_recovery_message"
        for action in state.get("actions", [])
    )

    policy_res = evaluate_policy_guardrails(
        proposed_decision=proposed_decision,
        proposed_reason=proposed_reason,
        payment_data=payment_data,
        customer_data=customer_data,
        action_count=action_count,
        retry_count=retry_count,
        payment_link_created=payment_link_created,
        recovery_message_sent=recovery_message_sent,
        max_retry_attempts=state.get("max_retry_attempts", MAX_RETRY_ATTEMPTS),
        high_value_threshold_paise=state.get("high_value_threshold_paise"),
    )

    if policy_res.allowed:
        audit_events.append({
            "event_type": "POLICY_ALLOWED",
            "actor": ACTOR_GUARDRAIL,
            "details": f"Policy approved action '{policy_res.decision}'",
        })
        return {
            "decision": policy_res.decision,
            "reason": policy_res.reason,
            "audit_events": audit_events,
        }
    else:
        audit_events.append({
            "event_type": "POLICY_BLOCKED",
            "actor": ACTOR_GUARDRAIL,
            "details": f"Policy blocked '{proposed_decision}'. Overridden to '{policy_res.decision}': {policy_res.reason}",
        })
        return {
            "decision": policy_res.decision,
            "reason": policy_res.reason,
            "audit_events": audit_events,
        }


def execute_action_node(state: RecoveryAgentState, tools_by_name: Dict[str, Callable]) -> Dict[str, Any]:
    """Node 5: Execute chosen recovery tool."""
    if state.get("error"):
        return {}

    actions = list(state.get("actions", []))
    audit_events = list(state.get("audit_events", []))
    decision = state.get("decision", "stop")
    payment_id = state["payment_id"]
    customer_id = state.get("customer_id")
    action_count = state.get("action_count", 0)
    retry_count = state.get("retry_count", 0)
    created_link = state.get("created_payment_link")
    payment_data = dict(state.get("payment_data") or {})

    amount_recovered = state.get("amount_recovered_paise", 0)
    final_status = state.get("final_status", "in_progress")
    exec_result = state.get("execution_result")

    if decision == "retry_payment":
        tool_fn = tools_by_name["retry_payment"]
        res = tool_fn(payment_id)
        action_count += 1
        retry_count += 1

        success = res.get("success", False)
        status_str = "success" if success else "failed"
        action_recovered = res.get("amount_recovered_paise", 0) if success else 0
        actions.append({
            "tool": "retry_payment",
            "action_type": "retry_payment",
            "status": status_str,
            "result": res.get("message") or status_str,
            "reason": state.get("reason", ""),
            "approved": True,
            "amount_recovered_paise": action_recovered,
        })
        audit_events.append({
            "event_type": "RETRY_ATTEMPTED",
            "actor": ACTOR_AGENT,
            "details": f"Attempted payment retry #{retry_count} (result: {status_str})",
        })

        if success:
            amount_recovered = res.get("amount_recovered_paise", 0)
            final_status = "success"
            payment_data["status"] = "success"
            audit_events.append({
                "event_type": "RECOVERY_SUCCEEDED",
                "actor": ACTOR_AGENT,
                "details": f"Payment {payment_id} successfully recovered INR {amount_recovered / 100:.2f}",
            })
        else:
            final_status = "failed"
            payment_data["attempt_count"] = payment_data.get("attempt_count", 0) + 1

        exec_result = res

    elif decision == "create_payment_link":
        tool_fn = tools_by_name["create_payment_link"]
        res = tool_fn(payment_id)
        action_count += 1

        success = res.get("success", False)
        status_str = "success" if success else "failed"
        actions.append({
            "tool": "create_payment_link",
            "action_type": "create_payment_link",
            "status": status_str,
            "result": res.get("message") or status_str,
            "reason": state.get("reason", ""),
            "approved": True,
            "amount_recovered_paise": 0,
        })

        if success and res.get("payment_link"):
            created_link = res["payment_link"]

        audit_events.append({
            "event_type": "PAYMENT_LINK_CREATED",
            "actor": ACTOR_AGENT,
            "details": f"Created payment link: {created_link or 'Failed'}",
        })

        final_status = "in_progress"
        exec_result = res

    elif decision == "send_recovery_message":
        tool_fn = tools_by_name["send_recovery_message"]
        msg_text = "Your recent payment could not be completed. Please use this secure payment link to complete your payment."
        res = tool_fn(
            customer_id=customer_id,
            message=msg_text,
            payment_link=created_link,
        )
        action_count += 1

        success = res.get("success", False)
        status_str = "success" if success else "failed"
        actions.append({
            "tool": "send_recovery_message",
            "action_type": "send_recovery_message",
            "status": status_str,
            "result": res.get("message") or status_str,
            "reason": state.get("reason", ""),
            "approved": True,
            "amount_recovered_paise": 0,
        })

        audit_events.append({
            "event_type": "RECOVERY_MESSAGE_SENT",
            "actor": ACTOR_AGENT,
            "details": f"Sent recovery message to customer {customer_id} (message_id={res.get('message_id')})",
        })

        final_status = "in_progress"
        exec_result = res

    elif decision == "escalate":
        action_count += 1
        actions.append({
            "tool": "escalate",
            "action_type": "escalate",
            "status": "success",
            "result": f"Case escalated: {state.get('reason', '')}",
            "reason": state.get("reason", ""),
            "approved": True,
            "amount_recovered_paise": 0,
        })
        audit_events.append({
            "event_type": "AGENT_ESCALATED",
            "actor": ACTOR_AGENT,
            "details": f"Case escalated for payment {payment_id}. Reason: {state.get('reason')}",
        })
        final_status = "escalated"
        exec_result = {"action": "escalate", "reason": state.get("reason")}

    elif decision == "stop":
        audit_events.append({
            "event_type": "AGENT_STOPPED",
            "actor": ACTOR_AGENT,
            "details": f"Agent workflow stopped. Reason: {state.get('reason')}",
        })
        if final_status != "success":
            final_status = "stopped"
        exec_result = {"action": "stop", "reason": state.get("reason")}

    return {
        "actions": actions,
        "audit_events": audit_events,
        "action_count": action_count,
        "retry_count": retry_count,
        "payment_data": payment_data,
        "created_payment_link": created_link,
        "amount_recovered_paise": amount_recovered,
        "final_status": final_status,
        "execution_result": exec_result,
    }


def evaluate_result_routing(state: RecoveryAgentState) -> str:
    """Route graph flow after action execution."""
    if state.get("error"):
        return "end"

    final_status = state.get("final_status")
    decision = state.get("decision")
    amount_recovered = state.get("amount_recovered_paise", 0)
    action_count = state.get("action_count", 0)

    if amount_recovered > 0 or final_status == "success":
        return "end"
    if decision in {"stop", "escalate"} or final_status in {"stopped", "escalated"}:
        return "end"
    # Link recovery is complete once the customer has received the link.  Keep
    # the case IN_PROGRESS so the runner's one-time follow-up owns the next
    # lifecycle transition instead of looping to a synthetic stop action.
    if decision == "send_recovery_message":
        return "end"
    if action_count >= MAX_RECOVERY_ACTIONS:
        return "end"

    return "continue"


def create_recovery_graph(tools_by_name: Dict[str, Callable], llm_reasoner: Optional[Callable] = None):
    """Construct and compile the Multi-Step Recovery Agent StateGraph."""
    reasoner = llm_reasoner or default_gemini_reasoner

    builder = StateGraph(RecoveryAgentState)

    def node_inspect_payment(state: RecoveryAgentState):
        return inspect_payment_node(state, tools_by_name)

    def node_inspect_customer(state: RecoveryAgentState):
        return inspect_customer_node(state, tools_by_name)

    def node_agent_reasoning(state: RecoveryAgentState):
        return agent_reasoning_node(state, reasoner)

    def node_policy_check(state: RecoveryAgentState):
        return policy_check_node(state)

    def node_execute_action(state: RecoveryAgentState):
        return execute_action_node(state, tools_by_name)

    builder.add_node("inspect_payment", node_inspect_payment)
    builder.add_node("inspect_customer", node_inspect_customer)
    builder.add_node("agent_reasoning", node_agent_reasoning)
    builder.add_node("policy_check", node_policy_check)
    builder.add_node("execute_action", node_execute_action)

    builder.add_edge(START, "inspect_payment")

    def inspect_continue(state: RecoveryAgentState) -> str:
        return "end" if state.get("error") else "next"

    builder.add_conditional_edges("inspect_payment", inspect_continue, {"next": "inspect_customer", "end": END})
    builder.add_conditional_edges("inspect_customer", inspect_continue, {"next": "agent_reasoning", "end": END})

    builder.add_edge("agent_reasoning", "policy_check")
    builder.add_edge("policy_check", "execute_action")

    builder.add_conditional_edges(
        "execute_action",
        evaluate_result_routing,
        {
            "continue": "agent_reasoning",
            "end": END,
        },
    )

    return builder.compile()
