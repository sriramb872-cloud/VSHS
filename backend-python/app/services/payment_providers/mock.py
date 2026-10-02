# backend-python/app/services/payment_providers/mock.py
"""Development-only payment provider (provider = "INTERNAL").

Behaves like a real provider from the subscription system's point of view:

* ``create_order()`` issues an order id.
* ``build_result_payload()`` plays the role of the provider's hosted
  checkout: it produces the *provider's signed response* for a chosen test
  outcome (SUCCESS / FAILED / CANCELLED / PENDING).
* ``verify_payment()`` re-derives the HMAC signature from the server-side
  secret and checks amount + currency against what we ordered - exactly the
  boundary a real provider's signature verification enforces. The HTTP
  client only ever supplies the desired test *outcome*; it can never forge
  a verified success without the secret, and the subscription service only
  activates access after this verification passes.

The provider is disabled whenever ENVIRONMENT=production
(``PaymentService.mock_payments_enabled``), so no checkout route works in
production.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

from app.services.payment_providers.base import (
    OrderRequest,
    PaymentOrder,
    PaymentProvider,
    PaymentProviderError,
    RefundResult,
    VerificationResult,
)

_VALID_OUTCOMES = ("SUCCESS", "FAILED", "CANCELLED", "PENDING")


class MockPaymentProvider(PaymentProvider):
    name = "INTERNAL"

    def __init__(self, secret: str):
        self._secret = (secret or "").encode("utf-8")

    # -- helpers ------------------------------------------------------------

    def _sign(self, *parts: Any) -> str:
        message = ":".join(str(p) for p in parts)
        return hmac.new(self._secret, message.encode("utf-8"), hashlib.sha256).hexdigest()

    # -- PaymentProvider contract -------------------------------------------

    def create_order(self, request: OrderRequest) -> PaymentOrder:
        return PaymentOrder(
            provider=self.name,
            order_id=f"mock_order_{uuid.uuid4().hex}",
            status="PENDING",
            amount=request.amount,
            currency=request.currency,
        )

    def build_result_payload(
        self,
        *,
        order_id: str,
        amount: Decimal,
        currency: str,
        user_id: int,
        plan_id: int,
        outcome: str,
    ) -> Dict[str, Any]:
        """Simulate the provider's signed checkout/webhook response.

        Called server-side; the caller's requested ``outcome`` is baked into
        the signature so ``verify_payment`` can authenticate it.
        """
        outcome = str(outcome or "").upper()
        if outcome not in _VALID_OUTCOMES:
            raise PaymentProviderError(
                "INVALID_OUTCOME",
                f"outcome must be one of: {', '.join(_VALID_OUTCOMES)}",
            )
        amount_text = f"{Decimal(amount):.2f}"
        payment_id = (
            f"mockpay_{uuid.uuid4().hex[:24]}" if outcome == "SUCCESS" else None
        )
        return {
            "order_id": order_id,
            "status": outcome,
            "payment_id": payment_id,
            "amount": amount_text,
            "currency": currency,
            "user_id": user_id,
            "plan_id": plan_id,
            "signature": self._sign(
                order_id, outcome, amount_text, currency, user_id, plan_id
            ),
        }

    def verify_payment(
        self,
        payload: Dict[str, Any],
        *,
        expected_amount: Optional[Decimal] = None,
        expected_currency: Optional[str] = None,
    ) -> VerificationResult:
        required = ("order_id", "status", "amount", "currency", "signature")
        missing = [key for key in required if not payload.get(key) and payload.get(key) != 0]
        if missing:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message=f"missing fields: {', '.join(missing)}",
            )

        status = str(payload["status"]).upper()
        if status not in _VALID_OUTCOMES:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="unknown status",
            )

        try:
            amount = Decimal(str(payload["amount"]))
            amount_text = f"{amount:.2f}"
        except (InvalidOperation, ValueError):
            return VerificationResult(
                provider=self.name, verified=False, status="FAILED", message="bad amount"
            )

        expected_signature = self._sign(
            payload["order_id"],
            status,
            amount_text,
            payload["currency"],
            payload.get("user_id"),
            payload.get("plan_id"),
        )
        if not hmac.compare_digest(str(payload["signature"]), expected_signature):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="signature mismatch",
            )

        if expected_amount is not None and amount != Decimal(expected_amount):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="amount mismatch",
            )
        if (
            expected_currency is not None
            and str(payload["currency"]).upper() != str(expected_currency).upper()
        ):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="currency mismatch",
            )

        return VerificationResult(
            provider=self.name,
            verified=True,
            status=status,
            provider_payment_id=payload.get("payment_id"),
            amount=amount,
            currency=str(payload["currency"]).upper(),
            message="ok",
        )

    def handle_webhook(
        self, headers: Dict[str, str], body: bytes
    ) -> VerificationResult:
        signature = headers.get("x-mock-signature") or headers.get("X-Mock-Signature")
        expected = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(str(signature), expected):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="webhook signature mismatch",
            )
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return VerificationResult(
                provider=self.name, verified=False, status="FAILED", message="bad body"
            )
        return self.verify_payment(payload)

    def refund_payment(
        self, *, order_id: str, amount: Optional[Decimal] = None
    ) -> RefundResult:
        return RefundResult(
            provider=self.name,
            status="REFUNDED",
            provider_refund_id=f"mockrefund_{uuid.uuid4().hex[:20]}",
            message=f"mock refund of {amount if amount is not None else 'full amount'}",
        )

    def cancel_payment(self, *, order_id: str) -> VerificationResult:
        return VerificationResult(
            provider=self.name,
            verified=True,
            status="CANCELLED",
            message=f"mock order {order_id} cancelled",
        )
