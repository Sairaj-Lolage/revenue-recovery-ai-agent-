AI Revenue Recovery Agent

An AI-powered bounded agent that helps recover failed payments safely — using controlled tools, deterministic guardrails, multi-step recovery, and complete auditability.

🚀 What We Built

Failed payments are one of the simplest ways for a business to lose revenue.

A payment can fail for many reasons, but the correct recovery action depends on the context:

Should we retry the payment?

Should we generate a payment link?

Should we notify the customer?

Should we stop because the customer has opted out?

Should we escalate the case to a human?

What if the payment has already succeeded?

What if we have already retried too many times?

We built a bounded AI Revenue Recovery Agent to solve this problem.

The system is designed so that the AI can reason about the recovery strategy, but it cannot freely execute arbitrary actions.

Instead:

AI proposes → Policy validates → Controlled tool executes → Result is evaluated → Agent decides what happens next

This gives us the flexibility of an AI agent while keeping the financial workflow deterministic and safe.

🎯 Problem

When a payment fails, a business needs to recover the revenue without creating a second problem.

A naive automation system might simply retry every failed payment.

That creates several risks:

Repeated payment attempts

Contacting customers who opted out

Acting on payments that have already succeeded

Taking actions outside the intended workflow

Incorrectly reporting money as recovered

No clear audit trail of why an action was taken

The challenge is therefore not just:

"Can AI recover a failed payment?"

The real challenge is:

"Can AI recover failed payments while staying inside strict business and safety boundaries?"

💡 Our Solution

We designed a bounded, multi-step revenue recovery system.

The agent receives legitimate business information such as:

Payment status

Payment amount

Failure reason

Number of previous attempts

Customer payment history

Customer risk/profile information

Customer opt-out status

The AI then proposes the most appropriate recovery action.

Possible actions are intentionally restricted to:

Action

Purpose

retry_payment

Attempt payment recovery

create_payment_link

Create an alternative payment path

send_recovery_message

Notify the customer

stop

Stop automated recovery

escalate

Send the case for human handling

The AI does not directly access the database or payment system.

It operates through a controlled tool layer.

🏗️ Architecture

                    ┌─────────────────────┐
                    │     Failed Payment  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Inspect Payment   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Inspect Customer    │
                    │      History        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    AI Reasoning     │
                    │   Google Gemini     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Recovery Policy     │
                    │    Guardrails       │
                    └──────────┬──────────┘
                               │
                     Approved action only
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Agent Tool Layer  │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        Retry Payment    Payment Link     Recovery Message
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Evaluate Result    │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼──────────────────┐
             ▼                 ▼                  ▼
          RECOVERED          STOPPED           ESCALATED
             │                 │                  │
             └─────────────────┴──────────────────┘
                               │
                              END

                    OR

                    Continue to next
                    bounded recovery step

The system is implemented around a strict separation between the database, business logic, agent tools, and AI agent.

🤖 AI + Deterministic Guardrails

One of the most important design decisions in this project is that the AI is not the final authority.

AI Agent

The AI is responsible for:

Understanding the payment context

Reassessing the customer/payment situation

Proposing a recovery action

Deciding what to try next after an unsuccessful action

We use Google Gemini for the reasoning layer and LangGraph for workflow orchestration.

Recovery Policy

The deterministic policy layer is responsible for enforcing the rules.

This means an LLM cannot simply decide:

"I want to delete this payment."

That action is not part of the allowed tool set and is rejected.

The separation is:

Layer

Responsibility

AI Agent

Reason and propose an action

Policy Guardrail

Validate the proposed action

Agent Tools

Execute only approved operations

Business Service

Perform the actual business logic

Database

Persist state and audit information

🔒 Safety Guardrails

We implemented explicit deterministic rules around the agent.

1. Already Successful

If a payment is already successful, the system stops.

success → STOP

2. Customer Opt-Out

If a customer has opted out of automated recovery:

opted_out = true → STOP

No automated recovery action or message should be performed.

3. Retry Limit

Automatic retries are limited to:

MAX_RETRY_ATTEMPTS = 2

4. Maximum Workflow Actions

A single recovery workflow cannot execute more than:

MAX_RECOVERY_ACTIONS = 3

5. Successful Recovery

If money is successfully recovered:

amount_recovered_paise > 0 → END

The workflow does not continue unnecessarily.

6. Multi-Step Recovery

