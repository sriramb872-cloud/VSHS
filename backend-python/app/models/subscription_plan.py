# backend-python/app/models/subscription_plan.py
"""School-specific subscription plans (pricing catalogue).

A plan is the *price offered to one role in one school*. It does NOT grant
access by itself - access comes from an entitlement (``subscriptions`` row)
or an override. Plans are never hard-deleted once used: they are deactivated
(``is_active = False``) so historical subscriptions/payments keep their
foreign keys intact.

Durations are fully configurable: ``duration_value`` + ``duration_unit``
express anything from 7 days to 1 year (or more). Nothing in the system
assumes "1 month = 30 days"; month/year arithmetic is calendar-aware (see
``app.core.time_utils.add_duration``).
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)

from app.core.database import Base

# Duration units supported by every duration field in the subscription
# domain. Calendar-aware (MONTH/YEAR clamp to the last valid day, e.g.
# Jan 31 + 1 month = Feb 28/29).
DURATION_UNITS = ("DAY", "MONTH", "YEAR")

# Informational billing cadence shown in listings. The authoritative length
# of a plan is always duration_value + duration_unit.
BILLING_INTERVALS = (
    "ONE_TIME",
    "WEEKLY",
    "MONTHLY",
    "QUARTERLY",
    "YEARLY",
    "CUSTOM",
)

# Roles that can be billed. SUPER_ADMIN is deliberately excluded: platform
# admins bypass subscription enforcement entirely.
BILLABLE_ROLES = ("PRINCIPAL", "TEACHER", "STUDENT")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    school_id = Column(
        Integer,
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # String (not a native MySQL ENUM) so future roles/statuses can be added
    # without an ALTER on a live billing table. Validated at the API layer
    # against BILLABLE_ROLES.
    role = Column(String(20), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    # Money: Numeric(10, 2) keeps exact decimal precision (never float).
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR", server_default="INR")

    billing_interval = Column(
        String(20),
        nullable=False,
        default="CUSTOM",
        server_default="CUSTOM",
    )
    duration_value = Column(Integer, nullable=False)
    duration_unit = Column(String(10), nullable=False)  # DAY | MONTH | YEAR

    # Deactivation (not deletion) is the only way to retire a plan.
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        # The hot lookup: "plans offered for this role in this school".
        Index("ix_subscription_plans_school_role", "school_id", "role"),
        Index("ix_subscription_plans_school_active", "school_id", "is_active"),
    )
