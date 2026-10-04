# backend-python/app/models/subscription_payment.py
"""Payment records for subscription purchases.

Created *now*, before any real payment provider is integrated, so the
subscription domain already depends on an abstract payment record instead of
being retrofitted later.

``provider`` identifies who processed the money:
  * ``INTERNAL``  - the development-only mock provider (never in production)
  * ``RAZORPAY``  - one-time prepaid UPI orders (Razorpay ORDERS API)

Statuses: PENDING | SUCCESS | FAILED | CANCELLED | REFUNDED.

Financial rows are append-only: a plan being deactivated or a subscription
being cancelled never deletes payment history.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)

from app.core.database import Base

PAYMENT_STATUSES = ("PENDING", "SUCCESS", "FAILED", "CANCELLED", "REFUNDED")

PAYMENT_PROVIDERS = ("INTERNAL", "RAZORPAY")


class SubscriptionPayment(Base):
    __tablename__ = "subscription_payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    school_id = Column(
        Integer,
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # SET NULL: if a user row is ever removed manually, the financial record
    # survives (school + timestamps still identify it).
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plan_id = Column(
        Integer,
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR", server_default="INR")

    provider = Column(String(20), nullable=False, default="INTERNAL", server_default="INTERNAL")
    provider_order_id = Column(String(100), nullable=True)
    provider_payment_id = Column(String(100), nullable=True)

    status = Column(String(20), nullable=False, default="PENDING", index=True)

    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        # Idempotency anchors: one order/payment identity per provider.
        # NULLs are allowed multiple times on both MySQL and SQLite.
        Index(
            "uq_subscription_payment_order",
            "provider",
            "provider_order_id",
            unique=True,
        ),
        Index(
            "uq_subscription_payment_provider_ref",
            "provider",
            "provider_payment_id",
            unique=True,
        ),
        # Dashboard metrics + admin lists.
        Index("ix_subscription_payments_school_status", "school_id", "status"),
        Index("ix_subscription_payments_user_created", "user_id", "created_at"),
    )
