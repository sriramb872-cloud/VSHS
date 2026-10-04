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


class CheckoutResponse(SubscriptionPaymentResponse):
    """What ``POST /payments`` returns: the payment row + checkout handle.

    Superset of :class:`SubscriptionPaymentResponse`, so the development mock
    flow keeps working unchanged (its extra fields are simply ``null``).

    For ``provider="RAZORPAY"`` the browser needs four things to open
    Checkout.js: the PUBLIC key id, the order id, the amount in paise and the
    currency. The key SECRET and the webhook secret are deliberately not part
    of this model - they never leave the server.
    """

    amount_paise: Optional[int] = None
    razorpay_key_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None


class RazorpayVerifyRequest(BaseModel):
    """Browser checkout callback (``POST /payments/{id}/verify``).

    Deliberately WITHOUT an order id or an amount: the order comes from the
    payment row in the database and the amount is re-read from Razorpay, so a
    client can neither choose what it paid nor claim a success.
    """

    razorpay_payment_id: str = Field(..., min_length=1, max_length=64)
    razorpay_signature: str = Field(..., min_length=1, max_length=256)


class RazorpayWebhookResponse(BaseModel):
    """Ack for Razorpay's webhook (200 == "do not retry")."""

    status: str = "ok"
    payment_id: Optional[int] = None


class SubscriptionPaymentListResponse(BaseModel):
    total: int
    items: List[SubscriptionPaymentResponse]
