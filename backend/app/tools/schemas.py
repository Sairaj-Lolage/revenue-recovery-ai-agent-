"""
backend/app/tools/schemas.py
============================
Pydantic schemas for agent tool inputs and outputs.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input Schemas
# ---------------------------------------------------------------------------

class GetPaymentInput(BaseModel):
    payment_id: int = Field(..., description="ID of the payment to retrieve", gt=0)


class GetCustomerHistoryInput(BaseModel):
    customer_id: int = Field(..., description="ID of the customer to retrieve history for", gt=0)


class RetryPaymentInput(BaseModel):
    payment_id: int = Field(..., description="ID of the payment to retry", gt=0)


class CreatePaymentLinkInput(BaseModel):
    payment_id: int = Field(..., description="ID of the payment to create a link for", gt=0)


class SendRecoveryMessageInput(BaseModel):
    customer_id: int = Field(..., description="ID of the customer to message", gt=0)
    message: str = Field(..., description="Message text to send to customer", min_length=1)
    payment_link: Optional[str] = Field(default=None, description="Optional payment link URL")


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------

class GetPaymentResponse(BaseModel):
    success: bool = Field(..., description="True if payment found, False otherwise")
    payment_id: Optional[int] = Field(default=None, description="Payment ID")
    customer_id: Optional[int] = Field(default=None, description="Customer ID")
    amount_paise: Optional[int] = Field(default=None, description="Amount in paise (integer)")
    currency: Optional[str] = Field(default=None, description="Currency code (e.g. INR)")
    status: Optional[str] = Field(default=None, description="Payment status")
    failure_reason: Optional[str] = Field(default=None, description="Reason for payment failure")
    attempt_count: Optional[int] = Field(default=None, description="Number of retry attempts made")
    error: Optional[str] = Field(default=None, description="Error code if request failed")
    message: Optional[str] = Field(default=None, description="Human-readable message or error description")


class GetCustomerHistoryResponse(BaseModel):
    success: bool = Field(..., description="True if customer found, False otherwise")
    customer_id: Optional[int] = Field(default=None, description="Customer ID")
    name: Optional[str] = Field(default=None, description="Customer name")
    segment: Optional[str] = Field(default=None, description="Customer segment (e.g. SMB, Enterprise)")
    total_paid_paise: Optional[int] = Field(default=None, description="Total amount successfully paid in paise")
    successful_payments: Optional[int] = Field(default=None, description="Count of successful payments")
    failed_payments: Optional[int] = Field(default=None, description="Count of failed payments")
    opted_out: Optional[bool] = Field(default=None, description="True if customer opted out of recovery messages")
    error: Optional[str] = Field(default=None, description="Error code if request failed")
    message: Optional[str] = Field(default=None, description="Human-readable message or error description")


class RetryPaymentResponse(BaseModel):
    success: bool = Field(..., description="True if retry attempt succeeded")
    payment_id: int = Field(..., description="Payment ID")
    amount_recovered_paise: int = Field(..., description="Amount recovered in paise")
    status: str = Field(..., description="Status result of retry (success, failed, blocked, already_successful)")
    message: str = Field(..., description="Human-readable message")
    error: Optional[str] = Field(default=None, description="Error code if request failed")


class CreatePaymentLinkResponse(BaseModel):
    success: bool = Field(..., description="True if payment link created successfully")
    payment_id: int = Field(..., description="Payment ID")
    payment_link: Optional[str] = Field(default=None, description="Generated payment link URL")
    message: str = Field(..., description="Human-readable message")
    error: Optional[str] = Field(default=None, description="Error code if request failed")


class SendRecoveryMessageResponse(BaseModel):
    success: bool = Field(..., description="True if message sent successfully")
    customer_id: int = Field(..., description="Customer ID")
    channel: str = Field(default="mock", description="Messaging channel used")
    message_id: Optional[str] = Field(default=None, description="Generated message ID")
    message: str = Field(..., description="Message text or failure description")
    error: Optional[str] = Field(default=None, description="Error code if request failed")
