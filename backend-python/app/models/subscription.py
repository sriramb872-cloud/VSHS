# backend-python/app/models/subscription.py
"""User subscription entitlements.

A ``subscriptions`` row is the *entitlement* that says "this user paid (or
was granted) access until ``end_at``". It is deliberately separate from
``users.account_status``: account status answers "is the login enabled?",
subscription status answers "is the user entitled to paid ERP functionality?".

Lifecycle rules
---------------
* Access is evaluated from *current time*, not from the stored status:
  ``start_at <= now < end_at``. A stored ``ACTIVE`` row whose ``end_at`` has
  passed is expired the moment the clock ticks over, even if no background
  job ever rewrites the status.
* One row per renewal is NOT created; renewals extend ``end_at`` of the
  active row (paid time is never thrown away). Cancelled/superseded rows are
  preserved as history.
* Statuses: ACTIVE | EXPIRED | CANCELLED | SUSPENDED.
* Sources: PAYMENT | ADMIN_GRANT | INDIVIDUAL_OVERRIDE | ROLE_PLAN |
  SCHOOL_OVERRIDE.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base

# Stored status values (String, not a native MySQL ENUM, so statuses can
# evolve without an ALTER on a live billing table). Note that access checks
# never trust this column alone - time is evaluated too.
SUBSCRIPTION_STATUSES = ("ACTIVE", "EXPIRED", "CANCELLED", "SUSPENDED")

SUBSCRIPTION_SOURCES = (
    "PAYMENT",
    "ADMIN_GRANT",
    "INDIVIDUAL_OVERRIDE",
    "ROLE_PLAN",
    "SCHOOL_OVERRIDE",
)

# Statuses that represent "not terminated by the user" - used to find the
# row a renewal should extend (ACTIVE and SUSPENDED rows keep their paid
# time; CANCELLED rows are history and get a fresh row instead).
LIVE_STATUSES = ("ACTIVE", "SUSPENDED")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    school_id = Column(
        Integer,
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id = Column(
        Integer,
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=True,  # historical rows may outlive a manually removed plan
        index=True,
    )

    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False, index=True)
    source = Column(String(30), nullable=False, default="ADMIN_GRANT")

    # Snapshot of the price paid at grant time (keeps history meaningful even
    # if the plan's price changes later).
    amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    plan = relationship("SubscriptionPlan", foreign_keys=[plan_id])

    __table_args__ = (
        # Access-check hot path: "is there a live subscription for this user".
        Index("ix_subscriptions_user_status", "user_id", "status"),
        # Aggregation/reporting hot path: per-school status counts.
        Index("ix_subscriptions_school_status", "school_id", "status"),
        # Expiry sweeps: "live rows that have passed their end".
        Index("ix_subscriptions_status_end", "status", "end_at"),
    )
