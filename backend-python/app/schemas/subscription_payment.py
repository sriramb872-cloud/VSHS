# backend-python/app/schemas/subscription_payment.py
"""Pydantic schemas for subscription payment records (provider-agnostic)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PaymentCreateRequest(BaseModel):
    plan_id: int = Field(..., description="Active plan to purchase")


class MockCheckoutRequest(BaseModel):
    """Development-only checkout completion for the INTERNAL mock provider.

    ``outcome`` is what the simulated provider page returned. The server
    still verifies the provider payload (signed order + amount from the DB)
    before any subscription is activated - a client claim alone never grants
    access.
    """

    outcome: str = Field(..., max_length=20, description="SUCCESS | FAILED | CANCELLED | PENDING")


class SubscriptionPaymentResponse(BaseModel):
    id: int
    school_id: int
    user_id: Optional[int] = None
    plan_id: Optional[int] = None
    subscription_id: Optional[int] = None
    amount: float
    currency: str
    provider: str
    provider_order_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionPaymentListResponse(BaseModel):
    total: int
    items: List[SubscriptionPaymentResponse]