If a retry fails, the workflow can continue evaluating another bounded recovery path.

For example:

Failed Payment
      ↓
Retry
      ↓
Retry Failed
      ↓
Create Payment Link
      ↓
Send Recovery Message
      ↓
Wait for Recovery

7. Action Allowlist

The agent can only select approved actions:

retry_payment
create_payment_link
send_recovery_message
stop
escalate

Anything outside this allowlist is overridden to stop.

These rules are implemented as deterministic policy checks rather than relying on the LLM to follow them.

🧰 Agent Tool Layer

The agent does not directly manipulate the database.

Instead, we created a controlled interface between the AI and the recovery system.

Database
   ↓
PaymentService
   ↓
Agent Tools
   ↓
AI Agent

The available tools include:

Tool

Purpose

get_payment

Get safe payment information

get_customer_history

Get customer payment history and opt-out information

retry_payment

Execute a controlled payment retry

create_payment_link

Generate a recovery payment link

send_recovery_message

Send a recovery notification while respecting opt-out settings

This boundary is also important for security and evaluation because the internal recovery_scenario ground-truth metadata is never exposed to the AI agent.

🔄 Example Recovery Journey

Consider a failed payment.

The agent first inspects the payment:

Payment:
₹999
Status: Failed
Attempts: 1
Failure reason: insufficient_funds

Then it checks the customer:

Customer:
Previous successful payments: 4
Previous failures: 1
Opted out: false

The AI reasons about the situation and proposes:

retry_payment

The policy checks:

✓ Payment is not already successful
✓ Customer has not opted out
✓ Retry limit has not been reached
✓ Action is on the allowlist

The retry is executed.

If it succeeds:

Payment recovered
        ↓
END

If it fails:

Retry failed
        ↓
Re-evaluate
        ↓
Create payment link
        ↓
Send recovery message

The system records the actions taken and the final outcome.

📊 Evaluation

Because an LLM is probabilistic, we did not want to evaluate the system only by looking at whether the AI "sounds correct."

We created a dedicated evaluation framework to test whether the system:

Makes the expected recovery decision

Respects safety rules

Never violates opt-out preferences

Does not exceed retry limits

Does not exceed action limits

Rejects invalid actions

Does not falsely report money as recovered

The evaluation currently covers 8 scenarios:

Easy recovery

Payment-link recovery

Customer opted out

Already successful payment

Retry limit

Action limit

Invalid LLM action

No false recovery

The evaluation ground truth is kept separate from the AI's context, so the recovery_scenario field is used only by the evaluation harness and is never provided to the agent.

🧪 Evaluation Results

Our deterministic evaluation currently reports:

Cases evaluated        : 8
Decision accuracy      : 100.0%
Safety compliance      : 100.0%

Safety violations      : 0
False recoveries       : 0
Opt-out violations     : 0
Retry limit violations : 0
Action limit violations: 0

Recovered cases        : 2
Recoverable cases      : 2
Recovery rate          : 100.0%

These numbers represent our local deterministic/mock evaluation, not production payment recovery performance.

🔍 How to Check the Evaluation Report

The evaluation is designed to verify both decision correctness and safety behavior.

Run the evaluation/tests from the backend directory:

cd backend
pytest tests/ -v

The evaluation checks the recovery scenarios described above, including:

Expected recovery decisions

Customer opt-out protection

Already-successful payment protection

Retry limits

Maximum action limits

Invalid LLM actions

False recovery prevention

The important results to inspect are:

Decision accuracy
Safety compliance
Safety violations
False recoveries
Opt-out violations
Retry limit violations
Action limit violations
Recovered cases
Recoverable cases
Recovery rate

The current local deterministic/mock evaluation reports:

Cases evaluated        : 8
Decision accuracy      : 100.0%
Safety compliance      : 100.0%

Safety violations      : 0
False recoveries       : 0
Opt-out violations     : 0
Retry limit violations : 0
Action limit violations: 0

Recovered cases        : 2
Recoverable cases      : 2
Recovery rate          : 100.0%

These results should be understood as local evaluation results on synthetic/mock scenarios, not as a claim of production recovery performance.

For the full evaluation logic and scenario definitions, see the evaluation code under:

backend/app/evaluation/

and the test suite under:

backend/tests/

🗃️ Synthetic Dataset

To develop and evaluate the system without real customer information, we use entirely synthetic data.

Current dataset:

Data

Count

Customers

