# backend-python/app/services/payment_providers/base.py
"""Payment provider abstraction.

The subscription domain depends on THIS interface only - never on a specific
vendor SDK. Phase 1 ships the development ``MockPaymentProvider``; Phase 2
adds ``RazorpayProvider`` implementing the same contract, and no
subscription business logic changes:

    PaymentService
          |
          +---- MockPaymentProvider   (provider="INTERNAL", dev only)
          |
          +---- RazorpayProvider      (provider="RAZORPAY", Phase 2)

Contract meaning:
    create_order()      - open a checkout for a fixed amount/currency
    verify_payment()    - verify a provider result BEFORE any entitlement
                          changes (server-side, signature + amount check)
    handle_webhook()    - verify + decode an async provider notification
    refund_payment()    - provider-side refund
    cancel_payment()    - provider-side order/payment cancellation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass
class OrderRequest:
    user_id: int
    school_id: int
    plan_id: int
    amount: Decimal
    currency: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentOrder:
    provider: str
    order_id: str
    status: str  # PENDING
    amount: Decimal
    currency: str


@dataclass
class VerificationResult:
    provider: str
    verified: bool
    status: str  # SUCCESS | FAILED | CANCELLED | PENDING | REFUNDED
    provider_payment_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    message: Optional[str] = None


@dataclass
class RefundResult:
    provider: str
    status: str  # REFUNDED | FAILED
    provider_refund_id: Optional[str] = None
    message: Optional[str] = None


class PaymentProviderError(Exception):
    """Provider-level failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class PaymentProvider(ABC):
    """Contract every payment provider must implement."""

    name: str = ""

    @abstractmethod
    def create_order(self, request: OrderRequest) -> PaymentOrder:
        """Open a provider order for the given amount/currency."""

    @abstractmethod
    def verify_payment(
        self,
        payload: Dict[str, Any],
        *,
        expected_amount: Optional[Decimal] = None,
        expected_currency: Optional[str] = None,
    ) -> VerificationResult:
        """Verify a provider result server-side.

        MUST NOT trust the caller: check the provider's signature and that
        the paid amount/currency match what we ordered. Only a verified
        SUCCESS may activate an entitlement.
        """

    @abstractmethod
    def handle_webhook(
        self, headers: Dict[str, str], body: bytes
    ) -> VerificationResult:
        """Verify + decode an async provider notification (webhook)."""

    @abstractmethod
    def refund_payment(
        self, *, order_id: str, amount: Optional[Decimal] = None
    ) -> RefundResult:
        """Refund a captured payment (full or partial)."""

    @abstractmethod
    def cancel_payment(self, *, order_id: str) -> VerificationResult:
        """Cancel a pending order/payment at the provider."""
