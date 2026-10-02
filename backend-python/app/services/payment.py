# backend-python/app/services/payment.py
"""Payment orchestration - provider-agnostic.

Flow (identical for the mock provider now and Razorpay later):

    client -> create_checkout()        -> provider.create_order()
                                       -> subscription_payments row (PENDING)
    client -> checkout at provider ----> provider result (signed)
    server -> complete_*()             -> provider.verify_payment()  <-- boundary
                                       -> payment status update
                                       -> ONLY on verified SUCCESS:
                                          activate/renew entitlement
                                       -> payment + activation notifications

The client NEVER tells the backend "my payment succeeded" and gets access;
it only reports which test outcome the simulated provider returned, and the
server-side verification decides.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.time_utils import utcnow
from app.models.subscription import Subscription
from app.models.subscription_payment import SubscriptionPayment
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.schemas.subscription_payment import SubscriptionPaymentResponse
from app.services.payment_providers import (
    OrderRequest,
    PaymentProvider,
    PaymentProviderError,
)
from app.services.payment_providers.mock import MockPaymentProvider
from app.services.subscription import (
    SubscriptionError,
    SubscriptionService,
    notify_user,
)


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
    def get_provider(provider: Optional[str] = None) -> PaymentProvider:
        """Factory: today only the mock provider exists (Phase 1)."""
        name = (provider or "INTERNAL").upper()
        if name == "INTERNAL":
            if not PaymentService.mock_payments_enabled():
                raise SubscriptionError(
                    "PAYMENT_PROVIDER_UNAVAILABLE",
                    "Mock payments are disabled in this environment",
                    400,
                )
            return MockPaymentProvider(secret=app_settings.SECRET_KEY)
        # Phase 2: elif name == "RAZORPAY": return RazorpayProvider(...)
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
        chooses which plan it wants, never the price.
        """
        SubscriptionService._ensure_billable(user)
        plan = (
            db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        )
        if plan is None:
            raise SubscriptionError("PLAN_NOT_FOUND", "Plan not found", 404)
        SubscriptionService.ensure_plan_usable(db, plan=plan, target=user)

        provider = PaymentService.get_provider("INTERNAL")
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

    # -----------------------------------------------------------------------
    # Completion (mock checkout result -> verified -> entitlement)
    # -----------------------------------------------------------------------

    @staticmethod
    def complete_mock_checkout(
        db: Session, *, user: User, payment_id: int, outcome: str
    ) -> SubscriptionPayment:
        """Complete a PENDING mock checkout.

        The client supplies only the test outcome. The provider payload is
        built + signed server-side and verified before any state changes -
        mirroring how Razorpay's signature verification will work later.
        """
        provider = PaymentService.get_provider("INTERNAL")  # raises if disabled

        payment = (
            db.query(SubscriptionPayment)
            .filter(SubscriptionPayment.id == payment_id)
            .first()
        )
        # Never leak the existence of another user's payment.
        if payment is None or payment.user_id != user.id:
            raise SubscriptionError("PAYMENT_NOT_FOUND", "Payment not found", 404)
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
        )
        if not verification.verified:
            # Signature/amount mismatch = tampering or corruption. Fail loud,
            # change nothing.
            raise SubscriptionError(
                "PAYMENT_VERIFICATION_FAILED",
                "Payment verification failed",
                400,
            )

        if verification.status == "PENDING":
            db.commit()  # nothing changed; keep the row PENDING
            return payment

        payment.status = verification.status
        if verification.status == "SUCCESS":
            payment.paid_at = utcnow()
            payment.provider_payment_id = verification.provider_payment_id

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
        if payment.status == "SUCCESS":
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

    # -----------------------------------------------------------------------
    # Provider maintenance hooks (used by tests / future admin tooling)
    # -----------------------------------------------------------------------

    @staticmethod
    def cancel_pending(
        db: Session, *, user: User, payment_id: int
    ) -> SubscriptionPayment:
        payment = (
            db.query(SubscriptionPayment)
            .filter(SubscriptionPayment.id == payment_id)
            .first()
        )
        if payment is None or payment.user_id != user.id:
            raise SubscriptionError("PAYMENT_NOT_FOUND", "Payment not found", 404)
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