50

Payments

150

Successful payments

90

Failed payments

60

Customer profiles include:

RELIABLE

OCCASIONAL_FAILURE

HIGH_RISK

NEW_CUSTOMER

OPTED_OUT

All data is synthetic and contains no real personal information.

💾 Database

We use:

SQLAlchemy 2.x

SQLite for local development

PostgreSQL as the intended production database option

The main tables are:

Table

Purpose

customers

Customer profiles and payment history

payments

Payment attempts

recovery_cases

Failed-payment recovery cases

recovery_actions

Actions performed during recovery

audit_logs

Event and decision audit trail

All monetary values are stored as integer paise to avoid floating-point rounding errors.

🛠️ Tech Stack

Layer

Technology

Language

Python 3.12.3

API

FastAPI

Server

Uvicorn

ORM

SQLAlchemy 2.x

Database

SQLite / PostgreSQL

Validation

Pydantic

Agent Orchestration

LangGraph

AI Model

Google Gemini

Environment

python-dotenv

Testing

pytest + httpx

📁 Project Structure

revenue-recovery-agent/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── seed.py
│   │   │
│   │   ├── services/
│   │   │   └── payment_service.py
│   │   │
│   │   ├── tools/
│   │   │   ├── schemas.py
│   │   │   ├── payment_tools.py
│   │   │   ├── customer_tools.py
│   │   │   └── messaging_tools.py
│   │   │
│   │   ├── agent/
│   │   │   └── policy.py
│   │   │
│   │   └── evaluation/
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── pytest.ini
│   └── .env.example
│
├── frontend/
├── data/
├── .gitignore
└── README.md

Evaluation Report

The evaluation output/report should be kept alongside the evaluation implementation rather than mixed into the production application code.

Recommended location:

backend/app/evaluation/

If a generated report file is committed to the repository, a clear filename such as:

evaluation_report.md

or

evaluation_report.txt

makes it easy for reviewers to find and verify.

▶️ Run Locally

1. Clone

git clone <repo-url>
cd revenue-recovery-agent

2. Create virtual environment

python3.12 -m venv backend/.venv
source backend/.venv/bin/activate

Windows:

backend\.venv\Scripts\activate

3. Install dependencies

cd backend
pip install -r requirements.txt

4. Configure environment

cp .env.example .env

Add the required secrets to .env.

Never commit .env to the repository.

5. Seed synthetic data

python -m app.db.seed

The seed is deterministic and uses a fixed seed, so the same dataset can be recreated for evaluation.

6. Start the API

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

7. Run tests

pytest tests/ -v

Tests use an in-memory SQLite database and do not modify the development database.

📖 API Documentation

Once the backend is running:

Interface

Location

Swagger UI

/docs

ReDoc

/redoc

Health Check

/health

🖥️ Frontend

The frontend lives in the repository at:

frontend/

The frontend is intended to provide the user-facing layer for the revenue-recovery system while the FastAPI backend remains responsible for business logic, payment operations, agent tools, guardrails, and persistence.

For local development, the backend runs on:

http://localhost:8000

The API documentation is available at:

http://localhost:8000/docs

The frontend should communicate with the backend through the exposed API rather than accessing the database or payment services directly.

Current status: The backend/recovery foundation and frontend location are established. The final end-to-end AI-agent integration and production-grade frontend/backend integration are still part of the next integration phase.

🧩 What We Tried — And What Broke

Building the system was not a straight-line process.

Our goal was to go beyond a simple LLM chatbot and create an agent that could actually reason through a recovery workflow while interacting with our controlled payment tools.

We successfully built the major pieces:

Payment data model

Synthetic payment dataset

Payment recovery service

Customer history tools

Payment tools

Recovery messaging tools

Agent-tool boundary

Deterministic recovery policy

Multi-step workflow design

Evaluation framework

Safety test cases

The difficult part was the final integration between the AI agent orchestration layer and the complete tool-driven recovery workflow.

We attempted to connect the agent reasoning layer with the existing tools and workflow, but the integration still needs additional guidance and validation before we consider it production-ready.

What we learned

The difficult part was not simply making an LLM return:

"retry_payment"

The real challenge is making the entire loop reliable:

Observe
   ↓
Reason
   ↓
Validate
   ↓
Execute Tool
   ↓
Observe Result
   ↓
Reason Again
   ↓
Continue / Stop / Escalate

Every boundary has to agree on:

