# backend-python/app/services/payment_providers/razorpay.py
"""Razorpay provider - UPI only, one-time prepaid payments (ORDERS API).

WHY ORDERS AND NOT SUBSCRIPTIONS
--------------------------------
Our plans are fixed-duration rows and access is extended by
``SubscriptionService.apply_entitlement``, so we do not want Razorpay to own
the billing cadence. An ORDER is a single prepaid payment for exactly the
amount stored on the plan row; when it is verified we extend access ourselves.
Razorpay's Subscriptions API would introduce proration, cancellations and a
second source of truth for "what the customer owes" - all of which this
module deliberately does not use.

UPI ONLY
--------
India-only product, INR only, and exactly one instrument:
``payment.method == "upi"`` is checked on every server-side verification
(browser callback AND webhook). Cards, netbanking, wallets, EMI and pay-later
are rejected as ``verified=False`` even if they somehow reach us, and the
frontend hides them in Checkout.js.

VERIFICATION BOUNDARIES
-----------------------
* ``verify_payment()``  - signature (constant time) + a fresh fetch FROM
  Razorpay + order/amount/currency/method checks. The browser only tells us
  *which* ids Razorpay handed it; every fact that matters is re-read from
  Razorpay's own API.
* ``handle_webhook()``  - HMAC over the RAW body bytes with the webhook
  secret, before anything else touches the database.
* Only a verified SUCCESS may reach ``PaymentService._finalize``.

NETWORK POLICY
--------------
Every SDK call carries an explicit timeout and is executed exactly ONCE: the
SDK retry loop stays disabled (``build_client``), because a hidden retry on a
money-moving request is how a customer gets charged twice. Failures become
``PaymentProviderError`` with a stable code.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any, Callable, Dict, Optional

import razorpay
from razorpay.errors import BadRequestError, SignatureVerificationError

from app.services.payment_providers.base import (
    OrderRequest,
    PaymentOrder,
    PaymentProvider,
    PaymentProviderError,
    RefundResult,
    VerificationResult,
    to_paise,
)

#: The one instrument this integration accepts.
PAYMENT_METHOD = "upi"

#: Explicit per-call timeout (connect + read) in seconds. No retries.
REQUEST_TIMEOUT_SECONDS = 15.0

#: Razorpay payment status -> our status vocabulary. Anything unknown stays
#: PENDING: an unreadable status must never activate access.
PAYMENT_STATUS_MAP = {
    "captured": "SUCCESS",
    "failed": "FAILED",
    "authorized": "PENDING",
}

#: Webhook event -> our status vocabulary. Unknown events are acknowledged
#: (200) and ignored, so Razorpay does not retry an event we will never use.
WEBHOOK_STATUS_MAP = {
    "payment.captured": "SUCCESS",
    "payment.failed": "FAILED",
}

_SIGNATURE_HEADER = "x-razorpay-signature"


def build_client(key_id: str, key_secret: str) -> Any:
    """Build the Razorpay SDK client.

    Kept as a module-level function so tests can seam it without ever
    reaching the network. Retries stay OFF - see the module docstring.
    """
    client = razorpay.Client(auth=(key_id, key_secret))
    client.enable_retry(False)
    return client


def _receipt() -> str:
    """Unique, short receipt id (Razorpay allows max 40 characters)."""
    return f"sch-{uuid.uuid4().hex[:32]}"  # 36 characters


def _call(
    code: str, message: str, func: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    """Run exactly ONE SDK call and normalise any failure.

    ``BadRequestError`` (a request Razorpay refused) and every transport
    error (timeout, DNS, 5xx) collapse into a ``PaymentProviderError`` with a
    stable code so the caller can map it to a structured HTTP error without
    ever echoing a secret back to the client.
    """
    try:
        return func(*args, **kwargs)
    except SignatureVerificationError:  # pragma: no cover - re-raised by callers
        raise
    except Exception as exc:  # noqa: BLE001 - SDK + requests error surface
        raise PaymentProviderError(code, f"{message}: {exc}") from exc


class RazorpayProvider(PaymentProvider):
    """``PaymentProvider`` implementation backed by Razorpay's Orders API."""

    name = "RAZORPAY"

    def __init__(
        self,
        *,
        key_id: str,
        key_secret: str,
        webhook_secret: str,
        client: Optional[Any] = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ):
        missing = [
            name
            for name, value in (
                ("RAZORPAY_KEY_ID", key_id),
                ("RAZORPAY_KEY_SECRET", key_secret),
                ("RAZORPAY_WEBHOOK_SECRET", webhook_secret),
            )
            if not str(value or "").strip()
        ]
        if missing:
            # Names only - never the values.
            raise PaymentProviderError(
                "RAZORPAY_NOT_CONFIGURED",
                "Razorpay is not configured: " + ", ".join(missing),
            )
        self._key_id = str(key_id)
        self._key_secret = str(key_secret)
        self._webhook_secret = str(webhook_secret)
        self._timeout = float(timeout)
        self._client = (
            client if client is not None else build_client(self._key_id, self._key_secret)
        )

    # -- PaymentProvider contract -------------------------------------------

    def create_order(self, request: OrderRequest) -> PaymentOrder:
        """Open a Razorpay order for the DATABASE amount, in paise."""
        currency = str(request.currency or "INR").upper()
        if currency != "INR":
            raise PaymentProviderError(
                "UNSUPPORTED_CURRENCY",
                "Razorpay checkout is India-only: the currency must be INR",
            )

        # Decimal end-to-end: price -> paise without ever touching a float.
        amount = Decimal(request.amount)
        paise = to_paise(amount)
        if paise < 100:
            raise PaymentProviderError(
                "AMOUNT_TOO_SMALL", "A Razorpay order must be at least 1 INR"
            )

        data: Dict[str, Any] = {
            "amount": paise,
            "currency": currency,
            "receipt": _receipt(),
            "notes": {
                "user_id": str(request.user_id),
                "school_id": str(request.school_id),
                "plan_id": str(request.plan_id),
            },
        }
        order = _call(
            "ORDER_CREATE_FAILED",
            "Could not create the Razorpay order",
            self._client.order.create,
            data,
            timeout=self._timeout,
        )
        order_id = str((order or {}).get("id") or "")
        if not order_id:
            raise PaymentProviderError(
                "ORDER_CREATE_FAILED", "Razorpay did not return an order id"
            )
        return PaymentOrder(
            provider=self.name,
            order_id=order_id,
            status="PENDING",
            amount=amount,
            currency=currency,
        )

    def verify_payment(
        self,
        payload: Dict[str, Any],
        *,
        expected_amount: Optional[Decimal] = None,
        expected_currency: Optional[str] = None,
        expected_order_id: Optional[str] = None,
    ) -> VerificationResult:
        """Verify a browser checkout callback.

        1. constant-time signature check (``order_id|payment_id`` signed with
           our key secret) - the client cannot forge any of this;
        2. fetch the payment from Razorpay - the client is never trusted for
           status, amount, currency or method;
        3. the fetched payment must belong to this order;
        4. amount + currency must equal what WE ordered (from the DB row);
        5. method must be UPI, and only then is the status mapped.
        """
        required = ("razorpay_order_id", "razorpay_payment_id", "razorpay_signature")
        missing = [key for key in required if not str(payload.get(key) or "").strip()]
        if missing:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message=f"missing fields: {', '.join(missing)}",
            )

        order_id = str(payload["razorpay_order_id"])
        payment_id = str(payload["razorpay_payment_id"])
        signature = str(payload["razorpay_signature"])

        if not self._verify_payment_signature(order_id, payment_id, signature):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="signature mismatch",
            )

        if expected_order_id is not None and order_id != str(expected_order_id):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="order mismatch",
            )

        try:
            fetched = (
                self._client.payment.fetch(payment_id, timeout=self._timeout) or {}
            )
        except BadRequestError as exc:
            # Razorpay does not know this payment id: the client made it up.
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message=f"payment not found at Razorpay: {exc}",
            )
        except Exception as exc:  # noqa: BLE001 - timeout / transport failure
            raise PaymentProviderError(
                "PAYMENT_FETCH_FAILED", f"Could not fetch the Razorpay payment: {exc}"
            ) from exc

        if str(fetched.get("order_id") or "") != order_id:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="payment does not belong to this order",
            )

        try:
            paid_paise = int(fetched.get("amount"))
        except (TypeError, ValueError):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="bad amount",
            )
        if expected_amount is not None and paid_paise != to_paise(
            Decimal(expected_amount)
        ):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="amount mismatch",
            )

        paid_currency = str(fetched.get("currency") or "").upper()
        if expected_currency is not None and paid_currency != str(
            expected_currency
        ).upper():
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="currency mismatch",
            )

        if str(fetched.get("method") or "").lower() != PAYMENT_METHOD:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="non-UPI payment",
            )

        status = PAYMENT_STATUS_MAP.get(
            str(fetched.get("status") or "").lower(), "PENDING"
        )
        return VerificationResult(
            provider=self.name,
            verified=True,
            status=status,
            provider_payment_id=str(fetched.get("id") or payment_id),
            amount=Decimal(paid_paise) / 100,
            currency=paid_currency,
            provider_order_id=order_id,
            message="ok",
        )

    def handle_webhook(
        self, headers: Dict[str, str], body: bytes
    ) -> VerificationResult:
        """Verify the webhook signature over the RAW bytes, then decode it."""
        normalized = {str(key).lower(): str(value) for key, value in headers.items()}
        signature = normalized.get(_SIGNATURE_HEADER)
        if not signature:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="missing webhook signature",
            )

        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="webhook body is not valid UTF-8",
            )

        if not self._verify_webhook_signature(text, signature):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="webhook signature mismatch",
            )

        try:
            payload = json.loads(text)
        except ValueError:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="webhook body is not valid JSON",
            )

        event = str(payload.get("event") or "")
        status = WEBHOOK_STATUS_MAP.get(event)
        if status is None:
            # Signed, but not an event we act on: acknowledge it and change
            # nothing (verified=True + PENDING == "no state change").
            return VerificationResult(
                provider=self.name,
                verified=True,
                status="PENDING",
                message=f"ignored event {event or '(none)'}",
            )

        entity = (
            ((payload.get("payload") or {}).get("payment") or {}).get("entity") or {}
        )
        order_id = str(entity.get("order_id") or "")
        if not order_id:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                message="missing order id in webhook payload",
            )

        if str(entity.get("method") or "").lower() != PAYMENT_METHOD:
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="non-UPI payment",
            )

        try:
            paise = int(entity.get("amount"))
        except (TypeError, ValueError):
            return VerificationResult(
                provider=self.name,
                verified=False,
                status="FAILED",
                provider_order_id=order_id,
                message="bad amount",
            )

        # Amount/currency are returned here and compared with the payment row
        # by PaymentService.process_webhook - the row is the source of truth.
        return VerificationResult(
            provider=self.name,
            verified=True,
            status=status,
            provider_payment_id=str(entity.get("id") or "") or None,
            amount=Decimal(paise) / 100,
            currency=str(entity.get("currency") or "").upper(),
            provider_order_id=order_id,
            message="ok",
        )

    def refund_payment(
        self, *, order_id: str, amount: Optional[Decimal] = None
    ) -> RefundResult:
        """Full or partial refund (paise) of the captured payment of an order."""
        payments = _call(
            "REFUND_LOOKUP_FAILED",
            "Could not list the payments of this order",
            self._client.order.payments,
            str(order_id),
            timeout=self._timeout,
        )
        captured = next(
            (
                item
                for item in (payments or [])
                if str((item or {}).get("status") or "").lower() == "captured"
            ),
            None,
        )
        if captured is None or not captured.get("id"):
            raise PaymentProviderError(
                "REFUND_FAILED", "This order has no captured payment to refund"
            )

        data: Dict[str, Any] = {"payment_id": str(captured["id"])}
        if amount is not None:
            data["amount"] = to_paise(Decimal(amount))

        refund = _call(
            "REFUND_FAILED",
            "Razorpay rejected the refund",
            self._client.refund.create,
            data,
            timeout=self._timeout,
        )
        refund_id = str((refund or {}).get("id") or "") or None
        return RefundResult(
            provider=self.name,
            status="REFUNDED",
            provider_refund_id=refund_id,
            message="refund accepted by Razorpay",
        )

    def cancel_payment(self, *, order_id: str) -> VerificationResult:
        """Razorpay orders cannot be cancelled at the provider - local only."""
        return VerificationResult(
            provider=self.name,
            verified=True,
            status="CANCELLED",
            provider_order_id=str(order_id),
            message=(
                "Razorpay orders cannot be cancelled through the API; the local "
                "payment row was marked CANCELLED"
            ),
        )

    # -- signature helpers ---------------------------------------------------

    def _verify_payment_signature(
        self, order_id: str, payment_id: str, signature: str
    ) -> bool:
        """``HMAC_SHA256("order_id|payment_id", key_secret)`` - constant time."""
        try:
            return bool(
                self._client.utility.verify_payment_signature(
                    {
                        "razorpay_order_id": order_id,
                        "razorpay_payment_id": payment_id,
                        "razorpay_signature": signature,
                    }
                )
            )
        except (SignatureVerificationError, KeyError, TypeError, ValueError):
            return False

    def _verify_webhook_signature(self, body: str, signature: str) -> bool:
        """HMAC-SHA256 over the exact bytes Razorpay signed - constant time.

        ``body`` is the UTF-8 decoding of the raw request bytes, so
        ``encode("utf-8")`` inside the utility reproduces those bytes exactly.
        """
        try:
            return bool(
                self._client.utility.verify_webhook_signature(
                    body, signature, self._webhook_secret
                )
            )
        except (SignatureVerificationError, KeyError, TypeError, ValueError):
            return False
