# backend-python/app/services/payment.py
"""Payment orchestration - provider-agnostic.

Flow (identical for the mock provider and for Razorpay):

    client -> create_checkout()          -> provider.create_order()
                                         -> subscription_payments row (PENDING)
    client -> checkout at provider -----> provider result (signed)
    server -> verify_client_payment()    -> provider.verify_payment()  <-- boundary
    server -> process_webhook()          -> provider.handle_webhook()  <-- boundary
                                         -> payment status update
                                         -> ONLY on verified SUCCESS:
                                            activate/renew entitlement
                                         -> payment + activation notifications

The client NEVER tells the backend "my payment succeeded" and gets access. It
only reports which ids the provider handed it; the signature, the status, the
amount and the currency are all re-read from the provider, and the values they
are checked against always come from OUR payment row.

Concurrency: every state change funnels through ``_finalize``, which re-reads
the payment row with a lock (``SELECT ... FOR UPDATE``). The browser callback
and Razorpay's webhook routinely race each other - exactly one of them extends
the subscription, and a replay is a no-op.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Mapping, Optional

from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.time_utils import utcnow
from app.models.subscription import Subscription
from app.models.subscription_payment import SubscriptionPayment
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.schemas.subscription_payment import (
    CheckoutResponse,
    RazorpayVerifyRequest,
    SubscriptionPaymentResponse,
)
from app.services.payment_providers import (
    OrderRequest,
    PaymentProvider,
    PaymentProviderError,
    VerificationResult,
    to_paise,
)
from app.services.payment_providers.mock import MockPaymentProvider
from app.services.subscription import (
    SubscriptionError,
    SubscriptionService,
    notify_user,
)

# Structured logs for the payment domain. NEVER attach a key secret, a webhook
# secret or a client signature to a record.
logger = logging.getLogger("scholaris.payments")


class PaymentService:
    """Static-method service (house style)."""

    # -----------------------------------------------------------------------
    # Provider availability
    # -----------------------------------------------------------------------

    @staticmethod
    def mock_payments_enabled() -> bool:
        """Mock checkout is a development tool, NEVER a production one.

        Hard-disabled when ENVIRONMENT=production regardless of flags, and
        can be switched off elsewhere with ENABLE_MOCK_PAYMENTS=0.
        """
        env = os.getenv("ENVIRONMENT", "").strip().lower()
        if env == "production":
            return False
        flag = os.getenv("ENABLE_MOCK_PAYMENTS", "1").strip().lower()
        return flag in ("1", "true", "yes", "on")

    @staticmethod
    def active_provider() -> str:
        """Provider used for NEW checkouts (``PAYMENT_PROVIDER`` setting)."""
        name = str(app_settings.PAYMENT_PROVIDER or "INTERNAL").strip().upper()
        return name or "INTERNAL"

    @staticmethod
    def get_provider(provider: Optional[str] = None) -> PaymentProvider:
        """Resolve a provider name; defaults to the configured one.

        Callers that hold a payment row pass ``payment.provider`` so a
        verification/cancellation always talks to the provider that took the
        money, even if the configuration changed in between.
        """
        name = str(provider or PaymentService.active_provider()).strip().upper()
        if name == "INTERNAL":
            if not PaymentService.mock_payments_enabled():
                raise SubscriptionError(
                    "PAYMENT_PROVIDER_UNAVAILABLE",
                    "Mock payments are disabled in this environment",
                    400,
                )
            return MockPaymentProvider(secret=app_settings.SECRET_KEY)
        if name == "RAZORPAY":
            # Imported lazily on purpose: an environment that only ever runs
            # the mock provider never needs the Razorpay SDK on its import
            # path, and a misconfiguration becomes a structured 400 instead
            # of an import-time crash.
            from app.services.payment_providers.razorpay import RazorpayProvider

            try:
                return RazorpayProvider(
                    key_id=app_settings.RAZORPAY_KEY_ID or "",
                    key_secret=app_settings.RAZORPAY_KEY_SECRET or "",
                    webhook_secret=app_settings.RAZORPAY_WEBHOOK_SECRET or "",
                )
            except PaymentProviderError as exc:
                raise SubscriptionError(exc.code, exc.message, 400)
        raise SubscriptionError(
            "PAYMENT_PROVIDER_UNAVAILABLE",
            f"Payment provider {name} is not configured",
            400,
        )

    # -----------------------------------------------------------------------
    # Checkout
    # -----------------------------------------------------------------------

    @staticmethod
    def create_checkout(
        db: Session, *, user: User, plan_id: int
    ) -> SubscriptionPayment:
        """Open a PENDING payment for an active plan of the user's own school.

        Amount/currency always come from the DATABASE plan - the client only
        chooses which plan it wants, never the price. The provider comes from
        ``PAYMENT_PROVIDER`` (INTERNAL in development, RAZORPAY in production).
        """
        SubscriptionService._ensure_billable(user)
        plan = (
            db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        )
        if plan is None:
            raise SubscriptionError("PLAN_NOT_FOUND", "Plan not found", 404)
        SubscriptionService.ensure_plan_usable(db, plan=plan, target=user)

        provider = PaymentService.get_provider()
        order = provider.create_order(
            OrderRequest(
                user_id=user.id,
                school_id=user.school_id or 0,
                plan_id=plan.id,
                amount=Decimal(plan.price),
                currency=plan.currency,
            )
        )

        payment = SubscriptionPayment(
            school_id=plan.school_id,
            user_id=user.id,
            plan_id=plan.id,
            subscription_id=None,
            amount=Decimal(plan.price),
            currency=plan.currency,
            provider=provider.name,
            provider_order_id=order.order_id,
            provider_payment_id=None,
            status="PENDING",
            paid_at=None,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def checkout_response(payment: SubscriptionPayment) -> CheckoutResponse:
        """Serialise a payment for the browser's checkout screen.

        Adds exactly what Checkout.js needs - the PUBLIC key id, the order id
        and the amount in paise. The key secret and the webhook secret are
        never referenced here and can never end up in a response body.
        """
        response = CheckoutResponse.model_validate(payment)
        response.amount_paise = to_paise(Decimal(payment.amount))
        response.currency = str(payment.currency)
        if str(payment.provider).upper() == "RAZORPAY":
            response.razorpay_key_id = app_settings.RAZORPAY_KEY_ID or None
            response.razorpay_order_id = payment.provider_order_id
        return response

    # -----------------------------------------------------------------------
    # Payment lookup (every mutation goes through the same 404 leak guard)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_payment(
        db: Session, *, user: User, payment_id: int
    ) -> SubscriptionPayment:
        """Load one of the caller's own payments.

        Another user's payment id is reported exactly like a missing one -
        the API never confirms that someone else's row exists.
        """
        payment = (
            db.query(SubscriptionPayment)
            .filter(SubscriptionPayment.id == payment_id)
            .first()
        )
        if payment is None or payment.user_id != user.id:
            raise SubscriptionError("PAYMENT_NOT_FOUND", "Payment not found", 404)
        return payment

    # -----------------------------------------------------------------------
    # Completion (verified provider result -> entitlement)
    # -----------------------------------------------------------------------

    @staticmethod
    def _finalize(
        db: Session,
        *,
        payment: SubscriptionPayment,
        verification: VerificationResult,
        user: Optional[User] = None,
    ) -> SubscriptionPayment:
        """Apply an ALREADY VERIFIED provider result. Idempotent + race-safe.

        Shared by mock completion, the browser callback and Razorpay's
        webhook, so all three behave identically:

        * the row is re-read WITH A LOCK (``SELECT ... FOR UPDATE``) - the
          callback and the webhook race each other and exactly one of them
          may extend the subscription;
        * already ``SUCCESS`` -> returned untouched (a replay never extends
          access a second time);
        * ``PENDING`` (e.g. a UPI payment authorised but not captured yet)
          -> left PENDING for the webhook to resolve later;
        * notifications, the subscription audit and the platform audit are
          exactly as before.

        ``user`` is the authenticated caller when there is one; a webhook has
        no session, so the owner is then derived from the payment row.
        """
        locked = (
            db.query(SubscriptionPayment)
            .filter(SubscriptionPayment.id == payment.id)
            .with_for_update()
            .first()
        )
        if locked is None:
            raise SubscriptionError("PAYMENT_NOT_FOUND", "Payment not found", 404)
        payment = locked

        if payment.status == "SUCCESS":
            # Verified replay (callback vs webhook): extend nothing.
            db.commit()
            return payment
        if verification.status == "PENDING":
            db.commit()  # nothing changed; keep the row PENDING
            return payment

        if user is None and payment.user_id:
            user = db.query(User).filter(User.id == payment.user_id).first()

        payment.status = verification.status
        if verification.provider_payment_id:
            # Keep the provider reference for audit/support (both for a
            # captured payment and for the attempt that failed).
            payment.provider_payment_id = verification.provider_payment_id

        if verification.status == "SUCCESS":
            payment.paid_at = utcnow()

            if user is None:
                # The account behind this payment is gone: record the money,
                # never invent an entitlement for nobody.
                logger.warning(
                    "payment finalized without an owner",
                    extra={"payment_id": payment.id, "provider": payment.provider},
                )
            else:
                plan = (
                    db.query(SubscriptionPlan)
                    .filter(SubscriptionPlan.id == payment.plan_id)
                    .first()
                )
                if plan is None:
                    raise SubscriptionError("PLAN_NOT_FOUND", "Plan not found", 404)
                # Renewal rules live in apply_entitlement: extend an active
                # subscription from its existing end, start fresh when expired.
                subscription = SubscriptionService.apply_entitlement(
                    db,
                    user=user,
                    plan=plan,
                    source="PAYMENT",
                    activate=True,
                    amount=Decimal(payment.amount),
                    currency=str(payment.currency),
                )
                payment.subscription_id = subscription.id
                SubscriptionService.audit(
                    db,
                    action="USER_SUBSCRIPTION_GRANTED",
                    school_id=payment.school_id,
                    admin_id=None,
                    user_id=user.id,
                    new_value=(
                        f"{SubscriptionService._plan_value(plan)} until "
                        f"{subscription.end_at.isoformat()}"
                    ),
                    reason=f"Payment #{payment.id} via {payment.provider}",
                )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        # ---- best-effort notifications (after the commit) ----------------
        if user is None:
            pass  # nobody to notify; the platform audit below still runs
        elif payment.status == "SUCCESS":
            notify_user(
                db,
                user=user,
                title="Payment successful",
                message=(
                    f"We received {payment.amount} {payment.currency} for your "
                    f"subscription payment #{payment.id}."
                ),
                reference_id=payment.id,
            )
            sub = (
                db.query(Subscription)
                .filter(Subscription.id == payment.subscription_id)
                .first()
            )
            notify_user(
                db,
                user=user,
                title="Subscription activated",
                message=(
                    f"Your subscription is active until "
                    f"{sub.end_at.strftime('%d %b %Y')}."
                    if sub is not None
                    else "Your subscription is active."
                ),
                reference_id=payment.subscription_id,
            )
        elif payment.status == "FAILED":
            notify_user(
                db,
                user=user,
                title="Payment failed",
                message=(
                    f"Your payment #{payment.id} failed. You can try again "
                    f"from the Subscription page."
                ),
                reference_id=payment.id,
            )

        SubscriptionService._platform_audit(
            db,
            admin=None,
            school_id=payment.school_id,
            action="UPDATE",
            resource_id=payment.id,
            details={
                "payment_status": payment.status,
                "provider": payment.provider,
                "amount": str(payment.amount),
            },
        )
        return payment

    @staticmethod
    def complete_mock_checkout(
        db: Session, *, user: User, payment_id: int, outcome: str
    ) -> SubscriptionPayment:
        """Complete a PENDING mock checkout.

        The client supplies only the test outcome. The provider payload is
        built + signed server-side and verified before any state changes -
        the same boundary Razorpay's signature verification enforces.
        """
        provider = PaymentService.get_provider("INTERNAL")  # raises if disabled

        payment = PaymentService.get_payment(db, user=user, payment_id=payment_id)
        if payment.status == "SUCCESS":
            # Idempotent: a double-click on completion must not double-extend.
            return payment
        if payment.status != "PENDING":
            raise SubscriptionError(
                "PAYMENT_NOT_PENDING",
                f"Payment is {payment.status.lower()} and cannot be completed",
            )

        outcome_value = str(outcome or "").upper()
        try:
            payload = provider.build_result_payload(
                order_id=str(payment.provider_order_id),
                amount=Decimal(payment.amount),
                currency=str(payment.currency),
                user_id=payment.user_id or 0,
                plan_id=payment.plan_id or 0,
                outcome=outcome_value,
            )
        except PaymentProviderError as exc:
            raise SubscriptionError(exc.code, exc.message)

        verification = provider.verify_payment(
            payload,
            expected_amount=Decimal(payment.amount),
            expected_currency=str(payment.currency),
            expected_order_id=str(payment.provider_order_id),
        )
        if not verification.verified:
            # Signature/amount mismatch = tampering or corruption. Fail loud,
            # change nothing.
            raise SubscriptionError(
                "PAYMENT_VERIFICATION_FAILED",
                "Payment verification failed",
                400,
            )

        return PaymentService._finalize(
            db, payment=payment, verification=verification, user=user
        )

    # -----------------------------------------------------------------------
    # Razorpay: browser callback + webhook
    # -----------------------------------------------------------------------

    @staticmethod
    def verify_client_payment(
        db: Session, *, user: User, payment_id: int, payload: RazorpayVerifyRequest
    ) -> SubscriptionPayment:
        """Verify the browser's Razorpay checkout callback, server-side.

        The client supplies exactly two values: the payment id and the
        signature Razorpay generated for it. The ORDER id comes from our row,
        the expected amount and currency come from our row, and the payment
        itself is fetched back from Razorpay before anything is trusted - so
        a client can neither choose what it paid nor claim a success it did
        not make.
        """
        payment = PaymentService.get_payment(db, user=user, payment_id=payment_id)
        if payment.status == "SUCCESS":
            # Replay of an already finalized payment: extend nothing.
            return payment

        provider = PaymentService.get_provider(payment.provider)
        try:
            verification = provider.verify_payment(
                {
                    "razorpay_order_id": str(payment.provider_order_id),
                    "razorpay_payment_id": str(payload.razorpay_payment_id),
                    "razorpay_signature": str(payload.razorpay_signature),
                },
                expected_amount=Decimal(payment.amount),
                expected_currency=str(payment.currency),
                expected_order_id=str(payment.provider_order_id),
            )
        except PaymentProviderError as exc:
            logger.warning(
                "payment verification errored",
                extra={"payment_id": payment.id, "code": exc.code},
            )
            raise SubscriptionError(exc.code, exc.message, 400)

        if not verification.verified:
            logger.warning(
                "payment verification rejected",
                extra={"payment_id": payment.id, "reason": verification.message},
            )
            raise SubscriptionError(
                "PAYMENT_VERIFICATION_FAILED",
                "Payment verification failed",
                400,
            )

        return PaymentService._finalize(
            db, payment=payment, verification=verification, user=user
        )

    @staticmethod
    def process_webhook(
        db: Session, *, headers: Mapping[str, str], body: bytes
    ) -> Optional[SubscriptionPayment]:
        """Handle a Razorpay webhook.

        * signature over the RAW body bytes is verified first - nothing is
          written to the database before that passes (a bad signature is a
          ``400``, never a silent 200);
        * an unknown event or an unknown order id is logged and ACKed with
          ``None`` (the router answers 200) so Razorpay does not retry an
          event we will never act on;
        * there is no user session here: the owner comes from the payment row.

        Returns the finalized payment, or ``None`` when there was nothing to
        do.
        """
        provider = PaymentService.get_provider("RAZORPAY")
        normalized = {str(key).lower(): str(value) for key, value in headers.items()}

        try:
            result = provider.handle_webhook(normalized, body)
        except PaymentProviderError as exc:
            logger.warning("razorpay webhook errored", extra={"code": exc.code})
            raise SubscriptionError(exc.code, exc.message, 400)

        if not result.verified:
            logger.warning(
                "razorpay webhook rejected", extra={"reason": result.message}
            )
            raise SubscriptionError(
                "PAYMENT_VERIFICATION_FAILED", "Webhook verification failed", 400
            )

        if not result.provider_order_id:
            # Signed, but an event we deliberately do not act on.
            logger.info(
                "razorpay webhook acknowledged without state change",
                extra={"reason": result.message},
            )
            return None

        payment = (
            db.query(SubscriptionPayment)
            .filter(
                SubscriptionPayment.provider == result.provider,
                SubscriptionPayment.provider_order_id == result.provider_order_id,
            )
            .first()
        )
        if payment is None:
            logger.warning(
                "razorpay webhook for an unknown order",
                extra={"order_id": result.provider_order_id},
            )
            return None

        # Amount/currency are compared against OUR row (the client never sent
        # them). A mismatch means something is wrong with the payment itself:
        # log it, change nothing, and still ACK so Razorpay stops retrying.
        if result.amount is not None and Decimal(result.amount) != Decimal(
            payment.amount
        ):
            logger.warning(
                "razorpay webhook amount mismatch", extra={"payment_id": payment.id}
            )
            return None
        if result.currency and str(result.currency).upper() != str(
            payment.currency
        ).upper():
            logger.warning(
                "razorpay webhook currency mismatch", extra={"payment_id": payment.id}
            )
            return None

        user = None
        if payment.user_id:
            user = db.query(User).filter(User.id == payment.user_id).first()
        return PaymentService._finalize(db, payment=payment, verification=result, user=user)

    # -----------------------------------------------------------------------
    # Provider maintenance hooks (used by tests / future admin tooling)
    # -----------------------------------------------------------------------

    @staticmethod
    def cancel_pending(
        db: Session, *, user: User, payment_id: int
    ) -> SubscriptionPayment:
        payment = PaymentService.get_payment(db, user=user, payment_id=payment_id)
        if payment.status != "PENDING":
            raise SubscriptionError(
                "PAYMENT_NOT_PENDING",
                f"Payment is {payment.status.lower()} and cannot be cancelled",
            )
        provider = PaymentService.get_provider(payment.provider)
        result = provider.cancel_payment(order_id=str(payment.provider_order_id))
        if not result.verified:
            raise SubscriptionError(
                "PAYMENT_VERIFICATION_FAILED", "Payment verification failed", 400
            )
        payment.status = "CANCELLED"
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def serialize(payment: SubscriptionPayment) -> SubscriptionPaymentResponse:
        return SubscriptionPaymentResponse.model_validate(payment)