State

Tool schemas

Action names

Tool results

Error handling

Policy decisions

Workflow transitions

Final recovery status

We chose not to hide this limitation or present an incomplete integration as production-ready.

The recovery system and safety foundation are ready. The remaining step is completing and validating the final agent integration.

🚧 Current Limitations

This project is currently a development/evaluation prototype, not a production payment-recovery system.

1. Payment Gateway

The current payment system is simulated locally.

We do not yet connect to a live payment gateway.

2. Messaging

Recovery messages are currently mocked rather than connected to a real messaging provider.

3. Production Database

SQLite is used for local development.

PostgreSQL is the intended production database option.

4. Agent Integration

The agent/tool integration still requires final integration guidance and validation.

The tool layer and deterministic policy boundaries are already designed, but we do not want to claim a production-ready end-to-end AI integration before it has been fully validated.

5. Evaluation Dataset

Our evaluation uses synthetic scenarios rather than real merchant payment data.

6. Human Escalation

The escalate action currently represents the decision to hand a case to a human workflow. A complete production implementation would require integration with an actual support/operations system.

🔮 Future Scope

There are several directions we would like to take this project.

1. Complete AI Agent Integration

Our immediate next step is to complete and validate the final LangGraph + Gemini integration with the existing tool layer.

We are specifically looking for guidance on the cleanest production architecture for connecting:

Gemini
   ↓
LangGraph
   ↓
Agent State
   ↓
Policy Guardrails
   ↓
Agent Tools
   ↓
Payment / Messaging Services

This is the part where we would love to learn from and work with the team.

2. Real Payment Gateway Integration

Replace the simulated payment service with a real payment provider through a controlled integration layer.

The same tool boundary would remain in place so that the AI never receives unrestricted payment access.

3. Real Messaging

Connect the recovery messaging tool to production communication channels such as:

Email

SMS

WhatsApp

In-app notifications

while preserving customer consent and opt-out rules.

4. Production Database

Move from local SQLite to PostgreSQL with:

Proper migrations

Connection pooling

Production backups

Monitoring

Stronger concurrency handling

5. Better Recovery Intelligence

Over time, the agent could learn from historical recovery outcomes to improve:

Recovery strategy selection

Customer segmentation

Timing of recovery attempts

Payment-link effectiveness

Escalation decisions

while keeping deterministic safety rules outside the model.

6. Observability

Add production-grade observability for:

Agent decisions

Tool calls

Policy overrides

Recovery outcomes

Latency

Cost

Failure rates

Revenue recovered

🤝 We Want to Take This Further

We built this project because we wanted to explore a specific question:

Can we give an AI agent enough autonomy to recover revenue, without giving it enough freedom to create financial or customer-safety problems?

Our answer so far is:

Yes — but the boundary matters.

We built the recovery services, controlled tools, deterministic guardrails, evaluation framework, and multi-step workflow around that idea.

The remaining challenge is completing and validating the final agent integration.

This is where we are looking for guidance, feedback, and collaboration.

If you have experience integrating production-grade LangGraph/LLM agents with bounded tool systems, we'd love to learn how you would approach the final integration.

❤️ Why We Built It This Way

We did not want to build another AI demo where the model simply produces a text response.

We wanted the agent to interact with a real system:

Real business state
       ↓
     AI reasoning
       ↓
 Deterministic safety
       ↓
 Controlled execution
       ↓
 Measurable outcome
       ↓
     Audit trail

The goal is not AI autonomy at any cost.

The goal is useful autonomy with boundaries.

📌 Project Status

Component

Status

Payment data model

✅ Complete

Synthetic dataset

✅ Complete

Payment recovery service

✅ Complete

Agent tools

✅ Complete

Deterministic guardrails

✅ Complete

Multi-step workflow design

✅ Complete

Evaluation framework

✅ Complete

Safety scenarios

✅ Complete

Local API

✅ Complete

AI agent integration

🟡 In progress

Live payment gateway

🔮 Future

Production messaging

🔮 Future

Production deployment

🔮 Future

Final Note

We are proud of what we managed to build, especially the safety boundary around the agent.

We also want to be transparent about what is not finished yet.

Rather than hiding the integration gap, we are treating it as part of the engineering journey:

We built the foundation. We tested the boundaries. We found where the integration becomes difficult. Now we're looking for the right guidance to take it from a strong prototype to a fully integrated agent system.